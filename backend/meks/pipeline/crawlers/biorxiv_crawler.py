import asyncio
import logging
from datetime import date, datetime, timedelta

import httpx

from meks.pipeline.crawlers import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

BIORXIV_API_BASE = "https://api.biorxiv.org/details"
RATE_LIMIT_DELAY = 1.0


class BiorxivCrawler(BaseCrawler):
    def __init__(self, server: str = "medrxiv", timeout: float = 30.0):
        self._server = server
        self._timeout = timeout

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
            headers={"User-Agent": "MEKS/1.0 (Medical Expert Knowledge System)"},
        )

    async def search(
        self, query: str, max_results: int = 20, watermark: str | None = None
    ) -> list[CrawlResult]:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        if watermark:
            try:
                start_date = datetime.strptime(watermark[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        interval = f"{start_date.isoformat()}/{end_date.isoformat()}"

        keywords = [kw.lower().strip() for kw in query.split() if kw.strip()]
        results: list[CrawlResult] = []
        cursor = 0

        async with self._build_client() as client:
            while len(results) < max_results:
                url = f"{BIORXIV_API_BASE}/{self._server}/{interval}/{cursor}"
                resp = await client.get(url)
                resp.raise_for_status()

                data = resp.json()
                collection = data.get("collection", [])
                if not collection:
                    break

                for item in collection:
                    if len(results) >= max_results:
                        break
                    title = item.get("title", "")
                    abstract = item.get("abstract", "")
                    searchable = (title + " " + abstract).lower()
                    if keywords and not all(kw in searchable for kw in keywords):
                        continue

                    doi = item.get("doi", "")
                    authors_raw = item.get("authors", "")
                    authors = "; ".join(
                        a.strip() for a in authors_raw.split(";") if a.strip()
                    ) if authors_raw else "Unknown"

                    pub_date = None
                    date_str = item.get("date", "")
                    if date_str:
                        try:
                            pub_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    version = str(item.get("version", "1"))
                    pdf_url = f"https://www.{self._server}.org/content/{doi}v{version}.full.pdf"

                    results.append(CrawlResult(
                        external_id=doi,
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=pdf_url,
                        published_date=pub_date,
                        metadata={
                            "category": item.get("category", ""),
                            "server": self._server,
                            "version": version,
                        },
                    ))

                messages = data.get("messages", [])
                total = 0
                if messages:
                    try:
                        total = int(messages[0].get("total", 0))
                    except (ValueError, TypeError):
                        pass

                cursor += len(collection)
                if cursor >= total or len(collection) == 0:
                    break

                await asyncio.sleep(RATE_LIMIT_DELAY)

        results.sort(key=lambda r: r.published_date or date.min, reverse=True)
        return results

    async def download(self, result: CrawlResult) -> bytes:
        async with self._build_client() as client:
            try:
                resp = await client.get(result.url)
                if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                    return resp.content
            except httpx.HTTPError:
                logger.debug("PDF download failed for %s", result.external_id)

            await asyncio.sleep(RATE_LIMIT_DELAY)

            doi = result.external_id
            version = result.metadata.get("version", "1")
            xml_url = f"https://www.{self._server}.org/content/{doi}v{version}.source.xml"
            resp = await client.get(xml_url)
            resp.raise_for_status()
            return resp.content

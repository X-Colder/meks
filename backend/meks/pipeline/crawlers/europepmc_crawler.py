import asyncio
import logging
from datetime import date, datetime

import httpx

from meks.pipeline.crawlers import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPEPMC_PDF_BASE = "https://europepmc.org/backend/ptpmcrender.fcgi"
EUROPEPMC_XML_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
RATE_LIMIT_DELAY = 0.5


class EuropePMCCrawler(BaseCrawler):
    def __init__(self, timeout: float = 30.0):
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
        results: list[CrawlResult] = []

        search_query = query
        if watermark:
            search_query = f"{query} AND FIRST_PDATE:[{watermark} TO *]"

        params = {
            "query": search_query,
            "format": "json",
            "resultType": "core",
            "pageSize": str(min(max_results, 100)),
            "sort": "FIRST_PDATE desc",
        }

        async with self._build_client() as client:
            resp = await client.get(EUROPEPMC_SEARCH, params=params)
            resp.raise_for_status()

            data = resp.json()
            items = data.get("resultList", {}).get("result", [])

            for item in items:
                if len(results) >= max_results:
                    break

                pmcid = item.get("pmcid", "")
                paper_id = pmcid or item.get("id", "")
                if not paper_id:
                    continue

                title = item.get("title", "Untitled").rstrip(".")
                authors = item.get("authorString", "Unknown").rstrip(".")
                abstract = item.get("abstractText", "")
                doi = item.get("doi", "")
                journal = item.get("journalTitle", "")

                pub_date = None
                date_str = item.get("firstPublicationDate", "")
                if date_str:
                    try:
                        pub_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                if pmcid:
                    url = f"{EUROPEPMC_PDF_BASE}?accid={pmcid}&blobtype=pdf"
                else:
                    url = f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}"

                metadata: dict = {}
                if doi:
                    metadata["doi"] = doi
                if journal:
                    metadata["journal"] = journal
                if pmcid:
                    metadata["pmcid"] = pmcid

                results.append(CrawlResult(
                    external_id=paper_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=url,
                    published_date=pub_date,
                    metadata=metadata,
                ))

        return results

    async def download(self, result: CrawlResult) -> bytes:
        async with self._build_client() as client:
            pmcid = result.metadata.get("pmcid", "")

            if pmcid:
                pdf_url = f"{EUROPEPMC_PDF_BASE}?accid={pmcid}&blobtype=pdf"
                try:
                    resp = await client.get(pdf_url)
                    if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                        return resp.content
                except httpx.HTTPError:
                    logger.debug("PDF download failed for %s", pmcid)

                await asyncio.sleep(RATE_LIMIT_DELAY)

                xml_url = f"{EUROPEPMC_XML_BASE}/{pmcid}/fullTextXML"
                resp = await client.get(xml_url)
                resp.raise_for_status()
                return resp.content

            resp = await client.get(result.url)
            resp.raise_for_status()
            return resp.content

import asyncio
import logging
from datetime import date

import httpx

from meks.pipeline.crawlers import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,abstract,year,externalIds,openAccessPdf,publicationDate,venue,citationCount,influentialCitationCount"
RATE_LIMIT_DELAY = 1.0


class SemanticScholarCrawler(BaseCrawler):
    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self._api_key = api_key
        self._timeout = timeout

    def _build_client(self) -> httpx.AsyncClient:
        headers = {"User-Agent": "MEKS/1.0 (Medical Expert Knowledge System)"}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
            headers=headers,
        )

    async def search(
        self, query: str, max_results: int = 20, watermark: str | None = None
    ) -> list[CrawlResult]:
        results: list[CrawlResult] = []
        offset = 0
        limit = min(max_results, 100)

        async with self._build_client() as client:
            while len(results) < max_results:
                params = {
                    "query": query,
                    "fields": S2_FIELDS,
                    "limit": str(limit),
                    "offset": str(offset),
                    "sort": "publicationDate:desc",
                }
                resp = await client.get(S2_SEARCH_URL, params=params)
                resp.raise_for_status()

                data = resp.json()
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    if len(results) >= max_results:
                        break

                    open_access_pdf = item.get("openAccessPdf")
                    if not open_access_pdf or not open_access_pdf.get("url"):
                        continue

                    paper_id = item.get("paperId", "")
                    if not paper_id:
                        continue

                    title = item.get("title", "Untitled")
                    authors_list = item.get("authors", [])
                    authors = "; ".join(
                        a.get("name", "") for a in authors_list if a.get("name")
                    ) or "Unknown"
                    abstract = item.get("abstract", "") or ""

                    external_ids = item.get("externalIds", {}) or {}
                    doi = external_ids.get("DOI", "")
                    external_id = doi if doi else paper_id

                    pub_date = None
                    pub_date_str = item.get("publicationDate", "")
                    if pub_date_str:
                        try:
                            from datetime import datetime
                            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    if pub_date is None:
                        year = item.get("year")
                        if year:
                            try:
                                pub_date = date(int(year), 1, 1)
                            except (ValueError, TypeError):
                                pass

                    pdf_url = open_access_pdf["url"]
                    venue = item.get("venue", "")

                    metadata: dict = {"paper_id": paper_id}
                    if doi:
                        metadata["doi"] = doi
                    if venue:
                        metadata["journal"] = venue
                    citation_count = item.get("citationCount", 0) or 0
                    metadata["citation_count"] = citation_count

                    results.append(CrawlResult(
                        external_id=external_id,
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=pdf_url,
                        published_date=pub_date,
                        metadata=metadata,
                    ))

                total = data.get("total", 0)
                offset += len(items)
                if offset >= total or len(items) == 0:
                    break

                await asyncio.sleep(RATE_LIMIT_DELAY)

        results.sort(
            key=lambda r: (
                r.published_date or date.min,
                r.metadata.get("citation_count", 0),
            ),
            reverse=True,
        )
        return results[:max_results]

    async def download(self, result: CrawlResult) -> bytes:
        async with self._build_client() as client:
            resp = await client.get(result.url)
            resp.raise_for_status()
            return resp.content

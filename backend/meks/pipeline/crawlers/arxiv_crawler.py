import asyncio
import logging
from datetime import date, datetime
from xml.etree import ElementTree as ET

import httpx

from meks.pipeline.crawlers import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
RATE_LIMIT_DELAY = 3  # arXiv asks for max 1 request per 3 seconds


class ArxivCrawler(BaseCrawler):
    """arXiv crawler using the arXiv Atom API."""

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
            # Use watermark as lastUpdatedDate for incremental fetching
            arxiv_date = watermark[:10].replace("-", "")
            search_query = f"{query} AND lastUpdatedDate:[{arxiv_date}000000 TO *]"

        params = {
            "search_query": search_query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        async with self._build_client() as client:
            resp = await client.get(ARXIV_API_URL, params=params)
            resp.raise_for_status()

            results = self._parse_feed(resp.text)

        return results

    def _parse_feed(self, xml_text: str) -> list[CrawlResult]:
        results: list[CrawlResult] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.error("Failed to parse arXiv Atom XML response")
            return results

        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            try:
                result = self._parse_entry(entry)
                if result:
                    results.append(result)
            except Exception:
                logger.warning("Failed to parse arXiv entry", exc_info=True)

        return results

    def _parse_entry(self, entry: ET.Element) -> CrawlResult | None:
        # Extract arXiv ID from the <id> element
        id_el = entry.find(f"{{{ATOM_NS}}}id")
        if id_el is None or not id_el.text:
            return None
        arxiv_url = id_el.text.strip()
        # ID is the last part of the URL, e.g. http://arxiv.org/abs/2301.12345v1
        arxiv_id = arxiv_url.rsplit("/abs/", 1)[-1] if "/abs/" in arxiv_url else arxiv_url

        # Extract title
        title_el = entry.find(f"{{{ATOM_NS}}}title")
        title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else "Untitled"

        # Extract authors
        author_names: list[str] = []
        for author in entry.findall(f"{{{ATOM_NS}}}author"):
            name_el = author.find(f"{{{ATOM_NS}}}name")
            if name_el is not None and name_el.text:
                author_names.append(name_el.text.strip())
        authors = "; ".join(author_names) if author_names else "Unknown"

        # Extract abstract (summary)
        summary_el = entry.find(f"{{{ATOM_NS}}}summary")
        abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""

        # Extract published date
        pub_date = None
        published_el = entry.find(f"{{{ATOM_NS}}}published")
        if published_el is not None and published_el.text:
            try:
                dt = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
                pub_date = dt.date()
            except ValueError:
                pass

        # Extract PDF link
        pdf_url = ""
        for link in entry.findall(f"{{{ATOM_NS}}}link"):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
                break
        if not pdf_url:
            # Fallback: construct PDF URL from arXiv ID
            clean_id = arxiv_id.rstrip("v0123456789").rstrip("v") if "v" in arxiv_id else arxiv_id
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        # Extract categories
        categories: list[str] = []
        for cat in entry.findall("{http://arxiv.org/schemas/atom}primary_category"):
            term = cat.get("term")
            if term:
                categories.append(term)

        # Extract DOI if available
        doi_el = entry.find("{http://arxiv.org/schemas/atom}doi")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

        metadata: dict = {"arxiv_url": arxiv_url}
        if categories:
            metadata["categories"] = categories
        if doi:
            metadata["doi"] = doi

        return CrawlResult(
            external_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            url=pdf_url,
            published_date=pub_date,
            metadata=metadata,
        )

    async def download(self, result: CrawlResult) -> bytes:
        async with self._build_client() as client:
            await asyncio.sleep(RATE_LIMIT_DELAY)
            resp = await client.get(result.url, follow_redirects=True)
            resp.raise_for_status()
            return resp.content

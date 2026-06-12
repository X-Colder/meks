import asyncio
import logging
from datetime import date, datetime
from xml.etree import ElementTree as ET

import httpx

from meks.pipeline.crawlers import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PMC_PDF_BASE = "https://www.ncbi.nlm.nih.gov/pmc/articles"
RATE_LIMIT_DELAY = 0.35  # 3 requests per second max
ESUMMARY_BATCH_SIZE = 200


class PMCCrawler(BaseCrawler):
    """PubMed Central crawler using NCBI E-utilities API."""

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

        async with self._build_client() as client:
            # Step 1: esearch to get PMCIDs
            search_params: dict = {
                "db": "pmc",
                "term": query,
                "retmax": str(max_results),
                "retmode": "xml",
                "sort": "date",
            }
            if watermark:
                # Use watermark as mindate for incremental fetching
                search_params["mindate"] = watermark
                search_params["datetype"] = "pdat"

            resp = await client.get(
                f"{EUTILS_BASE}/esearch.fcgi", params=search_params
            )
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            id_list = root.findall(".//IdList/Id")
            pmcids = [id_el.text for id_el in id_list if id_el.text]

            if not pmcids:
                return results

            await asyncio.sleep(RATE_LIMIT_DELAY)

            # Step 2: esummary is much lighter than full article efetch and avoids
            # long pre-download stalls when scanning hundreds of candidates.
            for i in range(0, len(pmcids), ESUMMARY_BATCH_SIZE):
                batch = pmcids[i : i + ESUMMARY_BATCH_SIZE]
                summary_params = {
                    "db": "pmc",
                    "id": ",".join(batch),
                    "retmode": "xml",
                }
                resp = await client.get(
                    f"{EUTILS_BASE}/esummary.fcgi", params=summary_params
                )
                resp.raise_for_status()
                results.extend(self._parse_summaries(resp.text))
                if i + ESUMMARY_BATCH_SIZE < len(pmcids):
                    await asyncio.sleep(RATE_LIMIT_DELAY)

        return results

    def _parse_summaries(self, xml_text: str) -> list[CrawlResult]:
        results: list[CrawlResult] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.error("Failed to parse PMC esummary XML response")
            return results

        for docsum in root.findall(".//DocSum"):
            pmc_num = docsum.findtext("Id")
            if not pmc_num:
                continue

            items = {item.get("Name", ""): item for item in docsum.findall("Item")}
            title = (items.get("Title").text or "Untitled") if items.get("Title") is not None else "Untitled"
            journal = (items.get("FullJournalName").text or "") if items.get("FullJournalName") is not None else ""
            doi = (items.get("DOI").text or "") if items.get("DOI") is not None else ""
            pub_date = self._parse_summary_date(
                (items.get("EPubDate").text or "") if items.get("EPubDate") is not None else ""
            ) or self._parse_summary_date(
                (items.get("PubDate").text or "") if items.get("PubDate") is not None else ""
            )

            authors: list[str] = []
            author_list = items.get("AuthorList")
            if author_list is not None:
                authors = [
                    author.text.strip()
                    for author in author_list.findall("Item")
                    if author.text and author.text.strip()
                ]

            pmcid = f"PMC{pmc_num}" if not pmc_num.startswith("PMC") else pmc_num
            metadata: dict = {}
            if doi:
                metadata["doi"] = doi
            if journal:
                metadata["journal"] = journal

            results.append(
                CrawlResult(
                    external_id=pmcid,
                    title=title.strip().rstrip(".") or "Untitled",
                    authors="; ".join(authors) if authors else "Unknown",
                    abstract="",
                    url=f"{PMC_PDF_BASE}/{pmcid}/",
                    published_date=pub_date,
                    metadata=metadata,
                )
            )
        return results

    def _parse_summary_date(self, value: str) -> date | None:
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y %b %d", "%Y %b", "%Y"):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.date()
            except ValueError:
                pass
        return None

    def _parse_articles(self, xml_text: str) -> list[CrawlResult]:
        results: list[CrawlResult] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.error("Failed to parse PMC efetch XML response")
            return results

        for article in root.findall(".//article"):
            try:
                result = self._parse_single_article(article)
                if result:
                    results.append(result)
            except Exception:
                logger.warning("Failed to parse PMC article entry", exc_info=True)

        return results

    def _parse_single_article(self, article: ET.Element) -> CrawlResult | None:
        # Extract PMCID
        article_ids = article.findall(".//article-id")
        pmcid = None
        doi = None
        for aid in article_ids:
            id_type = aid.get("pub-id-type", "")
            if id_type in ("pmc", "pmcid"):
                pmcid = f"PMC{aid.text}" if aid.text and not aid.text.startswith("PMC") else aid.text
            elif id_type == "doi":
                doi = aid.text

        if not pmcid:
            return None

        # Extract title
        title_el = article.find(".//article-title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else "Untitled"

        # Extract authors
        author_names: list[str] = []
        for contrib in article.findall(".//contrib[@contrib-type='author']"):
            surname = contrib.findtext("name/surname", "")
            given = contrib.findtext("name/given-names", "")
            if surname:
                author_names.append(f"{given} {surname}".strip())
        authors = "; ".join(author_names) if author_names else "Unknown"

        # Extract abstract
        abstract_el = article.find(".//abstract")
        abstract = "".join(abstract_el.itertext()).strip() if abstract_el is not None else ""

        # Extract publication date
        pub_date = None
        pub_date_el = article.find(".//pub-date[@pub-type='epub']")
        if pub_date_el is None:
            pub_date_el = article.find(".//pub-date")
        if pub_date_el is not None:
            year = pub_date_el.findtext("year")
            month = pub_date_el.findtext("month", "1")
            day = pub_date_el.findtext("day", "1")
            try:
                pub_date = date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                pass

        # Extract journal
        journal = article.findtext(".//journal-title", "")

        url = f"{PMC_PDF_BASE}/{pmcid}/"

        metadata: dict = {}
        if doi:
            metadata["doi"] = doi
        if journal:
            metadata["journal"] = journal

        return CrawlResult(
            external_id=pmcid,
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            published_date=pub_date,
            metadata=metadata,
        )

    async def download(self, result: CrawlResult) -> bytes:
        async with self._build_client() as client:
            # Try to download PDF from PMC
            pdf_url = f"{PMC_PDF_BASE}/{result.external_id}/pdf/"
            try:
                resp = await client.get(pdf_url, follow_redirects=True)
                if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                    return resp.content
            except httpx.HTTPError:
                logger.debug(
                    "PDF not available for %s, falling back to XML",
                    result.external_id,
                )

            await asyncio.sleep(RATE_LIMIT_DELAY)

            # Fallback: fetch article XML
            pmcid_num = result.external_id.replace("PMC", "")
            fetch_params = {
                "db": "pmc",
                "id": pmcid_num,
                "retmode": "xml",
            }
            resp = await client.get(
                f"{EUTILS_BASE}/efetch.fcgi", params=fetch_params
            )
            resp.raise_for_status()
            return resp.content

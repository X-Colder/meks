#!/usr/bin/env python3
"""
从 PubMed Central 和 arXiv 下载公开医学论文到本地，用于 MEKS 知识库测试。

用法:
    python3 scripts/fetch_test_papers.py

论文将下载到 test_data/ 目录，可通过前端或 API 上传到知识库。
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "test_data"

PMC_QUERIES = {
    "diabetes mellitus treatment": 3,
    "lung cancer diagnosis": 3,
    "hypertension management guidelines": 2,
    "Alzheimer disease biomarkers": 2,
    "COVID-19 clinical outcomes": 2,
    "stroke rehabilitation": 2,
    "chronic kidney disease": 2,
    "heart failure prognosis": 2,
}

ARXIV_QUERIES = {
    "all:medical image segmentation": 2,
    "all:clinical natural language processing": 2,
}

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ARXIV_API = "https://export.arxiv.org/api/query"


@dataclass
class Paper:
    source: str
    external_id: str
    title: str
    authors: str
    abstract: str
    url: str
    pub_date: str


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        follow_redirects=True,
        headers={"User-Agent": "MEKS/1.0 (Medical Expert Knowledge System; research testing)"},
    )


# ── PMC ──────────────────────────────────────────────────────


async def search_pmc(client: httpx.AsyncClient, query: str, max_results: int) -> list[Paper]:
    resp = await client.get(f"{EUTILS}/esearch.fcgi", params={
        "db": "pmc", "term": f'{query} AND "open access"[filter]',
        "retmax": str(max_results), "retmode": "xml", "sort": "date",
    })
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    pmcids = [el.text for el in root.findall(".//IdList/Id") if el.text]
    if not pmcids:
        return []

    await asyncio.sleep(0.4)

    resp = await client.get(f"{EUTILS}/efetch.fcgi", params={
        "db": "pmc", "id": ",".join(pmcids), "retmode": "xml",
    })
    resp.raise_for_status()

    papers: list[Paper] = []
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        print("    XML 解析失败")
        return []

    for article in root.findall(".//article"):
        pmcid = None
        for aid in article.findall(".//article-id"):
            id_type = aid.get("pub-id-type", "")
            if id_type in ("pmc", "pmcid"):
                pmcid = f"PMC{aid.text}" if aid.text and not aid.text.startswith("PMC") else aid.text
                break
        if not pmcid:
            continue

        title_el = article.find(".//article-title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else "Untitled"

        authors_list = []
        for c in article.findall(".//contrib[@contrib-type='author']"):
            s = c.findtext("name/surname", "")
            g = c.findtext("name/given-names", "")
            if s:
                authors_list.append(f"{g} {s}".strip())
        authors = "; ".join(authors_list[:5]) or "Unknown"

        abstract_el = article.find(".//abstract")
        abstract = "".join(abstract_el.itertext()).strip() if abstract_el is not None else ""

        pub_date = ""
        pde = article.find(".//pub-date[@pub-type='epub']") or article.find(".//pub-date")
        if pde is not None:
            y = pde.findtext("year", "")
            m = pde.findtext("month", "")
            d = pde.findtext("day", "")
            pub_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}" if y else ""

        papers.append(Paper(
            source="PMC", external_id=pmcid, title=title,
            authors=authors, abstract=abstract[:600],
            url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
            pub_date=pub_date,
        ))

    return papers


async def download_pmc(client: httpx.AsyncClient, paper: Paper) -> bytes | None:
    pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{paper.external_id}/pdf/"
    try:
        resp = await client.get(pdf_url)
        if resp.status_code == 200 and resp.content[:4] == b"%PDF":
            return resp.content
    except httpx.HTTPError:
        pass

    await asyncio.sleep(0.4)
    pmcid_num = paper.external_id.replace("PMC", "")
    resp = await client.get(f"{EUTILS}/efetch.fcgi", params={
        "db": "pmc", "id": pmcid_num, "retmode": "xml",
    })
    if resp.status_code == 200:
        return resp.content
    return None


# ── arXiv ────────────────────────────────────────────────────


async def search_arxiv(client: httpx.AsyncClient, query: str, max_results: int) -> list[Paper]:
    resp = await client.get(ARXIV_API, params={
        "search_query": query, "start": "0",
        "max_results": str(max_results),
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    resp.raise_for_status()

    ns = "http://www.w3.org/2005/Atom"
    papers: list[Paper] = []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return []

    for entry in root.findall(f"{{{ns}}}entry"):
        id_el = entry.find(f"{{{ns}}}id")
        if id_el is None or not id_el.text:
            continue
        arxiv_url = id_el.text.strip()
        arxiv_id = arxiv_url.rsplit("/abs/", 1)[-1] if "/abs/" in arxiv_url else arxiv_url

        title_el = entry.find(f"{{{ns}}}title")
        title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else "Untitled"

        author_names = []
        for a in entry.findall(f"{{{ns}}}author"):
            n = a.find(f"{{{ns}}}name")
            if n is not None and n.text:
                author_names.append(n.text.strip())
        authors = "; ".join(author_names[:5]) or "Unknown"

        summary = entry.find(f"{{{ns}}}summary")
        abstract = summary.text.strip().replace("\n", " ") if summary is not None and summary.text else ""

        pub_el = entry.find(f"{{{ns}}}published")
        pub_date = pub_el.text[:10] if pub_el is not None and pub_el.text else ""

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        for link in entry.findall(f"{{{ns}}}link"):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", pdf_url)
                break

        papers.append(Paper(
            source="arXiv", external_id=arxiv_id, title=title,
            authors=authors, abstract=abstract[:600],
            url=pdf_url, pub_date=pub_date,
        ))

    return papers


async def download_arxiv(client: httpx.AsyncClient, paper: Paper) -> bytes | None:
    await asyncio.sleep(3)
    resp = await client.get(paper.url)
    if resp.status_code == 200:
        return resp.content
    return None


# ── main ─────────────────────────────────────────────────────


def save_paper(directory: Path, paper: Paper, content: bytes) -> str:
    safe_id = paper.external_id.replace("/", "_")
    ext = "pdf" if content[:4] == b"%PDF" else "xml"
    filepath = directory / f"{safe_id}.{ext}"
    filepath.write_bytes(content)

    meta_path = directory / f"{safe_id}.meta.txt"
    meta_path.write_text(
        f"标题: {paper.title}\n"
        f"作者: {paper.authors}\n"
        f"发表日期: {paper.pub_date}\n"
        f"来源: {paper.source}\n"
        f"ID: {paper.external_id}\n"
        f"URL: {paper.url}\n"
        f"摘要: {paper.abstract}\n",
        encoding="utf-8",
    )
    return f"{safe_id}.{ext}"


async def main():
    print("=" * 60)
    print("MEKS 测试数据下载器")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    pmc_dir = OUTPUT_DIR / "pmc"
    arxiv_dir = OUTPUT_DIR / "arxiv"
    pmc_dir.mkdir(parents=True, exist_ok=True)
    arxiv_dir.mkdir(parents=True, exist_ok=True)

    pmc_count = 0
    arxiv_count = 0

    async with _build_client() as client:
        # ── PMC ──
        for query, n in PMC_QUERIES.items():
            print(f"\n[PMC] 搜索: {query} (最多 {n} 篇)")
            try:
                papers = await search_pmc(client, query, n)
                print(f"  找到 {len(papers)} 篇论文")
            except Exception as e:
                print(f"  搜索失败: {e}")
                continue

            for p in papers:
                safe_id = p.external_id.replace("/", "_")
                if list(pmc_dir.glob(f"{safe_id}.*")):
                    print(f"  [跳过] {safe_id}")
                    pmc_count += 1
                    continue

                print(f"  下载: {p.title[:70]}...")
                try:
                    content = await download_pmc(client, p)
                    if content:
                        fname = save_paper(pmc_dir, p, content)
                        print(f"    -> {fname} ({len(content)/1024:.0f} KB)")
                        pmc_count += 1
                    else:
                        print(f"    下载失败: 无内容")
                except Exception as e:
                    print(f"    下载失败: {e}")

                await asyncio.sleep(0.4)

        # ── arXiv ──
        print("\n等待 5 秒以避免 arXiv 限速...")
        await asyncio.sleep(5)
        for query, n in ARXIV_QUERIES.items():
            print(f"\n[arXiv] 搜索: {query} (最多 {n} 篇)")
            try:
                papers = await search_arxiv(client, query, n)
                print(f"  找到 {len(papers)} 篇论文")
            except Exception as e:
                print(f"  搜索失败: {e}")
                continue

            for p in papers:
                safe_id = p.external_id.replace("/", "_")
                if list(arxiv_dir.glob(f"{safe_id}.*")):
                    print(f"  [跳过] {safe_id}")
                    arxiv_count += 1
                    continue

                print(f"  下载: {p.title[:70]}...")
                try:
                    content = await download_arxiv(client, p)
                    if content:
                        fname = save_paper(arxiv_dir, p, content)
                        print(f"    -> {fname} ({len(content)/1024:.0f} KB)")
                        arxiv_count += 1
                    else:
                        print(f"    下载失败: 无内容")
                except Exception as e:
                    print(f"    下载失败: {e}")

    print("\n" + "=" * 60)
    print(f"完成! PMC: {pmc_count} 篇, arXiv: {arxiv_count} 篇")
    print(f"文件位于: {OUTPUT_DIR}")
    print()
    print("使用方式:")
    print("  1. 启动 MEKS: docker compose up -d")
    print("  2. 登录前端, 创建知识库")
    print("  3. 上传 test_data/pmc/ 和 test_data/arxiv/ 中的文件")
    print("  4. 等待系统处理完成后即可搜索和问答")


if __name__ == "__main__":
    asyncio.run(main())

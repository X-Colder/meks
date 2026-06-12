#!/usr/bin/env python3
"""
将 test_data/ 中的论文直接导入 MEKS 系统（数据库 + MinIO）。
跳过 Milvus 向量化步骤，仅完成数据入库，用于前端展示测试。

用法: python3 scripts/import_test_data.py
"""

import asyncio
import os
import sys
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

os.environ.setdefault("MEKS_SECRET_KEY", "dev-local-testing")
os.environ.setdefault("MEKS_DEBUG", "true")
os.environ.setdefault("MEKS_DATABASE_URL", "postgresql+asyncpg://meks:meks_dev_password@localhost:5432/meks")
os.environ.setdefault("MEKS_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MEKS_MILVUS_HOST", "localhost")
os.environ.setdefault("MEKS_MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MEKS_MINIO_ACCESS_KEY", "meksadmin")
os.environ.setdefault("MEKS_MINIO_SECRET_KEY", "meks_minio_password")
os.environ.setdefault("MEKS_MINIO_BUCKET", "meks-documents")
os.environ.setdefault("MEKS_MINIO_SECURE", "false")
os.environ.setdefault("MEKS_RATE_LIMIT_PER_MINUTE", "0")

from meks.config import settings
from meks.models.base import async_session
from meks.models.document import Document, DocumentStatus, FileType
from meks.models.knowledge_base import KnowledgeBase, KBType, Visibility
from meks.models.user import User
from meks.storage.client import get_minio_client

from sqlalchemy import select, func

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def parse_meta(meta_path: Path) -> dict:
    """Parse a .meta.txt file into a dict."""
    result = {}
    current_key = None
    for line in meta_path.read_text(encoding="utf-8").splitlines():
        if ": " in line and not line.startswith(" "):
            key, _, value = line.partition(": ")
            result[key.strip()] = value.strip()
            current_key = key.strip()
        elif current_key:
            result[current_key] += " " + line.strip()
    return result


async def get_admin_user(db) -> User:
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if not user:
        raise RuntimeError("管理员用户不存在，请先运行 seed_admin.py")
    return user


async def get_or_create_kb(db, name: str, description: str, owner: User) -> KnowledgeBase:
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == name)
    )
    kb = result.scalar_one_or_none()
    if kb:
        print(f"  知识库已存在: {name} (id={kb.id})")
        return kb

    kb = KnowledgeBase(
        name=name,
        description=description,
        owner_id=owner.id,
        visibility=Visibility.public,
        department=owner.department,
        milvus_collection=f"meks_kb_{uuid.uuid4().hex[:12]}",
        kb_type=KBType.literature,
        document_count=0,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    print(f"  创建知识库: {name} (id={kb.id})")
    return kb


async def upload_to_minio(file_path: Path, kb_id: uuid.UUID) -> tuple[str, int]:
    """Upload file to MinIO, return (storage_path, size_bytes)."""
    content = file_path.read_bytes()
    ext = file_path.suffix.lstrip(".")
    object_name = f"{kb_id}/{uuid.uuid4().hex}.{ext}"

    content_type_map = {
        "pdf": "application/pdf",
        "xml": "application/xml",
        "txt": "text/plain",
    }

    client = get_minio_client()
    client.put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(content),
        length=len(content),
        content_type=content_type_map.get(ext, "application/octet-stream"),
    )
    return object_name, len(content)


async def import_papers(db, kb: KnowledgeBase, source_dir: Path, owner: User) -> int:
    """Import all papers from a source directory into a knowledge base."""
    if not source_dir.exists():
        return 0

    data_files = [f for f in source_dir.iterdir() if f.suffix in (".pdf", ".xml") and not f.name.endswith(".meta.txt")]
    imported = 0

    for data_file in sorted(data_files):
        meta_file = source_dir / f"{data_file.stem}.meta.txt"
        meta = parse_meta(meta_file) if meta_file.exists() else {}

        external_id = data_file.stem
        title = meta.get("标题", external_id)

        existing = await db.execute(
            select(Document).where(
                Document.knowledge_base_id == kb.id,
                Document.doi == external_id,
            )
        )
        if existing.scalar_one_or_none():
            print(f"    [跳过] {title[:50]}...")
            imported += 1
            continue

        print(f"    导入: {title[:60]}...")

        storage_path, size_bytes = await upload_to_minio(data_file, kb.id)

        pub_date = None
        date_str = meta.get("发表日期", "")
        if date_str and date_str != "None":
            try:
                parts = date_str.split("-")
                pub_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                pass

        ext = data_file.suffix.lstrip(".")
        file_type = FileType.pdf if ext == "pdf" else FileType.xml

        doc = Document(
            title=title,
            filename=data_file.name,
            file_type=file_type,
            file_size_bytes=size_bytes,
            storage_path=storage_path,
            status=DocumentStatus.uploaded,
            authors=meta.get("作者"),
            abstract=meta.get("摘要"),
            doi=external_id,
            publication_date=pub_date,
            knowledge_base_id=kb.id,
            uploaded_by=owner.id,
        )
        db.add(doc)
        await db.commit()
        imported += 1

    kb.document_count = imported
    await db.commit()

    return imported


async def main():
    print("=" * 60)
    print("MEKS 测试数据导入")
    print("=" * 60)

    async with async_session() as db:
        admin = await get_admin_user(db)
        print(f"管理员用户: {admin.username} (id={admin.id})")

        # 创建知识库
        print("\n--- 创建知识库 ---")
        pmc_kb = await get_or_create_kb(
            db,
            name="PubMed Central 医学文献",
            description="从 PubMed Central 下载的开放获取医学论文，涵盖糖尿病、肺癌、高血压、阿尔茨海默病、COVID-19、脑卒中、慢性肾病、心力衰竭等领域。",
            owner=admin,
        )

        # 导入 PMC 论文
        print("\n--- 导入 PMC 论文 ---")
        pmc_count = await import_papers(db, pmc_kb, TEST_DATA_DIR / "pmc", admin)

        # 如果有 arXiv 数据也导入
        arxiv_dir = TEST_DATA_DIR / "arxiv"
        arxiv_files = list(arxiv_dir.glob("*.pdf")) + list(arxiv_dir.glob("*.xml")) if arxiv_dir.exists() else []
        arxiv_count = 0
        if arxiv_files:
            arxiv_kb = await get_or_create_kb(
                db,
                name="arXiv 医学AI论文",
                description="从 arXiv 下载的医学影像分割和临床NLP相关论文。",
                owner=admin,
            )
            print("\n--- 导入 arXiv 论文 ---")
            arxiv_count = await import_papers(db, arxiv_kb, arxiv_dir, admin)

        # 统计
        total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
        total_kbs = (await db.execute(select(func.count(KnowledgeBase.id)))).scalar() or 0

        print("\n" + "=" * 60)
        print(f"导入完成!")
        print(f"  知识库: {total_kbs} 个")
        print(f"  文档:   {total_docs} 篇 (PMC: {pmc_count}, arXiv: {arxiv_count})")
        print()
        print(f"前端访问: http://localhost:5173")
        print(f"后端 API: http://localhost:8088/docs")
        print(f"登录账号: admin / admin123456")


if __name__ == "__main__":
    asyncio.run(main())

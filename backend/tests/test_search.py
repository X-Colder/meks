"""搜索服务测试：批量查询 Document、空结果处理（mock Milvus）。"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.document import Document, DocumentStatus, FileType
from meks.models.knowledge_base import KBType, KnowledgeBase, Visibility
from meks.models.user import User


async def _seed_kb_and_doc(db: AsyncSession, owner: User):
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        name="搜索测试KB",
        owner_id=owner.id,
        visibility=Visibility.public,
        milvus_collection="meks_search_test",
        kb_type=KBType.literature,
    )
    db.add(kb)
    await db.flush()

    doc = Document(
        id=uuid.uuid4(),
        title="测试文献",
        filename="test.pdf",
        file_type=FileType.pdf,
        file_size_bytes=1024,
        storage_path="test/path.pdf",
        authors="张三",
        journal="医学杂志",
        status=DocumentStatus.indexed,
        knowledge_base_id=kb.id,
        uploaded_by=owner.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(kb)
    await db.refresh(doc)
    return kb, doc


class TestExecuteSemanticSearch:
    async def test_returns_enriched_results(
        self, db_session: AsyncSession, researcher_user: User
    ):
        kb, doc = await _seed_kb_and_doc(db_session, researcher_user)

        mock_hits = [
            {
                "id": 1,
                "score": 0.92,
                "document_id": str(doc.id),
                "chunk_index": 0,
                "content": "相关内容片段",
            }
        ]

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", return_value=mock_hits),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="测试查询",
                knowledge_base_ids=[str(kb.id)],
                top_k=10,
                min_score=0.5,
                db=db_session,
            )

        assert len(results) == 1
        assert results[0].document_id == str(doc.id)
        assert results[0].document_title == "测试文献"
        assert results[0].chunk_content == "相关内容片段"
        assert results[0].score == 0.92
        assert results[0].authors == "张三"
        assert results[0].journal == "医学杂志"

    async def test_empty_results_when_no_hits(
        self, db_session: AsyncSession, researcher_user: User
    ):
        kb, _ = await _seed_kb_and_doc(db_session, researcher_user)

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", return_value=[]),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="无匹配查询",
                knowledge_base_ids=[str(kb.id)],
                top_k=10,
                min_score=0.5,
                db=db_session,
            )

        assert results == []

    async def test_score_filter_excludes_low_scores(
        self, db_session: AsyncSession, researcher_user: User
    ):
        kb, doc = await _seed_kb_and_doc(db_session, researcher_user)

        mock_hits = [
            {"id": 1, "score": 0.3, "document_id": str(doc.id), "chunk_index": 0, "content": "低分内容"},
            {"id": 2, "score": 0.8, "document_id": str(doc.id), "chunk_index": 1, "content": "高分内容"},
        ]

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", return_value=mock_hits),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="测试",
                knowledge_base_ids=[str(kb.id)],
                top_k=10,
                min_score=0.5,
                db=db_session,
            )

        assert len(results) == 1
        assert results[0].chunk_content == "高分内容"

    async def test_unknown_document_shows_unknown_title(
        self, db_session: AsyncSession, researcher_user: User
    ):
        kb, _ = await _seed_kb_and_doc(db_session, researcher_user)
        nonexistent_doc_id = str(uuid.uuid4())

        mock_hits = [
            {"id": 1, "score": 0.9, "document_id": nonexistent_doc_id, "chunk_index": 0, "content": "内容"}
        ]

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", return_value=mock_hits),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="测试",
                knowledge_base_ids=[str(kb.id)],
                top_k=10,
                min_score=0.5,
                db=db_session,
            )

        assert len(results) == 1
        assert results[0].document_title == "Unknown"

    async def test_top_k_limits_results(
        self, db_session: AsyncSession, researcher_user: User
    ):
        kb, doc = await _seed_kb_and_doc(db_session, researcher_user)

        mock_hits = [
            {"id": i, "score": 0.9 - i * 0.05, "document_id": str(doc.id), "chunk_index": i, "content": f"内容{i}"}
            for i in range(10)
        ]

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", return_value=mock_hits),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="测试",
                knowledge_base_ids=[str(kb.id)],
                top_k=3,
                min_score=0.0,
                db=db_session,
            )

        assert len(results) <= 3

    async def test_milvus_exception_skips_kb(
        self, db_session: AsyncSession, researcher_user: User
    ):
        """Milvus 异常时应跳过该 KB，不抛出错误。"""
        kb, _ = await _seed_kb_and_doc(db_session, researcher_user)

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", side_effect=Exception("Milvus连接失败")),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="测试",
                knowledge_base_ids=[str(kb.id)],
                top_k=10,
                min_score=0.5,
                db=db_session,
            )

        assert results == []

    async def test_batch_document_query_no_n_plus_1(
        self, db_session: AsyncSession, researcher_user: User
    ):
        """验证批量查询逻辑：多个 hit 共享同一 document_id 时只需一次查询。"""
        kb, doc = await _seed_kb_and_doc(db_session, researcher_user)

        mock_hits = [
            {"id": i, "score": 0.9, "document_id": str(doc.id), "chunk_index": i, "content": f"块{i}"}
            for i in range(5)
        ]

        query_count = 0
        original_execute = db_session.execute

        async def counting_execute(stmt, *args, **kwargs):
            nonlocal query_count
            query_count += 1
            return await original_execute(stmt, *args, **kwargs)

        db_session.execute = counting_execute  # type: ignore

        with (
            patch("meks.services.search_service.generate_embeddings", return_value=[[0.1] * 768]),
            patch("meks.services.search_service.search_vectors", return_value=mock_hits),
        ):
            from meks.services.search_service import execute_semantic_search

            results = await execute_semantic_search(
                query="测试",
                knowledge_base_ids=[str(kb.id)],
                top_k=10,
                min_score=0.0,
                db=db_session,
            )

        assert len(results) == 5
        # 查询次数应为固定值（KB查询 + 1次Document批量查询），而非每个 hit 一次
        # 总查询次数应远少于 hit 数量（5）
        assert query_count < 5

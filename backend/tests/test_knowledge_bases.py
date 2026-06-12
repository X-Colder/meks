"""知识库 API 测试：CRUD、IDOR 防护、可见性过滤。"""
import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from meks.models.knowledge_base import KBType, KnowledgeBase, Visibility
from meks.models.user import User
from tests.conftest import make_token


async def _create_kb_in_db(
    db: AsyncSession,
    owner: User,
    name: str = "测试知识库",
    visibility: Visibility = Visibility.public,
    department: str | None = None,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        name=name,
        description="测试描述",
        owner_id=owner.id,
        visibility=visibility,
        department=department or owner.department,
        milvus_collection=f"meks_kb_{uuid.uuid4().hex[:12]}",
        kb_type=KBType.literature,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


class TestCreateKnowledgeBase:
    async def test_researcher_can_create_kb(
        self, async_client: AsyncClient, researcher_user: User
    ):
        token = make_token(researcher_user)
        with patch("meks.api.v1.knowledge_bases.create_collection"):
            resp = await async_client.post(
                "/api/v1/knowledge-bases",
                json={"name": "新知识库", "visibility": "public", "kb_type": "literature"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "新知识库"
        assert data["owner_id"] == str(researcher_user.id)

    async def test_viewer_cannot_create_kb(
        self, async_client: AsyncClient, viewer_user: User
    ):
        token = make_token(viewer_user)
        resp = await async_client.post(
            "/api/v1/knowledge-bases",
            json={"name": "新知识库", "visibility": "public", "kb_type": "literature"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_doctor_cannot_create_kb(
        self, async_client: AsyncClient, doctor_user: User
    ):
        token = make_token(doctor_user)
        resp = await async_client.post(
            "/api/v1/knowledge-bases",
            json={"name": "新知识库", "visibility": "public", "kb_type": "literature"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestUpdateKnowledgeBase:
    async def test_owner_can_update_own_kb(
        self, async_client: AsyncClient, researcher_user: User, db_session: AsyncSession
    ):
        kb = await _create_kb_in_db(db_session, researcher_user)
        token = make_token(researcher_user)
        resp = await async_client.patch(
            f"/api/v1/knowledge-bases/{kb.id}",
            json={"name": "修改后名称"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "修改后名称"

    async def test_researcher_cannot_update_others_kb(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        admin_user: User,
        db_session: AsyncSession,
    ):
        """IDOR 防护：researcher 不能修改他人的知识库。"""
        kb = await _create_kb_in_db(db_session, admin_user)
        token = make_token(researcher_user)
        resp = await async_client.patch(
            f"/api/v1/knowledge-bases/{kb.id}",
            json={"name": "越权修改"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_admin_can_update_any_kb(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        admin_user: User,
        db_session: AsyncSession,
    ):
        kb = await _create_kb_in_db(db_session, researcher_user)
        token = make_token(admin_user)
        resp = await async_client.patch(
            f"/api/v1/knowledge-bases/{kb.id}",
            json={"name": "管理员修改"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "管理员修改"

    async def test_update_nonexistent_kb(
        self, async_client: AsyncClient, researcher_user: User
    ):
        token = make_token(researcher_user)
        resp = await async_client.patch(
            f"/api/v1/knowledge-bases/{uuid.uuid4()}",
            json={"name": "不存在"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestDeleteKnowledgeBase:
    async def test_owner_can_delete_own_kb(
        self, async_client: AsyncClient, researcher_user: User, db_session: AsyncSession
    ):
        kb = await _create_kb_in_db(db_session, researcher_user)
        token = make_token(researcher_user)
        with patch("meks.api.v1.knowledge_bases.drop_collection"):
            resp = await async_client.delete(
                f"/api/v1/knowledge-bases/{kb.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert "已删除" in resp.json()["detail"]

    async def test_researcher_cannot_delete_others_kb(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        admin_user: User,
        db_session: AsyncSession,
    ):
        """IDOR 防护：researcher 不能删除他人的知识库。"""
        kb = await _create_kb_in_db(db_session, admin_user)
        token = make_token(researcher_user)
        resp = await async_client.delete(
            f"/api/v1/knowledge-bases/{kb.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_admin_can_delete_any_kb(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        admin_user: User,
        db_session: AsyncSession,
    ):
        kb = await _create_kb_in_db(db_session, researcher_user)
        token = make_token(admin_user)
        with patch("meks.api.v1.knowledge_bases.drop_collection"):
            resp = await async_client.delete(
                f"/api/v1/knowledge-bases/{kb.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200

    async def test_viewer_cannot_delete_kb(
        self, async_client: AsyncClient, researcher_user: User, viewer_user: User, db_session: AsyncSession
    ):
        kb = await _create_kb_in_db(db_session, researcher_user)
        token = make_token(viewer_user)
        resp = await async_client.delete(
            f"/api/v1/knowledge-bases/{kb.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestListKnowledgeBases:
    async def test_public_kb_visible_to_all(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        doctor_user: User,
        db_session: AsyncSession,
    ):
        kb = await _create_kb_in_db(db_session, researcher_user, visibility=Visibility.public)
        token = make_token(doctor_user)
        resp = await async_client.get(
            "/api/v1/knowledge-bases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(kb.id) in ids

    async def test_private_kb_not_visible_to_others(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        doctor_user: User,
        db_session: AsyncSession,
    ):
        kb = await _create_kb_in_db(
            db_session, researcher_user, visibility=Visibility.private
        )
        token = make_token(doctor_user)
        resp = await async_client.get(
            "/api/v1/knowledge-bases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(kb.id) not in ids

    async def test_owner_can_see_own_private_kb(
        self, async_client: AsyncClient, researcher_user: User, db_session: AsyncSession
    ):
        kb = await _create_kb_in_db(
            db_session, researcher_user, visibility=Visibility.private
        )
        token = make_token(researcher_user)
        resp = await async_client.get(
            "/api/v1/knowledge-bases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(kb.id) in ids

    async def test_department_kb_visible_to_same_department(
        self,
        async_client: AsyncClient,
        researcher_user: User,
        db_session: AsyncSession,
    ):
        # researcher 的 department 是 "研究部"
        kb = await _create_kb_in_db(
            db_session,
            researcher_user,
            visibility=Visibility.department,
            department="研究部",
        )
        token = make_token(researcher_user)
        resp = await async_client.get(
            "/api/v1/knowledge-bases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert str(kb.id) in ids

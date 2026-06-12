"""RBAC 权限测试：角色权限边界、has_permission 函数。"""
import pytest

from meks.core.rbac import ROLE_PERMISSIONS, Permission, has_permission
from meks.models.user import UserRole


class TestHasPermission:
    def test_admin_has_all_permissions(self):
        for perm in Permission:
            assert has_permission(UserRole.admin, perm), f"admin 应拥有权限 {perm}"

    def test_viewer_has_only_read_permissions(self):
        allowed = {Permission.KB_READ, Permission.DOC_READ, Permission.SEARCH_EXECUTE}
        for perm in Permission:
            expected = perm in allowed
            assert has_permission(UserRole.viewer, perm) == expected, (
                f"viewer 对 {perm} 的权限结果不符合预期"
            )

    def test_viewer_cannot_create_kb(self):
        assert not has_permission(UserRole.viewer, Permission.KB_CREATE)

    def test_viewer_cannot_admin(self):
        assert not has_permission(UserRole.viewer, Permission.ADMIN_USERS)
        assert not has_permission(UserRole.viewer, Permission.ADMIN_AUDIT)
        assert not has_permission(UserRole.viewer, Permission.ADMIN_SYSTEM)

    def test_doctor_can_chat(self):
        assert has_permission(UserRole.doctor, Permission.CHAT_CREATE)
        assert has_permission(UserRole.doctor, Permission.CHAT_READ)

    def test_doctor_cannot_create_kb(self):
        assert not has_permission(UserRole.doctor, Permission.KB_CREATE)

    def test_doctor_cannot_upload_doc(self):
        assert not has_permission(UserRole.doctor, Permission.DOC_UPLOAD)

    def test_doctor_cannot_admin(self):
        assert not has_permission(UserRole.doctor, Permission.ADMIN_USERS)

    def test_researcher_can_manage_kb(self):
        assert has_permission(UserRole.researcher, Permission.KB_CREATE)
        assert has_permission(UserRole.researcher, Permission.KB_UPDATE)
        assert has_permission(UserRole.researcher, Permission.KB_DELETE)

    def test_researcher_can_upload_doc(self):
        assert has_permission(UserRole.researcher, Permission.DOC_UPLOAD)
        assert has_permission(UserRole.researcher, Permission.DOC_DELETE)

    def test_researcher_cannot_admin_users(self):
        assert not has_permission(UserRole.researcher, Permission.ADMIN_USERS)

    def test_unknown_role_returns_false(self):
        # 传入不存在的 role 应安全返回 False
        assert not has_permission("unknown_role", Permission.KB_READ)  # type: ignore


class TestRolePermissionsCompleteness:
    def test_all_roles_defined(self):
        """确保所有 UserRole 都有权限映射。"""
        for role in UserRole:
            assert role in ROLE_PERMISSIONS, f"角色 {role} 未在 ROLE_PERMISSIONS 中定义"

    def test_admin_permissions_is_full_set(self):
        admin_perms = ROLE_PERMISSIONS[UserRole.admin]
        all_perms = set(Permission)
        assert admin_perms == all_perms

    def test_researcher_is_subset_of_admin(self):
        assert ROLE_PERMISSIONS[UserRole.researcher].issubset(ROLE_PERMISSIONS[UserRole.admin])

    def test_doctor_is_subset_of_researcher(self):
        # doctor 的权限是 researcher 的子集（不含写操作）
        dr_perms = ROLE_PERMISSIONS[UserRole.doctor]
        re_perms = ROLE_PERMISSIONS[UserRole.researcher]
        assert dr_perms.issubset(re_perms)

    def test_viewer_is_subset_of_doctor(self):
        assert ROLE_PERMISSIONS[UserRole.viewer].issubset(ROLE_PERMISSIONS[UserRole.doctor])

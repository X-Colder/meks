from enum import Enum

from meks.models.user import UserRole


class Permission(str, Enum):
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"
    DOC_UPLOAD = "doc:upload"
    DOC_READ = "doc:read"
    DOC_DELETE = "doc:delete"
    DOC_REPROCESS = "doc:reprocess"
    SEARCH_EXECUTE = "search:execute"
    SEARCH_HISTORY = "search:history"
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"
    CHAT_DELETE = "chat:delete"
    ADMIN_USERS = "admin:users"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SYSTEM = "admin:system"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.admin: set(Permission),
    UserRole.researcher: {
        Permission.KB_CREATE,
        Permission.KB_READ,
        Permission.KB_UPDATE,
        Permission.KB_DELETE,
        Permission.DOC_UPLOAD,
        Permission.DOC_READ,
        Permission.DOC_DELETE,
        Permission.DOC_REPROCESS,
        Permission.SEARCH_EXECUTE,
        Permission.SEARCH_HISTORY,
        Permission.CHAT_CREATE,
        Permission.CHAT_READ,
        Permission.CHAT_DELETE,
    },
    UserRole.doctor: {
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.SEARCH_EXECUTE,
        Permission.SEARCH_HISTORY,
        Permission.CHAT_CREATE,
        Permission.CHAT_READ,
        Permission.CHAT_DELETE,
    },
    UserRole.viewer: {
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.SEARCH_EXECUTE,
    },
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())

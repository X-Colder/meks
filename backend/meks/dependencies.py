from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.core.exceptions import ForbiddenException, UnauthorizedException
from meks.core.rbac import Permission, has_permission
from meks.core.security import decode_token
from meks.models.base import get_db
from meks.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedException("无效的访问令牌")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException()

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException("用户不存在或已被禁用")

    return user


def require_permission(permission: Permission):
    async def checker(user: User = Depends(get_current_user)):
        if not has_permission(user.role, permission):
            raise ForbiddenException(f"需要权限: {permission.value}")
        return user

    return checker

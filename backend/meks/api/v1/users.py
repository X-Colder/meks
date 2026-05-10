from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.users import UserCreate, UserListResponse, UserResponse, UserUpdate
from meks.core.exceptions import ConflictException, NotFoundException
from meks.core.rbac import Permission
from meks.core.security import hash_password
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.user import User, UserRole

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return UserListResponse(items=users, total=len(users))


@router.post("", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(User).where((User.username == request.username) | (User.email == request.email))
    )
    if existing.scalar_one_or_none():
        raise ConflictException("用户名或邮箱已存在")

    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=UserRole(request.role),
        department=request.department,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise NotFoundException("用户")

    update_data = request.model_dump(exclude_unset=True)
    if "role" in update_data:
        update_data["role"] = UserRole(update_data["role"])
    for field, value in update_data.items():
        setattr(target_user, field, value)

    await db.commit()
    await db.refresh(target_user)
    return target_user

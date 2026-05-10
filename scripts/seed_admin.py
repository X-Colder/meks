"""Seed admin user script.

Usage: python scripts/seed_admin.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")

from meks.models.base import async_session
from meks.models.user import User, UserRole
from meks.core.security import hash_password


async def seed():
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("Admin user already exists.")
            return

        admin = User(
            username="admin",
            email="admin@meks.local",
            hashed_password=hash_password("admin123456"),
            full_name="系统管理员",
            role=UserRole.admin,
            department="信息科",
        )
        db.add(admin)
        await db.commit()
        print("Admin user created: admin / admin123456")


if __name__ == "__main__":
    asyncio.run(seed())

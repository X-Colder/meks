import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Enum, Boolean, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meks.models.base import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    researcher = "researcher"
    doctor = "doctor"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.doctor)
    department: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(nullable=True)

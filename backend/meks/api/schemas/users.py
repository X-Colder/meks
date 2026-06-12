from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "doctor"
    department: str | None = None


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    department: str | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    items: list["UserResponse"]
    total: int
    page: int = 1
    page_size: int = 20


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    department: str | None
    is_active: bool
    created_at: str
    last_login: str | None = None

    model_config = {"from_attributes": True}


class PasswordResetRequest(BaseModel):
    new_password: str

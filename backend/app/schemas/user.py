import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.employee
    department_id: int | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    role: UserRole | None = None
    department_id: int | None = None
    is_active: bool | None = None
    avatar_url: str | None = Field(None, max_length=500)
    password: str | None = Field(None, min_length=8, max_length=128)


class UserOut(UserBase):
    id: uuid.UUID
    is_active: bool
    avatar_url: str | None
    created_at: datetime
    department_name: str | None = None

    model_config = {"from_attributes": True}


class UserMe(UserOut):
    pass

from pydantic import BaseModel, Field


class UserListItemResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool
    role: str


class UserRevokedItemResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    revoked_at: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool
    role: str
    company_id: str


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = None
    is_active: bool | None = None

from pydantic import BaseModel, Field

from app.modules.auth.schemas import AuthenticatedUserResponse


class UserCompanyResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    role: str
    is_active: bool


class MembershipContextResponse(BaseModel):
    role: str


class UserContextResponse(BaseModel):
    user: AuthenticatedUserResponse
    active_company: UserCompanyResponse | None
    membership: MembershipContextResponse | None
    available_companies: list[UserCompanyResponse]
    requires_company_selection: bool


class MeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class MeResponse(BaseModel):
    id: str
    name: str
    email: str

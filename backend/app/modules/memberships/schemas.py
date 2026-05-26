from pydantic import BaseModel

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

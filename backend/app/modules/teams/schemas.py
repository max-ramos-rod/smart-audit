from pydantic import BaseModel, Field


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class TeamUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class TeamMemberAddRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)


class TeamMemberResponse(BaseModel):
    user_id: str
    name: str
    email: str


class TeamResponse(BaseModel):
    id: str
    company_id: str
    name: str
    members: list[TeamMemberResponse]


class TeamListItemResponse(BaseModel):
    id: str
    company_id: str
    name: str
    member_count: int

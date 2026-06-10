from pydantic import BaseModel, Field


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool | None = None


class ClientResponse(BaseModel):
    id: str
    name: str
    is_active: bool

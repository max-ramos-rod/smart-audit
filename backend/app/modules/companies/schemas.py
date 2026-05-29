from pydantic import BaseModel, Field


class CompanyUpdateRequest(BaseModel):
    name:          str | None = Field(default=None, min_length=2, max_length=150)
    cnpj:          str | None = Field(default=None, min_length=1, max_length=18)
    timezone:      str | None = Field(default=None, min_length=1, max_length=50)
    contact_email: str | None = Field(default=None, min_length=1, max_length=255)
    phone:         str | None = Field(default=None, min_length=1, max_length=30)


class CompanyResponse(BaseModel):
    id:            str
    name:          str
    slug:          str
    plan:          str
    is_active:     bool
    cnpj:          str | None
    timezone:      str | None
    contact_email: str | None
    phone:         str | None

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FormFieldCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=180)
    field_type: str = Field(min_length=1, max_length=30)
    required: bool = False
    position: int
    config_json: dict = Field(default_factory=dict)
    instruction: str | None = Field(default=None, min_length=1, max_length=1000)
    # Escopo de componente (DR-0002 Fases 2-4 / ADR-0016). NULL = campo geral.
    # A existência do tipo na empresa é validada no service (cross-context).
    component_type_id: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("config_json")
    @classmethod
    def validate_select_options(cls, v: dict, info) -> dict:
        if info.data.get("field_type") == "select":
            options = v.get("options", [])
            if not isinstance(options, list) or len(options) == 0:
                raise ValueError(
                    "Campo do tipo select deve ter ao menos uma opcao em config_json.options."
                )
        return v


class FormCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    fields: list[FormFieldCreateRequest]


class FormVersionPublishRequest(BaseModel):
    fields: list[FormFieldCreateRequest]


class FormFieldResponse(BaseModel):
    id: str
    key: str
    label: str
    field_type: str
    required: bool
    position: int
    config_json: dict
    instruction: str | None
    component_type_id: str | None = None


class FormVersionResponse(BaseModel):
    id: str
    version: int
    status: str
    published_at: datetime | None
    fields: list[FormFieldResponse]


class FormResponse(BaseModel):
    id: str
    company_id: str
    name: str
    description: str | None
    is_active: bool
    current_version: FormVersionResponse


class FormListItemResponse(BaseModel):
    id: str
    company_id: str
    name: str
    description: str | None
    is_active: bool
    current_version_number: int
    current_version_status: str
    published_at: datetime | None


class FormVersionListItemResponse(BaseModel):
    id: str
    version: int
    status: str
    published_at: datetime | None
    fields_count: int
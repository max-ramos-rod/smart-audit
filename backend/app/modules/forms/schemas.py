from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FormFieldCreateRequest(BaseModel):
    key: str
    label: str
    field_type: str
    required: bool = False
    position: int
    config_json: dict = Field(default_factory=dict)

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
    name: str
    description: str | None = None
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
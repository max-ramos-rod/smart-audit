from datetime import datetime

from pydantic import BaseModel, Field


class AttachmentCreateRequest(BaseModel):
    # Escopo derivado dos campos (DR-0017): sem field_key => evidência da inspeção
    # (scope='submission'); com field_key e sem asset_id => campo geral (scope='field');
    # com field_key e asset_id => componente (scope='component').
    field_key: str | None = Field(default=None, min_length=1, max_length=100)
    asset_id: str | None = Field(default=None, min_length=1, max_length=36)
    file_url: str = Field(min_length=1, max_length=2048)
    thumbnail_url: str | None = Field(default=None, min_length=1, max_length=2048)
    mime_type: str = Field(min_length=1, max_length=120)
    file_size: int
    metadata_json: dict | None = None


class AttachmentResponse(BaseModel):
    id: str
    submission_id: str | None
    scope: str
    field_key: str | None
    asset_id: str | None = None
    component_label: str | None = None
    file_url: str
    thumbnail_url: str | None
    mime_type: str
    file_size: int
    metadata_json: dict | None = None
    created_at: datetime

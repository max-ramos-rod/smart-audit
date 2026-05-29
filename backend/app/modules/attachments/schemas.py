from datetime import datetime

from pydantic import BaseModel, Field


class AttachmentCreateRequest(BaseModel):
    field_key: str = Field(min_length=1, max_length=100)
    file_url: str = Field(min_length=1, max_length=2048)
    thumbnail_url: str | None = Field(default=None, min_length=1, max_length=2048)
    mime_type: str = Field(min_length=1, max_length=120)
    file_size: int


class AttachmentResponse(BaseModel):
    id: str
    submission_id: str
    field_key: str
    file_url: str
    thumbnail_url: str | None
    mime_type: str
    file_size: int
    created_at: datetime
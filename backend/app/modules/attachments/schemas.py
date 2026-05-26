from datetime import datetime

from pydantic import BaseModel


class AttachmentCreateRequest(BaseModel):
    field_key: str
    file_url: str
    thumbnail_url: str | None = None
    mime_type: str
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
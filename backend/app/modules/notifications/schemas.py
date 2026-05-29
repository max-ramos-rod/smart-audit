from pydantic import BaseModel, Field


class MarkReadRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)


class MarkAllReadRequest(BaseModel):
    keys: list[str] = Field(min_length=1)

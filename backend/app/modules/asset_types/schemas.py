from typing import Any

from pydantic import BaseModel, Field


class AssetTypeCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    # Aceito livre na Fase 1 (M1): a coluna existe, mas attributes_json NAO e validado
    # contra este schema. Nao ha validacao de conteudo aqui.
    attributes_schema: dict[str, Any] | None = None


class AssetTypeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    attributes_schema: dict[str, Any] | None = None
    is_active: bool | None = None


class AssetTypeResponse(BaseModel):
    id: str
    name: str
    description: str | None
    attributes_schema: dict[str, Any] | None
    is_active: bool

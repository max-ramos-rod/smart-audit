from typing import Any, Literal

from pydantic import BaseModel, Field

AssetStatus = Literal["active", "inactive", "retired"]


class AssetCreateRequest(BaseModel):
    asset_type_id: str = Field(min_length=1, max_length=36)
    identifier: str = Field(min_length=2, max_length=180)
    # NULL = raiz; preenchido = componente. Imutavel apos o create (M5).
    parent_asset_id: str | None = Field(default=None, min_length=1, max_length=36)
    # So permitido em raiz (M6) — validado no service (V3) e reforcado pelo CHECK.
    client_id: str | None = Field(default=None, min_length=1, max_length=36)
    # Aceito livre na Fase 1 (M1): sem validacao contra attributes_schema.
    attributes_json: dict[str, Any] | None = None


class AssetUpdateRequest(BaseModel):
    identifier: str | None = Field(default=None, min_length=2, max_length=180)
    client_id: str | None = Field(default=None, min_length=1, max_length=36)
    attributes_json: dict[str, Any] | None = None
    status: AssetStatus | None = None
    # parent_asset_id e imutavel apos o create (M5/V2). O campo so existe aqui para
    # ser explicitamente rejeitado com 400 quando enviado — nunca e aplicado.
    parent_asset_id: str | None = Field(default=None, min_length=1, max_length=36)


class AssetResponse(BaseModel):
    id: str
    asset_type_id: str
    identifier: str
    parent_asset_id: str | None
    client_id: str | None
    attributes_json: dict[str, Any]
    status: str


class AssetDetailResponse(AssetResponse):
    components: list[AssetResponse]  # filhos diretos

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.pagination import PageMeta

T = TypeVar("T")


class ResponseEnvelope(BaseModel, Generic[T]):
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


class PaginatedResponseEnvelope(ResponseEnvelope[T], Generic[T]):
    # Override intencional do tipo de `meta` do envelope base (dict -> PageMeta).
    meta: PageMeta  # type: ignore[assignment]


def success_response(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return ResponseEnvelope[Any](data=data, meta=meta or {}).model_dump(mode="json")


def paginated_response(data: Any, meta: PageMeta) -> dict[str, Any]:
    return PaginatedResponseEnvelope[Any](data=data, meta=meta).model_dump(mode="json")

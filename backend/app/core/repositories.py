from __future__ import annotations

from abc import ABC
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams

ModelT = TypeVar("ModelT")
EntityT = TypeVar("EntityT")


class SQLAlchemyRepository(Generic[ModelT], ABC):
    model: type[ModelT]

    def list(self, db: Session, *, order_by: Any | None = None) -> list[ModelT]:
        statement = select(self.model)
        if order_by is not None:
            statement = statement.order_by(order_by)
        return self._list_from_stmt(db, statement)

    def get(self, db: Session, entity_id: Any) -> ModelT | None:
        return db.get(self.model, entity_id)

    def create(self, db: Session, entity: ModelT) -> ModelT:
        return self._save(db, entity)

    def update_fields(self, db: Session, entity: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            setattr(entity, key, value)
        db.add(entity)
        db.flush()
        return entity

    def delete(self, db: Session, entity: ModelT) -> None:
        db.delete(entity)
        db.flush()

    def _save(self, db: Session, entity: EntityT) -> EntityT:
        db.add(entity)
        db.flush()
        return entity

    def _save_many(self, db: Session, entities: list[EntityT]) -> list[EntityT]:
        db.add_all(entities)
        db.flush()
        return entities

    def _get_one(self, db: Session, statement: Select[Any]) -> Any:
        return db.scalar(statement)

    def _list_from_stmt(self, db: Session, statement: Select[Any], *, unique: bool = False) -> list[Any]:
        result = db.scalars(statement)
        if unique:
            result = result.unique()
        return list(result.all())

    def _paginate_select(
        self,
        db: Session,
        statement: Select[Any],
        params: PaginationParams,
        *,
        unique: bool = False,
    ) -> tuple[list[Any], int]:
        total = int(db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)
        paginated_statement = statement.offset((params.page - 1) * params.page_size).limit(params.page_size)
        items = self._list_from_stmt(db, paginated_statement, unique=unique)
        return items, total

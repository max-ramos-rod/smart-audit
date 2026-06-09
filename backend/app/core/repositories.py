from __future__ import annotations

from abc import ABC
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams

ModelT = TypeVar("ModelT")
EntityT = TypeVar("EntityT")


class SQLAlchemyRepository(Generic[ModelT], ABC):
    model: type[ModelT]

    async def get(self, db: AsyncSession, entity_id: Any) -> ModelT | None:
        return await db.get(self.model, entity_id)

    async def create(self, db: AsyncSession, entity: ModelT) -> ModelT:
        return await self._save(db, entity)

    async def update_fields(
        self, db: AsyncSession, entity: EntityT, data: dict[str, Any]
    ) -> EntityT:
        for key, value in data.items():
            setattr(entity, key, value)
        db.add(entity)
        await db.flush()
        return entity

    async def delete(self, db: AsyncSession, entity: EntityT) -> None:
        await db.delete(entity)
        await db.flush()

    async def _save(self, db: AsyncSession, entity: EntityT) -> EntityT:
        db.add(entity)
        await db.flush()
        return entity

    async def _save_many(self, db: AsyncSession, entities: list[EntityT]) -> list[EntityT]:
        db.add_all(entities)
        await db.flush()
        return entities

    async def _get_one(self, db: AsyncSession, statement: Select[Any]) -> Any:
        return await db.scalar(statement.execution_options(populate_existing=True))

    async def _list_from_stmt(
        self, db: AsyncSession, statement: Select[Any], *, unique: bool = False
    ) -> list[Any]:
        result = await db.scalars(statement.execution_options(populate_existing=True))
        if unique:
            result = result.unique()
        return list(result.all())

    async def _paginate_select(
        self,
        db: AsyncSession,
        statement: Select[Any],
        params: PaginationParams,
        *,
        unique: bool = False,
    ) -> tuple[list[Any], int]:
        total = int(
            await db.scalar(
                select(func.count()).select_from(statement.order_by(None).subquery())
            ) or 0
        )
        paginated_statement = (
            statement.offset((params.page - 1) * params.page_size).limit(params.page_size)
        )
        items = await self._list_from_stmt(db, paginated_statement, unique=unique)
        return items, total

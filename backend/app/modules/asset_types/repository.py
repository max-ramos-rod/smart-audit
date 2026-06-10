from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.asset_types import AssetType


class AssetTypeRepository(SQLAlchemyRepository[AssetType]):
    model = AssetType

    async def list_by_company(
        self,
        db: AsyncSession,
        company_id: str,
        params: PaginationParams,
        is_active: bool | None = None,
    ) -> tuple[list[AssetType], int]:
        statement = (
            select(AssetType)
            .where(AssetType.company_id == company_id)
            .order_by(AssetType.name)
        )
        if is_active is not None:
            statement = statement.where(AssetType.is_active.is_(is_active))
        return await self._paginate_select(db, statement, params)

    async def get_company_type(
        self, db: AsyncSession, asset_type_id: str, company_id: str
    ) -> AssetType | None:
        statement = select(AssetType).where(
            AssetType.id == asset_type_id, AssetType.company_id == company_id
        )
        return await self._get_one(db, statement)

    async def create_asset_type(self, db: AsyncSession, asset_type: AssetType) -> AssetType:
        return await self._save(db, asset_type)

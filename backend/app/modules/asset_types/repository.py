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

    async def filter_existing_ids(
        self, db: AsyncSession, company_id: str, ids: set[str]
    ) -> set[str]:
        """Retorna, dentre ``ids``, os que existem como tipos da empresa.

        Validação cross-context para o escopo de componente (DR-0002 T2): a diferença
        entre ``ids`` e o retorno são os tipos inválidos/de outra empresa.
        """
        if not ids:
            return set()
        statement = select(AssetType.id).where(
            AssetType.company_id == company_id, AssetType.id.in_(ids)
        )
        rows = await db.scalars(statement)
        return {str(row) for row in rows}

    async def create_asset_type(self, db: AsyncSession, asset_type: AssetType) -> AssetType:
        return await self._save(db, asset_type)

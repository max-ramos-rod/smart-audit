from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.assets import Asset


class AssetFilters:
    def __init__(
        self,
        asset_type_id: str | None = None,
        client_id: str | None = None,
        parent_asset_id: str | None = None,
        status: str | None = None,
    ) -> None:
        self.asset_type_id = asset_type_id
        self.client_id = client_id
        self.parent_asset_id = parent_asset_id
        self.status = status


class AssetRepository(SQLAlchemyRepository[Asset]):
    model = Asset

    async def list_by_company(
        self,
        db: AsyncSession,
        company_id: str,
        params: PaginationParams,
        filters: AssetFilters,
    ) -> tuple[list[Asset], int]:
        statement = select(Asset).where(Asset.company_id == company_id)
        if filters.asset_type_id is not None:
            statement = statement.where(Asset.asset_type_id == filters.asset_type_id)
        if filters.client_id is not None:
            statement = statement.where(Asset.client_id == filters.client_id)
        if filters.parent_asset_id is not None:
            statement = statement.where(Asset.parent_asset_id == filters.parent_asset_id)
        if filters.status is not None:
            statement = statement.where(Asset.status == filters.status)
        statement = statement.order_by(Asset.identifier)
        return await self._paginate_select(db, statement, params)

    async def get_company_asset(
        self, db: AsyncSession, asset_id: str, company_id: str
    ) -> Asset | None:
        statement = (
            select(Asset)
            .where(Asset.id == asset_id, Asset.company_id == company_id)
            .options(
                selectinload(Asset.components),
                selectinload(Asset.asset_type),
                selectinload(Asset.client),
            )
        )
        return await self._get_one(db, statement)

    async def create_asset(self, db: AsyncSession, asset: Asset) -> Asset:
        return await self._save(db, asset)

    async def list_subtree_components(
        self, db: AsyncSession, root_asset_id: str
    ) -> list[dict]:
        """Componentes ativos da subárvore de ``root_asset_id`` (exclui a raiz), via CTE.

        Usado pelo motor de expansão do checklist (DR-0002 T3): retorna, para cada
        componente, ``id``, ``identifier``, ``asset_type_id``, ``type_name`` e ``path``
        (cadeia de ancestrais a partir da raiz). Ordenado por ``path`` para render estável.
        """
        statement = text(
            """
            WITH RECURSIVE subtree AS (
                SELECT a.id, a.identifier, a.asset_type_id, a.parent_asset_id, a.status,
                       a.identifier::text AS path, 0 AS depth
                FROM assets a WHERE a.id = CAST(:root AS uuid)
                UNION ALL
                SELECT c.id, c.identifier, c.asset_type_id, c.parent_asset_id, c.status,
                       s.path || ' > ' || c.identifier, s.depth + 1
                FROM assets c JOIN subtree s ON c.parent_asset_id = s.id
            )
            SELECT s.id, s.identifier, s.asset_type_id, t.name AS type_name, s.path
            FROM subtree s JOIN asset_types t ON t.id = s.asset_type_id
            WHERE s.depth > 0 AND s.status = 'active'
            ORDER BY s.path
            """
        )
        result = await db.execute(statement, {"root": root_asset_id})
        return [dict(row) for row in result.mappings()]

    async def deactivate_subtree(self, db: AsyncSession, root_asset_id: str) -> int:
        """Desativa o no e toda a subarvore via CTE recursiva (M4/V6).

        Marca ``status='inactive'`` na raiz e em todos os descendentes, na mesma
        transacao (sem commit aqui — o service comita). Retorna a contagem de
        **descendentes** afetados (exclui a propria raiz), para a auditoria.
        """
        statement = text(
            """
            WITH RECURSIVE subtree AS (
                SELECT id FROM assets WHERE id = CAST(:root AS uuid)
                UNION ALL
                SELECT a.id FROM assets a JOIN subtree s ON a.parent_asset_id = s.id
            )
            UPDATE assets
            SET status = 'inactive', updated_at = now()
            WHERE id IN (SELECT id FROM subtree)
            RETURNING id
            """
        )
        result = await db.execute(statement, {"root": root_asset_id})
        return len(result.fetchall()) - 1

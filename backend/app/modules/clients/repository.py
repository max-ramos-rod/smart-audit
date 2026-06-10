from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.clients import Client


class ClientRepository(SQLAlchemyRepository[Client]):
    model = Client

    async def list_by_company(
        self,
        db: AsyncSession,
        company_id: str,
        params: PaginationParams,
        is_active: bool | None = None,
    ) -> tuple[list[Client], int]:
        statement = (
            select(Client)
            .where(Client.company_id == company_id)
            .order_by(Client.name)
        )
        if is_active is not None:
            statement = statement.where(Client.is_active.is_(is_active))
        return await self._paginate_select(db, statement, params)

    async def get_company_client(
        self, db: AsyncSession, client_id: str, company_id: str
    ) -> Client | None:
        statement = select(Client).where(
            Client.id == client_id, Client.company_id == company_id
        )
        return await self._get_one(db, statement)

    async def create_client(self, db: AsyncSession, client: Client) -> Client:
        return await self._save(db, client)

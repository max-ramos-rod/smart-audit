from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.clients import Client
from app.db.models.memberships import Membership
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.clients.repository import ClientRepository
from app.modules.clients.schemas import (
    ClientCreateRequest,
    ClientResponse,
    ClientUpdateRequest,
)


class ClientService:
    def __init__(
        self,
        repository: ClientRepository | None = None,
        audit_repository: AuditLogRepository | None = None,
    ) -> None:
        self.repository = repository or ClientRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    async def list_clients(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
        is_active: bool | None = None,
    ) -> tuple[list[ClientResponse], PageMeta]:
        active_filter = True if is_active is None else is_active
        clients, total = await self.repository.list_by_company(
            db, str(membership.company_id), params, is_active=active_filter
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize(c) for c in clients], meta

    async def get_client(
        self, db: AsyncSession, membership: Membership, client_id: str
    ) -> ClientResponse:
        client = await self._get_or_404(db, membership, client_id)
        return self._serialize(client)

    async def create_client(
        self,
        db: AsyncSession,
        membership: Membership,
        payload: ClientCreateRequest,
    ) -> ClientResponse:
        client = Client(company_id=membership.company_id, name=payload.name)
        await self.repository.create_client(db, client)
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="client.created",
            meta={"client_name": client.name},
        )
        await db.commit()
        loaded = await self.repository.get_company_client(
            db, str(client.id), str(membership.company_id)
        )
        assert loaded is not None
        return self._serialize(loaded)

    async def update_client(
        self,
        db: AsyncSession,
        membership: Membership,
        client_id: str,
        payload: ClientUpdateRequest,
    ) -> ClientResponse:
        client = await self._get_or_404(db, membership, client_id)
        data = payload.model_dump(exclude_unset=True)
        if data:
            await self.repository.update_fields(db, client, data)
        await db.commit()
        loaded = await self.repository.get_company_client(
            db, client_id, str(membership.company_id)
        )
        assert loaded is not None
        return self._serialize(loaded)

    async def deactivate_client(
        self, db: AsyncSession, membership: Membership, client_id: str
    ) -> None:
        client = await self._get_or_404(db, membership, client_id)
        await self.repository.update_fields(db, client, {"is_active": False})
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="client.deactivated",
            meta={"client_name": client.name},
        )
        await db.commit()

    async def _get_or_404(
        self, db: AsyncSession, membership: Membership, client_id: str
    ) -> Client:
        client = await self.repository.get_company_client(
            db, client_id, str(membership.company_id)
        )
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado."
            )
        return client

    @staticmethod
    def _serialize(client: Client) -> ClientResponse:
        return ClientResponse(
            id=str(client.id),
            name=client.name,
            is_active=client.is_active,
        )

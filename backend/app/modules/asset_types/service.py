from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.asset_types import AssetType
from app.db.models.memberships import Membership
from app.modules.asset_types.repository import AssetTypeRepository
from app.modules.asset_types.schemas import (
    AssetTypeCreateRequest,
    AssetTypeResponse,
    AssetTypeUpdateRequest,
)
from app.modules.audit_logs.repository import AuditLogRepository


class AssetTypeService:
    def __init__(
        self,
        repository: AssetTypeRepository | None = None,
        audit_repository: AuditLogRepository | None = None,
    ) -> None:
        self.repository = repository or AssetTypeRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    async def list_asset_types(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
        is_active: bool | None = None,
    ) -> tuple[list[AssetTypeResponse], PageMeta]:
        active_filter = True if is_active is None else is_active
        asset_types, total = await self.repository.list_by_company(
            db, str(membership.company_id), params, is_active=active_filter
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize(t) for t in asset_types], meta

    async def get_asset_type(
        self, db: AsyncSession, membership: Membership, asset_type_id: str
    ) -> AssetTypeResponse:
        asset_type = await self._get_or_404(db, membership, asset_type_id)
        return self._serialize(asset_type)

    async def create_asset_type(
        self,
        db: AsyncSession,
        membership: Membership,
        payload: AssetTypeCreateRequest,
    ) -> AssetTypeResponse:
        asset_type = AssetType(
            company_id=membership.company_id,
            name=payload.name,
            description=payload.description,
            attributes_schema=payload.attributes_schema,
        )
        await self.repository.create_asset_type(db, asset_type)
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="asset_type.created",
            meta={"asset_type_name": asset_type.name},
        )
        await db.commit()
        loaded = await self.repository.get_company_type(
            db, str(asset_type.id), str(membership.company_id)
        )
        assert loaded is not None
        return self._serialize(loaded)

    async def update_asset_type(
        self,
        db: AsyncSession,
        membership: Membership,
        asset_type_id: str,
        payload: AssetTypeUpdateRequest,
    ) -> AssetTypeResponse:
        asset_type = await self._get_or_404(db, membership, asset_type_id)
        data = payload.model_dump(exclude_unset=True)
        if data:
            await self.repository.update_fields(db, asset_type, data)
        await db.commit()
        loaded = await self.repository.get_company_type(
            db, asset_type_id, str(membership.company_id)
        )
        assert loaded is not None
        return self._serialize(loaded)

    async def deactivate_asset_type(
        self, db: AsyncSession, membership: Membership, asset_type_id: str
    ) -> None:
        asset_type = await self._get_or_404(db, membership, asset_type_id)
        await self.repository.update_fields(db, asset_type, {"is_active": False})
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="asset_type.deactivated",
            meta={"asset_type_name": asset_type.name},
        )
        await db.commit()

    async def _get_or_404(
        self, db: AsyncSession, membership: Membership, asset_type_id: str
    ) -> AssetType:
        asset_type = await self.repository.get_company_type(
            db, asset_type_id, str(membership.company_id)
        )
        if asset_type is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de ativo nao encontrado.",
            )
        return asset_type

    @staticmethod
    def _serialize(asset_type: AssetType) -> AssetTypeResponse:
        return AssetTypeResponse(
            id=str(asset_type.id),
            name=asset_type.name,
            description=asset_type.description,
            attributes_schema=asset_type.attributes_schema,
            is_active=asset_type.is_active,
        )

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.assets import Asset
from app.db.models.memberships import Membership
from app.modules.asset_types.repository import AssetTypeRepository
from app.modules.assets.repository import AssetFilters, AssetRepository
from app.modules.assets.schemas import (
    AssetCreateRequest,
    AssetDetailResponse,
    AssetResponse,
    AssetUpdateRequest,
)
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.clients.repository import ClientRepository


class AssetService:
    def __init__(
        self,
        repository: AssetRepository | None = None,
        asset_type_repository: AssetTypeRepository | None = None,
        client_repository: ClientRepository | None = None,
        audit_repository: AuditLogRepository | None = None,
    ) -> None:
        self.repository = repository or AssetRepository()
        self.asset_type_repository = asset_type_repository or AssetTypeRepository()
        self.client_repository = client_repository or ClientRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    async def list_assets(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
        filters: AssetFilters,
    ) -> tuple[list[AssetResponse], PageMeta]:
        assets, total = await self.repository.list_by_company(
            db, str(membership.company_id), params, filters
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize(a) for a in assets], meta

    async def get_asset(
        self, db: AsyncSession, membership: Membership, asset_id: str
    ) -> AssetDetailResponse:
        asset = await self._get_or_404(db, membership, asset_id)
        return self._serialize_detail(asset)

    async def create_asset(
        self,
        db: AsyncSession,
        membership: Membership,
        payload: AssetCreateRequest,
    ) -> AssetDetailResponse:
        company_id = str(membership.company_id)

        # V8: o tipo deve existir, pertencer a empresa e estar ativo.
        asset_type = await self.asset_type_repository.get_company_type(
            db, payload.asset_type_id, company_id
        )
        if asset_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de ativo invalido."
            )
        if not asset_type.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de ativo esta arquivado.",
            )

        # V3 (M6): client_id so e aceito em ativo raiz (sem pai).
        if payload.parent_asset_id is not None and payload.client_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="client_id so e permitido em ativo raiz.",
            )

        # V1: o pai deve existir e pertencer a mesma empresa.
        if payload.parent_asset_id is not None:
            parent = await self.repository.get_company_asset(
                db, payload.parent_asset_id, company_id
            )
            if parent is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Ativo pai invalido."
                )

        # V1 + V9: o cliente deve existir, pertencer a empresa e estar ativo.
        if payload.client_id is not None:
            await self._validate_client(db, payload.client_id, company_id)

        asset = Asset(
            company_id=membership.company_id,
            asset_type_id=payload.asset_type_id,
            identifier=payload.identifier,
            parent_asset_id=payload.parent_asset_id,
            client_id=payload.client_id,
            attributes_json=payload.attributes_json or {},
        )
        await self.repository.create_asset(db, asset)
        await self.audit_repository.log(
            db,
            company_id=company_id,
            actor_id=str(membership.user_id),
            action="asset.created",
            meta={"identifier": asset.identifier},
        )
        await db.commit()
        loaded = await self.repository.get_company_asset(db, str(asset.id), company_id)
        assert loaded is not None
        return self._serialize_detail(loaded)

    async def update_asset(
        self,
        db: AsyncSession,
        membership: Membership,
        asset_id: str,
        payload: AssetUpdateRequest,
    ) -> AssetDetailResponse:
        company_id = str(membership.company_id)
        asset = await self._get_or_404(db, membership, asset_id)
        fields_set = payload.model_fields_set

        # V2 (M5): parent_asset_id e imutavel apos o create.
        if "parent_asset_id" in fields_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parent_asset_id e imutavel apos a criacao.",
            )

        data: dict[str, object] = {}
        if "identifier" in fields_set and payload.identifier is not None:
            data["identifier"] = payload.identifier
        if "attributes_json" in fields_set and payload.attributes_json is not None:
            data["attributes_json"] = payload.attributes_json
        if "status" in fields_set and payload.status is not None:
            # V7 (reativacao top-down — M4): so pode reativar (status='active') se for
            # raiz ou se o pai estiver active. Reativar nao cascateia para os filhos.
            if payload.status == "active" and asset.parent_asset_id is not None:
                parent = await self.repository.get_company_asset(
                    db, str(asset.parent_asset_id), company_id
                )
                if parent is None or parent.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nao e possivel reativar: o ativo pai esta inativo.",
                    )
            data["status"] = payload.status
        if "client_id" in fields_set:
            # V3 (M6): client_id so em ativo raiz.
            if payload.client_id is not None and asset.parent_asset_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="client_id so e permitido em ativo raiz.",
                )
            if payload.client_id is not None:
                await self._validate_client(db, payload.client_id, company_id)
            data["client_id"] = payload.client_id

        if data:
            await self.repository.update_fields(db, asset, data)
        await db.commit()
        loaded = await self.repository.get_company_asset(db, asset_id, company_id)
        assert loaded is not None
        return self._serialize_detail(loaded)

    async def deactivate_asset(
        self, db: AsyncSession, membership: Membership, asset_id: str
    ) -> None:
        asset = await self._get_or_404(db, membership, asset_id)
        # V6 (soft delete de arvore — M4): desativa o ativo e toda a subarvore na mesma
        # transacao. Invariante: nenhum ativo 'active' sob ancestral 'inactive'.
        descendants = await self.repository.deactivate_subtree(db, str(asset.id))
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="asset.deactivated",
            meta={"identifier": asset.identifier, "descendants": descendants},
        )
        await db.commit()

    async def _validate_client(
        self, db: AsyncSession, client_id: str, company_id: str
    ) -> None:
        client = await self.client_repository.get_company_client(db, client_id, company_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente invalido."
            )
        if not client.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente esta inativo."
            )

    async def _get_or_404(
        self, db: AsyncSession, membership: Membership, asset_id: str
    ) -> Asset:
        asset = await self.repository.get_company_asset(
            db, asset_id, str(membership.company_id)
        )
        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ativo nao encontrado."
            )
        return asset

    @staticmethod
    def _serialize(asset: Asset) -> AssetResponse:
        return AssetResponse(
            id=str(asset.id),
            asset_type_id=str(asset.asset_type_id),
            identifier=asset.identifier,
            parent_asset_id=str(asset.parent_asset_id) if asset.parent_asset_id else None,
            client_id=str(asset.client_id) if asset.client_id else None,
            attributes_json=asset.attributes_json,
            status=asset.status,
        )

    @classmethod
    def _serialize_detail(cls, asset: Asset) -> AssetDetailResponse:
        base = cls._serialize(asset)
        return AssetDetailResponse(
            **base.model_dump(),
            components=[cls._serialize(c) for c in asset.components],
        )

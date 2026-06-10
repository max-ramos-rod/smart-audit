from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.asset_types.schemas import (
    AssetTypeCreateRequest,
    AssetTypeUpdateRequest,
)
from app.modules.asset_types.service import AssetTypeService
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_manager_membership

router = APIRouter(prefix="/asset-types", tags=["asset-types"])


def get_asset_type_service() -> AssetTypeService:
    return AssetTypeService()


@router.get("")
async def list_asset_types(
    is_active: bool | None = None,
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetTypeService = Depends(get_asset_type_service),
) -> dict[str, object]:
    data, meta = await service.list_asset_types(db, membership, params, is_active)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("")
async def create_asset_type(
    payload: AssetTypeCreateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetTypeService = Depends(get_asset_type_service),
) -> dict[str, object]:
    data = await service.create_asset_type(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{asset_type_id}")
async def get_asset_type(
    asset_type_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetTypeService = Depends(get_asset_type_service),
) -> dict[str, object]:
    data = await service.get_asset_type(db, membership, asset_type_id)
    return success_response(data.model_dump(mode="json"))


@router.patch("/{asset_type_id}")
async def update_asset_type(
    asset_type_id: str,
    payload: AssetTypeUpdateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetTypeService = Depends(get_asset_type_service),
) -> dict[str, object]:
    data = await service.update_asset_type(db, membership, asset_type_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{asset_type_id}")
async def delete_asset_type(
    asset_type_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetTypeService = Depends(get_asset_type_service),
) -> dict[str, object]:
    await service.deactivate_asset_type(db, membership, asset_type_id)
    return success_response(None)

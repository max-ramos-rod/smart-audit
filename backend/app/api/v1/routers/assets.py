from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.assets.repository import AssetFilters
from app.modules.assets.schemas import AssetCreateRequest, AssetUpdateRequest
from app.modules.assets.service import AssetService
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_manager_membership

router = APIRouter(prefix="/assets", tags=["assets"])


def get_asset_service() -> AssetService:
    return AssetService()


@router.get("")
async def list_assets(
    asset_type_id: str | None = None,
    client_id: str | None = None,
    parent_asset_id: str | None = None,
    status: str | None = None,
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetService = Depends(get_asset_service),
) -> dict[str, object]:
    filters = AssetFilters(
        asset_type_id=asset_type_id,
        client_id=client_id,
        parent_asset_id=parent_asset_id,
        status=status,
    )
    data, meta = await service.list_assets(db, membership, params, filters)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("")
async def create_asset(
    payload: AssetCreateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetService = Depends(get_asset_service),
) -> dict[str, object]:
    data = await service.create_asset(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetService = Depends(get_asset_service),
) -> dict[str, object]:
    data = await service.get_asset(db, membership, asset_id)
    return success_response(data.model_dump(mode="json"))


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: str,
    payload: AssetUpdateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetService = Depends(get_asset_service),
) -> dict[str, object]:
    data = await service.update_asset(db, membership, asset_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: AssetService = Depends(get_asset_service),
) -> dict[str, object]:
    await service.deactivate_asset(db, membership, asset_id)
    return success_response(None)

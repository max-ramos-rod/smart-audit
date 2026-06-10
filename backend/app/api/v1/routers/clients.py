from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.clients.schemas import ClientCreateRequest, ClientUpdateRequest
from app.modules.clients.service import ClientService
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_manager_membership

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client_service() -> ClientService:
    return ClientService()


@router.get("")
async def list_clients(
    is_active: bool | None = None,
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: ClientService = Depends(get_client_service),
) -> dict[str, object]:
    data, meta = await service.list_clients(db, membership, params, is_active)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("")
async def create_client(
    payload: ClientCreateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: ClientService = Depends(get_client_service),
) -> dict[str, object]:
    data = await service.create_client(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: ClientService = Depends(get_client_service),
) -> dict[str, object]:
    data = await service.get_client(db, membership, client_id)
    return success_response(data.model_dump(mode="json"))


@router.patch("/{client_id}")
async def update_client(
    client_id: str,
    payload: ClientUpdateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: ClientService = Depends(get_client_service),
) -> dict[str, object]:
    data = await service.update_client(db, membership, client_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: ClientService = Depends(get_client_service),
) -> dict[str, object]:
    await service.deactivate_client(db, membership, client_id)
    return success_response(None)

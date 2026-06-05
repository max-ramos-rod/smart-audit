from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.models.users import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.forms.importer import parse_import_file
from app.modules.forms.schemas import FormCreateRequest, FormVersionPublishRequest
from app.modules.forms.service import FormService
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_manager_membership

router = APIRouter(prefix="/forms", tags=["forms"])


def get_form_service() -> FormService:
    return FormService()


@router.get("")
async def list_forms(
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    data, meta = await form_service.list_forms(db, membership, params)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("/import")
async def import_form(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    content = await file.read()
    payload = parse_import_file(content, file.filename or "formulario.csv", name)
    data = await form_service.create_form(db, membership, current_user, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{form_id}")
async def get_form(
    form_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    data = await form_service.get_form(db, membership, form_id)
    return success_response(data.model_dump(mode="json"))


@router.post("")
async def create_form(
    payload: FormCreateRequest,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    data = await form_service.create_form(db, membership, current_user, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{form_id}/versions")
async def list_form_versions(
    form_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    data = await form_service.list_versions(db, membership, form_id)
    return success_response([item.model_dump(mode="json") for item in data])


@router.get("/{form_id}/versions/{version_id}")
async def get_form_version(
    form_id: str,
    version_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    data = await form_service.get_version(db, membership, form_id, version_id)
    return success_response(data.model_dump(mode="json"))


@router.post("/{form_id}/versions")
async def publish_new_version(
    form_id: str,
    payload: FormVersionPublishRequest,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    form_service: FormService = Depends(get_form_service),
) -> dict[str, object]:
    data = await form_service.publish_new_version(db, membership, current_user, form_id, payload)
    return success_response(data.model_dump(mode="json"))

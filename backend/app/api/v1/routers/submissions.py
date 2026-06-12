from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.models.users import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_operator_membership
from app.modules.submissions.schemas import (
    SubmissionAnswersUpdateRequest,
    SubmissionConformityUpdateRequest,
    SubmissionCreateRequest,
)
from app.modules.submissions.service import SubmissionService

router = APIRouter(prefix="/submissions", tags=["submissions"])


def get_submission_service() -> SubmissionService:
    return SubmissionService()


@router.get("")
async def list_submissions(
    params: PaginationParams = Depends(),
    status: str | None = Query(default=None),
    form_id: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    asset_id: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data, meta = await submission_service.list_submissions(
        db,
        membership,
        params,
        status=status,
        form_id=form_id,
        created_by=created_by,
        asset_id=asset_id,
        client_id=client_id,
    )
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.get("/export")
async def export_submissions_csv(
    status: str | None = Query(default=None),
    form_id: str | None = Query(default=None),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> Response:
    from datetime import date as _date
    csv_bytes = await submission_service.export_csv(db, membership, status=status, form_id=form_id)
    filename = f"inspecoes_{_date.today().isoformat()}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("")
async def create_submission(
    payload: SubmissionCreateRequest,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_operator_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.create_submission(db, membership, current_user, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{submission_id}")
async def get_submission(
    submission_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.get_submission(db, membership, submission_id)
    return success_response(data.model_dump(mode="json"))


@router.put("/{submission_id}/answers")
async def save_answers(
    submission_id: str,
    payload: SubmissionAnswersUpdateRequest,
    membership: Membership = Depends(get_operator_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.save_answers(db, membership, submission_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{submission_id}/export")
async def export_submission_pdf(
    submission_id: str,
    inline: bool = Query(default=False),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> Response:
    pdf_bytes = await submission_service.export_pdf(db, membership, submission_id)
    disposition = "inline" if inline else f'attachment; filename="inspecao-{submission_id}.pdf"'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition},
    )


@router.put("/{submission_id}/conformity")
async def save_conformity(
    submission_id: str,
    payload: SubmissionConformityUpdateRequest,
    membership: Membership = Depends(get_operator_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.save_conformity(db, membership, submission_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.post("/{submission_id}/finish")
async def finish_submission(
    submission_id: str,
    membership: Membership = Depends(get_operator_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.finish_submission(db, membership, submission_id)
    return success_response(data.model_dump(mode="json"))

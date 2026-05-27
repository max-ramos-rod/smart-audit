from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.form_versions import FormVersion
from app.db.models.forms import Form
from app.db.models.submissions import Submission
from app.modules.forms.service import FormService
from app.modules.search.schemas import SearchResponse
from app.modules.submissions.service import SubmissionService

_LIMIT = 10


class SearchService:
    async def search(
        self, db: AsyncSession, company_id: str, q: str
    ) -> SearchResponse:
        term = f"%{q.strip()}%"

        forms_stmt = (
            select(Form)
            .where(Form.company_id == company_id, Form.name.ilike(term))
            .options(selectinload(Form.versions))
            .order_by(Form.created_at.desc())
            .limit(_LIMIT)
            .execution_options(populate_existing=True)
        )
        forms_result = await db.scalars(forms_stmt)
        forms = list(forms_result.unique().all())
        # serialize forms before the submissions query — populate_existing=True in the
        # subs query would expire Form.versions on already-loaded objects, causing a
        # lazy-load attempt (MissingGreenlet) when serialize_form_list_item accesses them.
        form_dtos = [FormService.serialize_form_list_item(f) for f in forms]

        matching_versions = (
            select(FormVersion.id)
            .join(Form, FormVersion.form_id == Form.id)
            .where(Form.name.ilike(term))
            .scalar_subquery()
        )
        subs_stmt = (
            select(Submission)
            .where(
                Submission.company_id == company_id,
                Submission.form_version_id.in_(matching_versions),
            )
            .options(selectinload(Submission.form_version).selectinload(FormVersion.form))
            .order_by(Submission.started_at.desc())
            .limit(_LIMIT)
            .execution_options(populate_existing=True)
        )
        subs_result = await db.scalars(subs_stmt)
        submissions = list(subs_result.unique().all())

        return SearchResponse(
            forms=form_dtos,
            submissions=[SubmissionService.serialize_submission_list_item(s) for s in submissions],
        )

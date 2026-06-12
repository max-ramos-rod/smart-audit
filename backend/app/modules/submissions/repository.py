from datetime import UTC, datetime, timedelta

from sqlalchemy import Numeric, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.assets import Asset
from app.db.models.form_versions import FormVersion
from app.db.models.forms import Form
from app.db.models.submission_conformities import SubmissionConformity
from app.db.models.submission_values import SubmissionValue
from app.db.models.submissions import Submission


class SubmissionRepository(SQLAlchemyRepository[Submission]):
    model = Submission

    async def get_form_by_id(
        self, db: AsyncSession, company_id: str, form_id: str
    ) -> Form | None:
        statement = (
            select(Form)
            .where(Form.company_id == company_id, Form.id == form_id)
            .options(selectinload(Form.versions).selectinload(FormVersion.fields))
        )
        return await self._get_one(db, statement)

    async def create_submission(self, db: AsyncSession, submission: Submission) -> Submission:
        return await self._save(db, submission)

    async def get_submission(
        self, db: AsyncSession, company_id: str, submission_id: str
    ) -> Submission | None:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id, Submission.id == submission_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.fields),
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
                selectinload(Submission.conformities).selectinload(SubmissionConformity.form_field),
                selectinload(Submission.asset),
            )
        )
        return await self._get_one(db, statement)

    async def list_submissions(
        self,
        db: AsyncSession,
        company_id: str,
        params: PaginationParams,
        status: str | None = None,
        form_id: str | None = None,
        created_by: str | None = None,
        asset_id: str | None = None,
        client_id: str | None = None,
    ) -> tuple[list[Submission], int]:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
                selectinload(Submission.asset),
            )
            .order_by(Submission.created_at.desc())
        )
        if status:
            statement = statement.where(Submission.status == status)
        if form_id:
            statement = statement.join(
                FormVersion, Submission.form_version_id == FormVersion.id
            ).where(FormVersion.form_id == form_id)
        if created_by:
            statement = statement.where(Submission.created_by == created_by)
        if asset_id:
            statement = statement.where(Submission.asset_id == asset_id)
        if client_id:
            # Inspeções cujo ativo vinculado pertence ao cliente (DR-0002 / ClientDetailView).
            # Join via assets: inspeções sem ativo (asset_id NULL) são naturalmente excluídas.
            statement = statement.join(Asset, Submission.asset_id == Asset.id).where(
                Asset.client_id == client_id
            )
        return await self._paginate_select(db, statement, params)

    async def get_submission_for_export(
        self, db: AsyncSession, company_id: str, submission_id: str
    ) -> Submission | None:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id, Submission.id == submission_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.fields),
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
                selectinload(Submission.creator),
                selectinload(Submission.company),
                selectinload(Submission.conformities).selectinload(SubmissionConformity.form_field),
            )
        )
        return await self._get_one(db, statement)

    async def get_conformity(
        self,
        db: AsyncSession,
        submission_id: str,
        form_field_id: str,
        asset_id: str | None = None,
    ) -> SubmissionConformity | None:
        statement = select(SubmissionConformity).where(
            SubmissionConformity.submission_id == submission_id,
            SubmissionConformity.form_field_id == form_field_id,
            SubmissionConformity.asset_id == asset_id
            if asset_id is not None
            else SubmissionConformity.asset_id.is_(None),
        )
        return await self._get_one(db, statement)

    async def save_conformity(
        self, db: AsyncSession, conformity: SubmissionConformity
    ) -> SubmissionConformity:
        return await self._save(db, conformity)

    async def get_submission_value_by_field_id(
        self,
        db: AsyncSession,
        submission_id: str,
        form_field_id: str,
        asset_id: str | None = None,
    ) -> SubmissionValue | None:
        statement = select(SubmissionValue).where(
            SubmissionValue.submission_id == submission_id,
            SubmissionValue.form_field_id == form_field_id,
            SubmissionValue.asset_id == asset_id
            if asset_id is not None
            else SubmissionValue.asset_id.is_(None),
        )
        return await self._get_one(db, statement)

    async def save_submission_value(
        self, db: AsyncSession, submission_value: SubmissionValue
    ) -> SubmissionValue:
        return await self._save(db, submission_value)

    async def list_all_for_export(
        self,
        db: AsyncSession,
        company_id: str,
        status: str | None = None,
        form_id: str | None = None,
    ) -> list[Submission]:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id)
            .options(selectinload(Submission.form_version).selectinload(FormVersion.form))
            .order_by(Submission.started_at.desc())
            .limit(5000)
        )
        if status:
            statement = statement.where(Submission.status == status)
        if form_id:
            statement = statement.where(
                Submission.form_version_id.in_(
                    select(FormVersion.id).where(FormVersion.form_id == form_id)
                )
            )
        return await self._list_from_stmt(db, statement)

    async def list_for_notifications(
        self,
        db: AsyncSession,
        company_id: str,
        pending_threshold: datetime,
        completed_since: datetime,
    ) -> list[Submission]:
        statement = (
            select(Submission)
            .where(
                Submission.company_id == company_id,
                or_(
                    and_(
                        Submission.status == "in_progress",
                        Submission.started_at < pending_threshold,
                    ),
                    and_(
                        Submission.status == "completed",
                        Submission.finished_at >= completed_since,
                        Submission.score.isnot(None),
                    ),
                ),
            )
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.form),
            )
            .order_by(Submission.started_at.desc())
            .limit(50)
        )
        return await self._list_from_stmt(db, statement)

    async def get_company_stats(
        self, db: AsyncSession, company_id: str, since: datetime | None = None
    ) -> dict:
        filters = [Submission.company_id == company_id]
        if since:
            filters.append(Submission.started_at >= since)
        result = await db.execute(
            select(
                func.count().label("total"),
                func.count(case((Submission.status == "completed", 1))).label("completed"),
                func.count(case((Submission.status == "in_progress", 1))).label("in_progress"),
                func.avg(
                    case((Submission.status == "completed", Submission.score))
                ).label("avg_score"),
            ).where(*filters)
        )
        row = result.one()
        return {
            "total": row.total,
            "completed": row.completed,
            "in_progress": row.in_progress,
            "avg_score": round(float(row.avg_score), 2) if row.avg_score is not None else None,
        }

    async def get_score_by_form(
        self, db: AsyncSession, company_id: str, since: datetime | None = None
    ) -> list[dict]:
        filters = [
            Submission.company_id == company_id,
            Submission.status == "completed",
            Submission.score.is_not(None),
        ]
        if since:
            filters.append(Submission.finished_at >= since)
        result = await db.execute(
            select(
                Form.id.label("form_id"),
                Form.name.label("form_name"),
                func.count().label("count"),
                func.avg(Submission.score).label("avg_score"),
            )
            .join(FormVersion, Submission.form_version_id == FormVersion.id)
            .join(Form, FormVersion.form_id == Form.id)
            .where(*filters)
            .group_by(Form.id, Form.name)
            .order_by(func.avg(Submission.score).asc())
            .limit(10)
        )
        return [
            {
                "form_id": str(row.form_id),
                "form_name": row.form_name,
                "count": row.count,
                "avg_score": round(float(row.avg_score), 2),
            }
            for row in result.all()
        ]

    async def get_score_trend(self, db: AsyncSession, company_id: str) -> list[dict]:
        since_30d = datetime.now(UTC) - timedelta(days=30)
        result = await db.execute(
            select(
                func.date(Submission.finished_at).label("date"),
                func.round(func.avg(Submission.score).cast(Numeric), 1).label("avg_score"),
            )
            .where(
                Submission.company_id == company_id,
                Submission.status == "completed",
                Submission.score.is_not(None),
                Submission.finished_at >= since_30d,
            )
            .group_by(func.date(Submission.finished_at))
            .order_by(func.date(Submission.finished_at).asc())
        )
        return [{"date": str(row.date), "avg_score": float(row.avg_score)} for row in result.all()]

    async def list_recent(
        self, db: AsyncSession, company_id: str, limit: int = 5, since: datetime | None = None
    ) -> list[Submission]:
        filters = [Submission.company_id == company_id]
        if since:
            filters.append(Submission.started_at >= since)
        statement = (
            select(Submission)
            .where(*filters)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
                selectinload(Submission.asset),
            )
            .order_by(Submission.created_at.desc())
            .limit(limit)
        )
        return await self._list_from_stmt(db, statement)

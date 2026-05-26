from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.form_versions import FormVersion
from app.db.models.forms import Form
from app.db.models.submission_values import SubmissionValue
from app.db.models.submissions import Submission


class SubmissionRepository(SQLAlchemyRepository[Submission]):
    model = Submission

    def get_form_by_id(self, db: Session, company_id: str, form_id: str) -> Form | None:
        statement = (
            select(Form)
            .where(Form.company_id == company_id, Form.id == form_id)
            .options(selectinload(Form.versions).selectinload(FormVersion.fields))
        )
        return self._get_one(db, statement)

    def create_submission(self, db: Session, submission: Submission) -> Submission:
        return self._save(db, submission)

    def get_submission(self, db: Session, company_id: str, submission_id: str) -> Submission | None:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id, Submission.id == submission_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.fields),
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
            )
        )
        return self._get_one(db, statement)

    def list_submissions(self, db: Session, company_id: str, params: PaginationParams) -> tuple[list[Submission], int]:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
            )
            .order_by(Submission.created_at.desc())
        )
        return self._paginate_select(db, statement, params)

    def get_submission_value_by_field_id(
        self,
        db: Session,
        submission_id: str,
        form_field_id: str,
    ) -> SubmissionValue | None:
        statement = select(SubmissionValue).where(
            SubmissionValue.submission_id == submission_id,
            SubmissionValue.form_field_id == form_field_id,
        )
        return self._get_one(db, statement)

    def save_submission_value(self, db: Session, submission_value: SubmissionValue) -> SubmissionValue:
        return self._save(db, submission_value)

    def get_company_stats(self, db: Session, company_id: str) -> dict:
        row = db.execute(
            select(
                func.count().label("total"),
                func.count(case((Submission.status == "completed", 1))).label("completed"),
                func.count(case((Submission.status == "in_progress", 1))).label("in_progress"),
                func.avg(
                    case((Submission.status == "completed", Submission.score))
                ).label("avg_score"),
            ).where(Submission.company_id == company_id)
        ).one()
        return {
            "total": row.total,
            "completed": row.completed,
            "in_progress": row.in_progress,
            "avg_score": round(float(row.avg_score), 2) if row.avg_score is not None else None,
        }

    def list_recent(self, db: Session, company_id: str, limit: int = 5) -> list[Submission]:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.form),
                selectinload(Submission.values),
            )
            .order_by(Submission.created_at.desc())
            .limit(limit)
        )
        return self._list_from_stmt(db, statement)

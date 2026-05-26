from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.attachments import Attachment
from app.db.models.form_versions import FormVersion
from app.db.models.submission_values import SubmissionValue
from app.db.models.submissions import Submission


class AttachmentRepository(SQLAlchemyRepository[Attachment]):
    model = Attachment

    def get_submission(self, db: Session, company_id: str, submission_id: str) -> Submission | None:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id, Submission.id == submission_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.fields),
                selectinload(Submission.values).selectinload(SubmissionValue.attachments),
            )
        )
        return self._get_one(db, statement)

    def get_submission_value(self, db: Session, submission_id: str, form_field_id: str) -> SubmissionValue | None:
        statement = select(SubmissionValue).where(
            SubmissionValue.submission_id == submission_id,
            SubmissionValue.form_field_id == form_field_id,
        )
        return self._get_one(db, statement)

    def save_submission_value(self, db: Session, submission_value: SubmissionValue) -> SubmissionValue:
        return self._save(db, submission_value)

    def save_attachment(self, db: Session, attachment: Attachment) -> Attachment:
        return self._save(db, attachment)

    def list_attachments_for_submission(
        self,
        db: Session,
        company_id: str,
        submission_id: str,
        params: PaginationParams,
    ) -> tuple[list[Attachment], int]:
        statement = (
            select(Attachment)
            .join(Attachment.submission_value)
            .join(SubmissionValue.submission)
            .where(Submission.company_id == company_id, Submission.id == submission_id)
            .options(selectinload(Attachment.submission_value).selectinload(SubmissionValue.form_field))
            .order_by(Attachment.created_at.desc())
        )
        return self._paginate_select(db, statement, params)

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.attachments import Attachment
from app.db.models.memberships import Membership
from app.db.models.submission_values import SubmissionValue
from app.db.models.users import User
from app.modules.attachments.repository import AttachmentRepository
from app.modules.attachments.schemas import AttachmentCreateRequest, AttachmentResponse


class AttachmentService:
    def __init__(self, repository: AttachmentRepository | None = None) -> None:
        self.repository = repository or AttachmentRepository()

    def list_attachments(
        self,
        db: Session,
        membership: Membership,
        submission_id: str,
        params: PaginationParams,
    ) -> tuple[list[AttachmentResponse], PageMeta]:
        attachments, total = self.repository.list_attachments_for_submission(
            db,
            str(membership.company_id),
            submission_id,
            params,
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_attachment(item) for item in attachments], meta

    def create_attachment(
        self,
        db: Session,
        membership: Membership,
        current_user: User,
        submission_id: str,
        payload: AttachmentCreateRequest,
    ) -> AttachmentResponse:
        submission = self.repository.get_submission(db, str(membership.company_id), submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada.")

        field = next((item for item in submission.form_version.fields if item.key == payload.field_key), None)
        if field is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campo da evidencia nao encontrado.")

        submission_value = self.repository.get_submission_value(db, str(submission.id), str(field.id))
        if submission_value is None:
            submission_value = SubmissionValue(submission_id=submission.id, form_field_id=field.id)
            self.repository.save_submission_value(db, submission_value)

        attachment = Attachment(
            submission_value_id=submission_value.id,
            file_url=payload.file_url,
            thumbnail_url=payload.thumbnail_url,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            uploaded_by=current_user.id,
        )
        self.repository.save_attachment(db, attachment)

        # keep answers_json in sync with the new attachment
        answers_snapshot = dict(submission.answers_json or {})
        answers_snapshot[field.key] = payload.file_url
        submission.answers_json = answers_snapshot
        db.add(submission)

        db.commit()

        attachments, _ = self.repository.list_attachments_for_submission(
            db,
            str(membership.company_id),
            submission_id,
            PaginationParams(page=1, page_size=100),
        )
        created = next(item for item in attachments if str(item.id) == str(attachment.id))
        return self.serialize_attachment(created)

    @staticmethod
    def serialize_attachment(attachment: Attachment) -> AttachmentResponse:
        return AttachmentResponse(
            id=str(attachment.id),
            submission_id=str(attachment.submission_value.submission_id),
            field_key=attachment.submission_value.form_field.key,
            file_url=attachment.file_url,
            thumbnail_url=attachment.thumbnail_url,
            mime_type=attachment.mime_type,
            file_size=attachment.file_size,
            created_at=attachment.created_at,
        )

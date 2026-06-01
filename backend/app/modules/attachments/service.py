from __future__ import annotations

import os

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def list_attachments(
        self,
        db: AsyncSession,
        membership: Membership,
        submission_id: str,
        params: PaginationParams,
    ) -> tuple[list[AttachmentResponse], PageMeta]:
        attachments, total = await self.repository.list_attachments_for_submission(
            db,
            str(membership.company_id),
            submission_id,
            params,
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_attachment(item) for item in attachments], meta

    async def create_attachment(
        self,
        db: AsyncSession,
        membership: Membership,
        current_user: User,
        submission_id: str,
        payload: AttachmentCreateRequest,
    ) -> AttachmentResponse:
        submission = await self.repository.get_submission(
            db, str(membership.company_id), submission_id
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada."
            )

        field = next(
            (item for item in submission.form_version.fields if item.key == payload.field_key), None
        )
        if field is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo da evidencia nao encontrado.",
            )

        submission_value = await self.repository.get_submission_value(
            db, str(submission.id), str(field.id)
        )
        if submission_value is None:
            submission_value = SubmissionValue(
                submission_id=submission.id, form_field_id=field.id
            )
            await self.repository.save_submission_value(db, submission_value)

        attachment = Attachment(
            submission_value_id=submission_value.id,
            file_url=payload.file_url,
            thumbnail_url=payload.thumbnail_url,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            uploaded_by=current_user.id,
        )
        await self.repository.save_attachment(db, attachment)

        answers_snapshot = dict(submission.answers_json or {})
        answers_snapshot[field.key] = payload.file_url
        submission.answers_json = answers_snapshot
        db.add(submission)

        await db.commit()

        attachments, _ = await self.repository.list_attachments_for_submission(
            db,
            str(membership.company_id),
            submission_id,
            PaginationParams(page=1, page_size=100),
        )
        created = next(item for item in attachments if str(item.id) == str(attachment.id))
        return self.serialize_attachment(created)

    async def delete_attachment(
        self,
        db: AsyncSession,
        membership: Membership,
        submission_id: str,
        attachment_id: str,
    ) -> None:
        attachment = await self.repository.get_attachment_by_id(
            db, str(membership.company_id), submission_id, attachment_id
        )
        if attachment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Anexo nao encontrado."
            )

        file_path = None
        try:
            from app.core.config import get_settings
            settings = get_settings()
            url = attachment.file_url
            base = settings.upload_base_url.rstrip("/")
            if url.startswith(base):
                relative = url[len(base):].lstrip("/")
                file_path = os.path.join(settings.upload_dir, relative)
        except Exception:
            pass

        await self.repository.delete_attachment(db, attachment)
        await db.commit()

        if file_path and os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

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

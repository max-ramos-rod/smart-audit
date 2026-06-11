from __future__ import annotations

import os

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.attachments import Attachment
from app.db.models.form_fields import FormField
from app.db.models.memberships import Membership
from app.db.models.submissions import Submission
from app.db.models.users import User
from app.modules.assets.repository import AssetRepository
from app.modules.attachments.repository import AttachmentRepository
from app.modules.attachments.schemas import AttachmentCreateRequest, AttachmentResponse


class AttachmentService:
    def __init__(
        self,
        repository: AttachmentRepository | None = None,
        asset_repository: AssetRepository | None = None,
    ) -> None:
        self.repository = repository or AttachmentRepository()
        self.asset_repository = asset_repository or AssetRepository()

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

        # Deriva o escopo e valida (INV1); attachments é a fonte da verdade — não escreve
        # answers_json (revisa o efeito colateral do ADR-0006/0016 — ADR-0017).
        scope, field, asset_id, component_label = await self._resolve_scope(db, submission, payload)

        attachment = Attachment(
            company_id=membership.company_id,
            scope=scope,
            submission_id=submission.id,
            form_field_id=field.id if field is not None else None,
            asset_id=asset_id,
            component_label=component_label,
            metadata_json=payload.metadata_json,
            file_url=payload.file_url,
            thumbnail_url=payload.thumbnail_url,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            uploaded_by=current_user.id,
        )
        await self.repository.save_attachment(db, attachment)
        await db.commit()

        created = await self.repository.get_attachment_by_id(
            db, str(membership.company_id), submission_id, str(attachment.id)
        )
        assert created is not None
        return self.serialize_attachment(created)

    async def _resolve_scope(
        self, db: AsyncSession, submission: Submission, payload: AttachmentCreateRequest
    ) -> tuple[str, FormField | None, str | None, str | None]:
        """Deriva (scope, field, asset_id, component_label) e valida INV1 (DR-0017)."""
        if payload.field_key is None:
            if payload.asset_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Evidencia por componente exige um campo.",
                )
            return "submission", None, None, None

        field = next(
            (f for f in submission.form_version.fields if f.key == payload.field_key), None
        )
        if field is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo da evidencia nao encontrado.",
            )
        if payload.asset_id is None:
            return "field", field, None, None

        component = await self._validate_component(db, submission, field, payload.asset_id)
        return "component", field, payload.asset_id, component["identifier"]

    async def _validate_component(
        self, db: AsyncSession, submission: Submission, field: FormField, asset_id: str
    ) -> dict:
        """INV1: o componente pertence à subárvore do ativo da inspeção e seu tipo bate com
        o ``component_type_id`` do campo. Senão 400 (RFC 7807)."""
        if field.component_type_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo nao aceita escopo de componente.",
            )
        if submission.asset_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inspecao sem ativo vinculado nao aceita evidencia por componente.",
            )
        rows = await self.asset_repository.list_subtree_components(db, str(submission.asset_id))
        component = next((r for r in rows if str(r["id"]) == str(asset_id)), None)
        if component is None or str(component["asset_type_id"]) != str(field.component_type_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Componente invalido para o campo (fora da arvore ou tipo divergente).",
            )
        return component

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
            submission_id=str(attachment.submission_id) if attachment.submission_id else None,
            scope=attachment.scope,
            field_key=attachment.form_field.key if attachment.form_field else None,
            asset_id=str(attachment.asset_id) if attachment.asset_id else None,
            component_label=attachment.component_label,
            file_url=attachment.file_url,
            thumbnail_url=attachment.thumbnail_url,
            mime_type=attachment.mime_type,
            file_size=attachment.file_size,
            metadata_json=attachment.metadata_json,
            created_at=attachment.created_at,
        )

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.attachments import Attachment
from app.db.models.form_versions import FormVersion
from app.db.models.submissions import Submission


class AttachmentRepository(SQLAlchemyRepository[Attachment]):
    model = Attachment

    async def get_submission(
        self, db: AsyncSession, company_id: str, submission_id: str
    ) -> Submission | None:
        statement = (
            select(Submission)
            .where(Submission.company_id == company_id, Submission.id == submission_id)
            .options(
                selectinload(Submission.form_version).selectinload(FormVersion.fields),
            )
        )
        return await self._get_one(db, statement)

    async def save_attachment(self, db: AsyncSession, attachment: Attachment) -> Attachment:
        return await self._save(db, attachment)

    async def get_attachment_by_id(
        self, db: AsyncSession, company_id: str, submission_id: str, attachment_id: str
    ) -> Attachment | None:
        statement = (
            select(Attachment)
            .where(
                Attachment.company_id == company_id,
                Attachment.submission_id == submission_id,
                Attachment.id == attachment_id,
            )
            .options(selectinload(Attachment.form_field))
        )
        return await self._get_one(db, statement)

    async def delete_attachment(self, db: AsyncSession, attachment: Attachment) -> None:
        await self.delete(db, attachment)

    async def list_attachments_for_submission(
        self,
        db: AsyncSession,
        company_id: str,
        submission_id: str,
        params: PaginationParams,
    ) -> tuple[list[Attachment], int]:
        statement = (
            select(Attachment)
            .where(
                Attachment.company_id == company_id,
                Attachment.submission_id == submission_id,
            )
            .options(selectinload(Attachment.form_field))
            .order_by(Attachment.created_at.asc())
        )
        return await self._paginate_select(db, statement, params)

    async def list_for_anchor(
        self,
        db: AsyncSession,
        company_id: str,
        submission_id: str,
        form_field_id: str | None,
        asset_id: str | None,
    ) -> list[Attachment]:
        """Evidências de uma instância exata (DR-0017). Helper único com ``IS NOT DISTINCT FROM``
        para tratar `NULL` (campo geral / sem componente) como igual sem o footgun do `=`."""
        statement = (
            select(Attachment)
            .where(
                Attachment.company_id == company_id,
                Attachment.submission_id == submission_id,
                Attachment.form_field_id.is_not_distinct_from(form_field_id),
                Attachment.asset_id.is_not_distinct_from(asset_id),
            )
            .options(selectinload(Attachment.form_field))
            .order_by(Attachment.created_at.asc())
        )
        return await self._list_from_stmt(db, statement)

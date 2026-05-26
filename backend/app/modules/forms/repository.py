from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.form_fields import FormField
from app.db.models.form_versions import FormVersion
from app.db.models.forms import Form


class FormRepository(SQLAlchemyRepository[Form]):
    model = Form

    async def create_form(self, db: AsyncSession, form: Form) -> Form:
        return await self._save(db, form)

    async def create_form_version(self, db: AsyncSession, form_version: FormVersion) -> FormVersion:
        return await self._save(db, form_version)

    async def create_form_fields(
        self, db: AsyncSession, fields: list[FormField]
    ) -> list[FormField]:
        return await self._save_many(db, fields)

    async def list_forms_by_company(
        self, db: AsyncSession, company_id: str, params: PaginationParams
    ) -> tuple[list[Form], int]:
        statement = (
            select(Form)
            .where(Form.company_id == company_id)
            .options(selectinload(Form.versions).selectinload(FormVersion.fields))
            .order_by(Form.created_at.desc())
        )
        return await self._paginate_select(db, statement, params, unique=True)

    async def get_form_by_id(
        self, db: AsyncSession, company_id: str, form_id: str
    ) -> Form | None:
        statement = (
            select(Form)
            .where(Form.company_id == company_id, Form.id == form_id)
            .options(selectinload(Form.versions).selectinload(FormVersion.fields))
        )
        return await self._get_one(db, statement)

    async def get_form_version_by_id(
        self, db: AsyncSession, company_id: str, form_id: str, version_id: str
    ) -> FormVersion | None:
        statement = (
            select(FormVersion)
            .join(Form, FormVersion.form_id == Form.id)
            .where(
                Form.company_id == company_id,
                FormVersion.form_id == form_id,
                FormVersion.id == version_id,
            )
            .options(selectinload(FormVersion.fields))
        )
        return await self._get_one(db, statement)

    async def list_form_versions(
        self, db: AsyncSession, company_id: str, form_id: str
    ) -> list[FormVersion]:
        statement = (
            select(FormVersion)
            .join(Form, FormVersion.form_id == Form.id)
            .where(Form.company_id == company_id, FormVersion.form_id == form_id)
            .options(selectinload(FormVersion.fields))
            .order_by(FormVersion.version.desc())
        )
        return await self._list_from_stmt(db, statement)

    async def get_next_version_number(self, db: AsyncSession, form_id: str) -> int:
        statement = select(func.max(FormVersion.version)).where(FormVersion.form_id == form_id)
        current_max = await db.scalar(statement) or 0
        return int(current_max) + 1

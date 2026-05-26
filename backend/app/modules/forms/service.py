from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.form_fields import FormField
from app.db.models.form_versions import FormVersion
from app.db.models.forms import Form
from app.db.models.memberships import Membership
from app.db.models.users import User
from app.modules.forms.repository import FormRepository
from app.modules.forms.schemas import (
    FormCreateRequest,
    FormFieldCreateRequest,
    FormFieldResponse,
    FormListItemResponse,
    FormResponse,
    FormVersionListItemResponse,
    FormVersionPublishRequest,
    FormVersionResponse,
)


class FormService:
    def __init__(self, repository: FormRepository | None = None) -> None:
        self.repository = repository or FormRepository()

    async def list_versions(
        self, db: AsyncSession, membership: Membership, form_id: str
    ) -> list[FormVersionListItemResponse]:
        form = await self.repository.get_form_by_id(db, str(membership.company_id), form_id)
        if form is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Formulario nao encontrado."
            )
        versions = await self.repository.list_form_versions(
            db, str(membership.company_id), form_id
        )
        return [
            FormVersionListItemResponse(
                id=str(v.id),
                version=v.version,
                status=v.status,
                published_at=v.published_at,
                fields_count=len(v.fields),
            )
            for v in versions
        ]

    async def list_forms(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[FormListItemResponse], PageMeta]:
        forms, total = await self.repository.list_forms_by_company(
            db, str(membership.company_id), params
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_form_list_item(form) for form in forms], meta

    async def get_version(
        self, db: AsyncSession, membership: Membership, form_id: str, version_id: str
    ) -> FormVersionResponse:
        version = await self.repository.get_form_version_by_id(
            db, str(membership.company_id), form_id, version_id
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Versao nao encontrada."
            )
        return self.serialize_version(version)

    async def get_form(
        self, db: AsyncSession, membership: Membership, form_id: str
    ) -> FormResponse:
        form = await self.repository.get_form_by_id(db, str(membership.company_id), form_id)
        if form is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Formulario nao encontrado."
            )
        return self.serialize_form(form)

    async def create_form(
        self,
        db: AsyncSession,
        membership: Membership,
        current_user: User,
        payload: FormCreateRequest,
    ) -> FormResponse:
        self.validate_fields(payload.fields)

        form = Form(
            company_id=membership.company_id,
            name=payload.name,
            description=payload.description,
            is_active=True,
            created_by=current_user.id,
        )
        await self.repository.create_form(db, form)

        form_version = FormVersion(
            form_id=form.id,
            version=1,
            status="published",
            published_at=datetime.now(UTC),
            created_by=current_user.id,
        )
        await self.repository.create_form_version(db, form_version)

        fields = [
            FormField(
                form_version_id=form_version.id,
                key=item.key,
                label=item.label,
                field_type=item.field_type,
                required=item.required,
                position=item.position,
                config_json=item.config_json,
            )
            for item in payload.fields
        ]
        await self.repository.create_form_fields(db, fields)
        await db.commit()

        created_form = await self.repository.get_form_by_id(
            db, str(membership.company_id), str(form.id)
        )
        return self.serialize_form(created_form)

    async def publish_new_version(
        self,
        db: AsyncSession,
        membership: Membership,
        current_user: User,
        form_id: str,
        payload: FormVersionPublishRequest,
    ) -> FormResponse:
        self.validate_fields(payload.fields)
        form = await self.repository.get_form_by_id(db, str(membership.company_id), form_id)
        if form is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Formulario nao encontrado."
            )

        next_version = await self.repository.get_next_version_number(db, form_id)
        form_version = FormVersion(
            form_id=form.id,
            version=next_version,
            status="published",
            published_at=datetime.now(UTC),
            created_by=current_user.id,
        )
        await self.repository.create_form_version(db, form_version)

        fields = [
            FormField(
                form_version_id=form_version.id,
                key=item.key,
                label=item.label,
                field_type=item.field_type,
                required=item.required,
                position=item.position,
                config_json=item.config_json,
            )
            for item in payload.fields
        ]
        await self.repository.create_form_fields(db, fields)
        await db.commit()

        updated_form = await self.repository.get_form_by_id(
            db, str(membership.company_id), form_id
        )
        return self.serialize_form(updated_form)

    @staticmethod
    def validate_fields(fields: list[FormFieldCreateRequest]) -> None:
        if not fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Informe ao menos um campo."
            )

        keys = [field.key for field in fields]
        positions = [field.position for field in fields]
        if len(keys) != len(set(keys)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="As chaves dos campos devem ser unicas.",
            )
        if len(positions) != len(set(positions)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="As posicoes dos campos devem ser unicas.",
            )

    @staticmethod
    def serialize_form(form: Form) -> FormResponse:
        current_version = max(form.versions, key=lambda item: item.version)
        return FormResponse(
            id=str(form.id),
            company_id=str(form.company_id),
            name=form.name,
            description=form.description,
            is_active=form.is_active,
            current_version=FormService.serialize_version(current_version),
        )

    @staticmethod
    def serialize_form_list_item(form: Form) -> FormListItemResponse:
        current_version = max(form.versions, key=lambda item: item.version)
        return FormListItemResponse(
            id=str(form.id),
            company_id=str(form.company_id),
            name=form.name,
            description=form.description,
            is_active=form.is_active,
            current_version_number=current_version.version,
            current_version_status=current_version.status,
            published_at=current_version.published_at,
        )

    @staticmethod
    def serialize_version(version: FormVersion) -> FormVersionResponse:
        ordered_fields = sorted(version.fields, key=lambda item: item.position)
        return FormVersionResponse(
            id=str(version.id),
            version=version.version,
            status=version.status,
            published_at=version.published_at,
            fields=[
                FormFieldResponse(
                    id=str(field.id),
                    key=field.key,
                    label=field.label,
                    field_type=field.field_type,
                    required=field.required,
                    position=field.position,
                    config_json=field.config_json,
                )
                for field in ordered_fields
            ],
        )

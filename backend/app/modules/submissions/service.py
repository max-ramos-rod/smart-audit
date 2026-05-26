from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.form_fields import FormField
from app.db.models.memberships import Membership
from app.db.models.submission_values import SubmissionValue
from app.db.models.submissions import Submission
from app.db.models.users import User
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import (
    CompanyStatsResponse,
    SubmissionAnswerResponse,
    SubmissionAnswersUpdateRequest,
    SubmissionCreateRequest,
    SubmissionListItemResponse,
    SubmissionResponse,
)


class SubmissionService:
    def __init__(self, repository: SubmissionRepository | None = None) -> None:
        self.repository = repository or SubmissionRepository()

    def get_company_stats(self, db: Session, membership: Membership) -> CompanyStatsResponse:
        company_id = str(membership.company_id)
        counts = self.repository.get_company_stats(db, company_id)
        recent = self.repository.list_recent(db, company_id)
        return CompanyStatsResponse(
            total_submissions=counts["total"],
            completed=counts["completed"],
            in_progress=counts["in_progress"],
            avg_score=counts["avg_score"],
            recent=[self.serialize_submission_list_item(s) for s in recent],
        )

    def list_submissions(
        self,
        db: Session,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[SubmissionListItemResponse], PageMeta]:
        submissions, total = self.repository.list_submissions(db, str(membership.company_id), params)
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_submission_list_item(item) for item in submissions], meta

    def create_submission(
        self,
        db: Session,
        membership: Membership,
        current_user: User,
        payload: SubmissionCreateRequest,
    ) -> SubmissionResponse:
        form = self.repository.get_form_by_id(db, str(membership.company_id), payload.form_id)
        if form is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario nao encontrado.")

        current_version = max(form.versions, key=lambda item: item.version)
        submission = Submission(
            company_id=membership.company_id,
            form_version_id=current_version.id,
            created_by=current_user.id,
            status="in_progress",
            answers_json={},
        )
        self.repository.create_submission(db, submission)
        db.commit()

        created = self.repository.get_submission(db, str(membership.company_id), str(submission.id))
        return self.serialize_submission(created)

    def get_submission(self, db: Session, membership: Membership, submission_id: str) -> SubmissionResponse:
        submission = self.repository.get_submission(db, str(membership.company_id), submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada.")
        return self.serialize_submission(submission)

    def save_answers(
        self,
        db: Session,
        membership: Membership,
        submission_id: str,
        payload: SubmissionAnswersUpdateRequest,
    ) -> SubmissionResponse:
        submission = self.repository.get_submission(db, str(membership.company_id), submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada.")
        if submission.status == "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inspecao ja finalizada.")

        fields_by_key = {field.key: field for field in submission.form_version.fields}
        answers_snapshot = dict(submission.answers_json or {})

        for answer in payload.answers:
            field = fields_by_key.get(answer.field_key)
            if field is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo invalido: {answer.field_key}.")

            normalized_value = self.normalize_value(field, answer.value)
            submission_value = self.repository.get_submission_value_by_field_id(db, str(submission.id), str(field.id))
            if submission_value is None:
                submission_value = SubmissionValue(submission_id=submission.id, form_field_id=field.id)

            submission_value.value_text = None
            submission_value.value_number = None
            submission_value.value_boolean = None
            submission_value.value_date = None
            submission_value.value_json = None

            if field.field_type == "boolean":
                submission_value.value_boolean = normalized_value
            elif field.field_type == "number":
                submission_value.value_number = normalized_value
            elif field.field_type == "date":
                submission_value.value_date = normalized_value
            elif field.field_type in {"select"} and isinstance(normalized_value, dict):
                submission_value.value_json = normalized_value
            else:
                submission_value.value_text = normalized_value

            self.repository.save_submission_value(db, submission_value)
            answers_snapshot[field.key] = self.serialize_raw_value(field.field_type, normalized_value)

        submission.answers_json = answers_snapshot
        submission.status = "in_progress"
        db.add(submission)
        db.commit()

        updated = self.repository.get_submission(db, str(membership.company_id), submission_id)
        return self.serialize_submission(updated)

    def finish_submission(self, db: Session, membership: Membership, submission_id: str) -> SubmissionResponse:
        submission = self.repository.get_submission(db, str(membership.company_id), submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada.")

        answers_by_field_id = {str(value.form_field_id): value for value in submission.values}
        missing_required = []
        for field in submission.form_version.fields:
            if field.required and str(field.id) not in answers_by_field_id:
                missing_required.append(field.key)

        if missing_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campos obrigatorios pendentes: {', '.join(missing_required)}.",
            )

        submission.status = "completed"
        submission.finished_at = datetime.now(UTC)
        submission.score = self.calculate_score(submission)
        db.add(submission)
        db.commit()

        updated = self.repository.get_submission(db, str(membership.company_id), submission_id)
        return self.serialize_submission(updated)

    @staticmethod
    def normalize_value(field: FormField, value):
        if field.field_type == "boolean":
            if not isinstance(value, bool):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo {field.key} espera boolean.")
            return value
        if field.field_type == "number":
            if not isinstance(value, (int, float)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo {field.key} espera numero.")
            return float(value)
        if field.field_type == "date":
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                return date.fromisoformat(value)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo {field.key} espera data ISO.")
        if field.field_type == "select" and isinstance(value, dict):
            return value
        if value is None:
            return None
        if not isinstance(value, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo {field.key} espera texto.")
        return value

    @staticmethod
    def serialize_raw_value(field_type: str, value):
        if isinstance(value, date):
            return value.isoformat()
        return value

    @staticmethod
    def calculate_score(submission: Submission) -> float | None:
        boolean_answers = []
        for field in submission.form_version.fields:
            if field.field_type != "boolean":
                continue
            submission_value = next((item for item in submission.values if str(item.form_field_id) == str(field.id)), None)
            if submission_value is not None and submission_value.value_boolean is not None:
                boolean_answers.append(submission_value.value_boolean)

        if not boolean_answers:
            return None

        approved = sum(1 for item in boolean_answers if item)
        return round((approved / len(boolean_answers)) * 100, 2)

    @staticmethod
    def serialize_submission(submission: Submission) -> SubmissionResponse:
        fields_by_id = {str(field.id): field for field in submission.form_version.fields}
        answers = []
        for value in submission.values:
            field = fields_by_id[str(value.form_field_id)]
            answers.append(
                SubmissionAnswerResponse(
                    field_key=field.key,
                    field_type=field.field_type,
                    value=SubmissionService.extract_value(value, field.field_type),
                )
            )

        ordered_answers = sorted(answers, key=lambda item: item.field_key)
        return SubmissionResponse(
            id=str(submission.id),
            form_id=str(submission.form_version.form.id),
            form_version_id=str(submission.form_version_id),
            form_name=submission.form_version.form.name,
            status=submission.status,
            score=float(submission.score) if submission.score is not None else None,
            started_at=submission.started_at,
            finished_at=submission.finished_at,
            answers=ordered_answers,
        )

    @staticmethod
    def serialize_submission_list_item(submission: Submission) -> SubmissionListItemResponse:
        return SubmissionListItemResponse(
            id=str(submission.id),
            form_id=str(submission.form_version.form.id),
            form_name=submission.form_version.form.name,
            status=submission.status,
            score=float(submission.score) if submission.score is not None else None,
            started_at=submission.started_at,
            finished_at=submission.finished_at,
        )

    @staticmethod
    def extract_value(submission_value: SubmissionValue, field_type: str):
        if field_type == "boolean":
            return submission_value.value_boolean
        if field_type == "number":
            return float(submission_value.value_number) if submission_value.value_number is not None else None
        if field_type == "date":
            return submission_value.value_date
        if field_type == "select" and submission_value.value_json is not None:
            return submission_value.value_json
        return submission_value.value_text

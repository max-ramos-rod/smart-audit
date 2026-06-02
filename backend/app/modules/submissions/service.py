from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.form_fields import FormField
from app.db.models.memberships import Membership
from app.db.models.submission_values import SubmissionValue
from app.db.models.submissions import Submission
from app.db.models.users import User
from app.modules.submissions.pdf import generate_submission_pdf
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import (
    CompanyStatsResponse,
    FormScoreStat,
    NotificationItem,
    ScoreBreakdown,
    ScoreTrendPoint,
    SubmissionAnswerResponse,
    SubmissionAnswersUpdateRequest,
    SubmissionCreateRequest,
    SubmissionListItemResponse,
    SubmissionResponse,
)


class SubmissionService:
    def __init__(self, repository: SubmissionRepository | None = None) -> None:
        self.repository = repository or SubmissionRepository()

    async def export_csv(
        self,
        db: AsyncSession,
        membership: Membership,
        status: str | None = None,
        form_id: str | None = None,
    ) -> bytes:
        submissions = await self.repository.list_all_for_export(
            db, str(membership.company_id), status=status, form_id=form_id
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "formulario", "status", "score", "iniciada_em", "finalizada_em"])
        for s in submissions:
            form_name = (
                s.form_version.form.name
                if s.form_version and s.form_version.form
                else ""
            )
            writer.writerow([
                str(s.id),
                form_name,
                s.status,
                f"{float(s.score):.2f}" if s.score is not None else "",
                s.started_at.strftime("%d/%m/%Y %H:%M") if s.started_at else "",
                s.finished_at.strftime("%d/%m/%Y %H:%M") if s.finished_at else "",
            ])
        return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")

    async def get_notifications(
        self, db: AsyncSession, membership: Membership, read_keys: set[str] | None = None
    ) -> list[NotificationItem]:
        now = datetime.now(UTC)
        pending_threshold = now - timedelta(hours=24)
        completed_since = now - timedelta(days=30)

        submissions = await self.repository.list_for_notifications(
            db, str(membership.company_id), pending_threshold, completed_since
        )

        read_set = read_keys or set()
        items: list[NotificationItem] = []
        for s in submissions:
            form_name = (
                s.form_version.form.name
                if s.form_version and s.form_version.form
                else "Formulário"
            )
            if s.status == "in_progress":
                hours_ago = int((now - s.started_at).total_seconds() / 3600)
                age = f"{int(hours_ago / 24)} dias" if hours_ago >= 48 else f"{hours_ago}h"
                key = f"pending-{s.id}"
                items.append(
                    NotificationItem(
                        id=key,
                        type="pending",
                        title=f"Inspeção pendente há {age}",
                        description=(
                            f"{form_name} iniciada em "
                            f"{s.started_at.strftime('%d/%m/%Y')} sem finalização."
                        ),
                        created_at=s.started_at,
                        read=key in read_set,
                    )
                )
            elif s.status == "completed" and s.score is not None:
                score = float(s.score)
                finished = s.finished_at or s.created_at
                if score < 80:
                    key = f"low-score-{s.id}"
                    items.append(
                        NotificationItem(
                            id=key,
                            type="low_score",
                            title="Score abaixo do mínimo",
                            description=f"{form_name}: {score:.0f}% (mínimo recomendado: 80%).",
                            created_at=finished,
                            read=key in read_set,
                        )
                    )
                elif score >= 90:
                    key = f"excellent-{s.id}"
                    items.append(
                        NotificationItem(
                            id=key,
                            type="excellent",
                            title="Inspeção concluída com excelência",
                            description=f"{form_name}: score {score:.0f}%.",
                            created_at=finished,
                            read=key in read_set,
                        )
                    )

        return items[:20]

    async def get_company_stats(
        self, db: AsyncSession, membership: Membership, period: str | None = None
    ) -> CompanyStatsResponse:
        company_id = str(membership.company_id)
        since = self.parse_period_start(period)
        counts = await self.repository.get_company_stats(db, company_id, since=since)
        recent = await self.repository.list_recent(db, company_id, since=since)
        score_by_form_rows = await self.repository.get_score_by_form(db, company_id, since=since)
        score_trend_rows = await self.repository.get_score_trend(db, company_id)
        return CompanyStatsResponse(
            total_submissions=counts["total"],
            completed=counts["completed"],
            in_progress=counts["in_progress"],
            avg_score=counts["avg_score"],
            recent=[self.serialize_submission_list_item(s) for s in recent],
            score_by_form=[FormScoreStat(**row) for row in score_by_form_rows],
            score_trend=[ScoreTrendPoint(**row) for row in score_trend_rows],
        )

    async def list_submissions(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
        status: str | None = None,
        form_id: str | None = None,
        created_by: str | None = None,
    ) -> tuple[list[SubmissionListItemResponse], PageMeta]:
        submissions, total = await self.repository.list_submissions(
            db,
            str(membership.company_id),
            params,
            status=status,
            form_id=form_id,
            created_by=created_by,
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_submission_list_item(item) for item in submissions], meta

    async def create_submission(
        self,
        db: AsyncSession,
        membership: Membership,
        current_user: User,
        payload: SubmissionCreateRequest,
    ) -> SubmissionResponse:
        form = await self.repository.get_form_by_id(
            db, str(membership.company_id), payload.form_id
        )
        if form is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Formulario nao encontrado."
            )

        current_version = max(form.versions, key=lambda item: item.version)
        submission = Submission(
            company_id=membership.company_id,
            form_version_id=current_version.id,
            created_by=current_user.id,
            status="in_progress",
            answers_json={},
        )
        await self.repository.create_submission(db, submission)
        await db.commit()

        created = await self.repository.get_submission(
            db, str(membership.company_id), str(submission.id)
        )
        return self.serialize_submission(created)

    async def get_submission(
        self, db: AsyncSession, membership: Membership, submission_id: str
    ) -> SubmissionResponse:
        submission = await self.repository.get_submission(
            db, str(membership.company_id), submission_id
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada."
            )
        return self.serialize_submission(submission)

    async def save_answers(
        self,
        db: AsyncSession,
        membership: Membership,
        submission_id: str,
        payload: SubmissionAnswersUpdateRequest,
    ) -> SubmissionResponse:
        submission = await self.repository.get_submission(
            db, str(membership.company_id), submission_id
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada."
            )
        if submission.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inspecao ja finalizada."
            )

        fields_by_key = {field.key: field for field in submission.form_version.fields}
        answers_snapshot = dict(submission.answers_json or {})

        for answer in payload.answers:
            field = fields_by_key.get(answer.field_key)
            if field is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo invalido: {answer.field_key}.",
                )
            if field.field_type == "section":
                continue

            normalized_value = self.normalize_value(field, answer.value)
            submission_value = await self.repository.get_submission_value_by_field_id(
                db, str(submission.id), str(field.id)
            )
            if submission_value is None:
                submission_value = SubmissionValue(
                    submission_id=submission.id, form_field_id=field.id
                )

            submission_value.value_text = None
            submission_value.value_number = None
            submission_value.value_boolean = None
            submission_value.value_date = None
            submission_value.value_json = None

            if field.field_type == "boolean":
                if normalized_value == "na":
                    submission_value.value_text = "na"
                else:
                    submission_value.value_boolean = normalized_value
            elif field.field_type == "number":
                submission_value.value_number = normalized_value
            elif field.field_type == "date":
                submission_value.value_date = normalized_value
            elif field.field_type == "select" and isinstance(normalized_value, dict):
                submission_value.value_json = normalized_value
            else:
                submission_value.value_text = normalized_value

            await self.repository.save_submission_value(db, submission_value)
            raw = self.serialize_raw_value(field.field_type, normalized_value)
            answers_snapshot[field.key] = raw

        submission.answers_json = answers_snapshot
        submission.status = "in_progress"
        db.add(submission)
        await db.commit()

        updated = await self.repository.get_submission(
            db, str(membership.company_id), submission_id
        )
        return self.serialize_submission(updated)

    async def finish_submission(
        self, db: AsyncSession, membership: Membership, submission_id: str
    ) -> SubmissionResponse:
        submission = await self.repository.get_submission(
            db, str(membership.company_id), submission_id
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada."
            )

        answers_by_field_id = {str(value.form_field_id): value for value in submission.values}
        answers_snapshot = submission.answers_json or {}
        missing_required = []
        for field in submission.form_version.fields:
            if not field.required:
                continue
            visible_if = field.config_json.get("visible_if") if field.config_json else None
            if visible_if:
                trigger_key = visible_if.get("field_key", "")
                operator = visible_if.get("operator", "eq")
                expected = str(visible_if.get("value", "")).lower()
                actual = str(answers_snapshot.get(trigger_key, "")).lower()
                is_visible = (actual == expected) if operator == "eq" else (actual != expected)
                if not is_visible:
                    continue
            if str(field.id) not in answers_by_field_id:
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
        await db.commit()

        updated = await self.repository.get_submission(
            db, str(membership.company_id), submission_id
        )
        return self.serialize_submission(updated)

    async def export_pdf(
        self, db: AsyncSession, membership: Membership, submission_id: str
    ) -> bytes:
        submission = await self.repository.get_submission_for_export(
            db, str(membership.company_id), submission_id
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inspecao nao encontrada."
            )

        values_by_field_id = {str(v.form_field_id): v for v in submission.values}

        sorted_fields = sorted(submission.form_version.fields, key=lambda f: f.position)
        fields_with_answers = [
            {
                "position": f.position,
                "label": f.label,
                "field_type": f.field_type,
                "value": self.extract_value(values_by_field_id[str(f.id)], f.field_type)
                if str(f.id) in values_by_field_id
                else None,
            }
            for f in sorted_fields
        ]

        breakdown = self.calculate_score_breakdown(submission)
        score_breakdown_dict = (
            {
                "total_boolean": breakdown.total_boolean,
                "conformes": breakdown.conformes,
                "nao_conformes": breakdown.nao_conformes,
                "sem_resposta": breakdown.sem_resposta,
                "na_count": breakdown.na_count,
            }
            if breakdown
            else None
        )
        return generate_submission_pdf(
            company_name=submission.company.name,
            form_name=submission.form_version.form.name,
            form_version=submission.form_version.version,
            inspector_name=submission.creator.name,
            status=submission.status,
            score=float(submission.score) if submission.score is not None else None,
            started_at=submission.started_at,
            finished_at=submission.finished_at,
            fields_with_answers=fields_with_answers,
            score_breakdown=score_breakdown_dict,
        )

    @staticmethod
    def parse_period_start(period: str | None) -> datetime | None:
        now = datetime.now(UTC)
        if period == "7d":
            return now - timedelta(days=7)
        if period == "30d":
            return now - timedelta(days=30)
        if period == "90d":
            return now - timedelta(days=90)
        return None

    @staticmethod
    def normalize_value(field: FormField, value):
        if field.field_type == "section":
            return None
        if field.field_type == "boolean":
            if value == "na" and field.config_json.get("allow_na"):
                return "na"
            if not isinstance(value, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo {field.key} espera boolean.",
                )
            return value
        if field.field_type == "number":
            if not isinstance(value, (int, float)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo {field.key} espera numero.",
                )
            return float(value)
        if field.field_type == "date":
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                return date.fromisoformat(value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campo {field.key} espera data ISO.",
            )
        if field.field_type == "select":
            if isinstance(value, str):
                return {"option": value}
            if isinstance(value, dict):
                return value
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campo {field.key} espera dict ou string para select.",
            )
        if value is None:
            return None
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campo {field.key} espera texto.",
            )
        return value

    @staticmethod
    def serialize_raw_value(field_type: str, value):
        if isinstance(value, date):
            return value.isoformat()
        return value

    @staticmethod
    def calculate_score_breakdown(submission: Submission) -> ScoreBreakdown | None:
        boolean_fields = [f for f in submission.form_version.fields if f.field_type == "boolean"]
        if not boolean_fields:
            return None
        values_by_field_id = {str(v.form_field_id): v for v in submission.values}
        conformes = 0
        nao_conformes = 0
        sem_resposta = 0
        na_count = 0
        for field in boolean_fields:
            sv = values_by_field_id.get(str(field.id))
            if sv is None:
                sem_resposta += 1
            elif sv.value_text == "na":
                na_count += 1
            elif sv.value_boolean is None:
                sem_resposta += 1
            elif sv.value_boolean:
                conformes += 1
            else:
                nao_conformes += 1
        return ScoreBreakdown(
            total_boolean=len(boolean_fields),
            conformes=conformes,
            nao_conformes=nao_conformes,
            sem_resposta=sem_resposta,
            na_count=na_count,
        )

    @staticmethod
    def calculate_score(submission: Submission) -> float | None:
        weighted_conformes = 0.0
        weighted_total = 0.0
        for field in submission.form_version.fields:
            if field.field_type != "boolean":
                continue
            weight = float(field.config_json.get("weight") or 1.0)
            sv = next(
                (item for item in submission.values if str(item.form_field_id) == str(field.id)),
                None,
            )
            if sv is None:
                continue
            extracted = SubmissionService.extract_value(sv, "boolean")
            if extracted is None or extracted == "na":
                continue
            weighted_total += weight
            if extracted is True:
                weighted_conformes += weight

        if weighted_total == 0:
            return None
        return round((weighted_conformes / weighted_total) * 100, 2)

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
            score_breakdown=SubmissionService.calculate_score_breakdown(submission),
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
            if submission_value.value_text == "na":
                return "na"
            return submission_value.value_boolean
        if field_type == "number":
            return (
                float(submission_value.value_number)
                if submission_value.value_number is not None
                else None
            )
        if field_type == "date":
            return submission_value.value_date
        if field_type == "select" and submission_value.value_json is not None:
            return submission_value.value_json
        return submission_value.value_text

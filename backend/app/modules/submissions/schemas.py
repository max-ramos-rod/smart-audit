from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class ConformityItem(BaseModel):
    field_key: str
    status: str
    justification: str | None


class ConformityInput(BaseModel):
    field_key: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=20)
    justification: str | None = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("conforme", "nao_conforme"):
            raise ValueError("status deve ser 'conforme' ou 'nao_conforme'")
        return v


class SubmissionConformityUpdateRequest(BaseModel):
    items: list[ConformityInput]


class SubmissionCreateRequest(BaseModel):
    form_id: str = Field(min_length=1, max_length=36)
    # Vínculo opcional ao ativo inspecionado (DR-0002 Fase 1). Ausente = inspeção sem ativo.
    asset_id: str | None = Field(default=None, min_length=1, max_length=36)


class SubmissionAnswerInput(BaseModel):
    field_key: str = Field(min_length=1, max_length=100)
    value: bool | int | float | str | date | dict | None


class SubmissionAnswersUpdateRequest(BaseModel):
    answers: list[SubmissionAnswerInput]


class SubmissionAnswerResponse(BaseModel):
    field_key: str
    field_type: str
    value: bool | float | str | date | dict | None


class ScoreBreakdown(BaseModel):
    total_boolean: int
    conformes: int
    nao_conformes: int
    sem_resposta: int
    na_count: int = 0


class ComponentInstance(BaseModel):
    """Componente expandido de um campo escopado (DR-0002 T3). Identidade vinda da árvore viva."""

    asset_id: str
    label: str
    type: str
    path: str


class ChecklistField(BaseModel):
    """Item do checklist expandido. ``components`` vazio = campo geral (uma instância)."""

    field_key: str
    field_type: str
    component_type_id: str | None = None
    components: list[ComponentInstance] = []


class SubmissionResponse(BaseModel):
    id: str
    form_id: str
    form_version_id: str
    form_name: str
    asset_id: str | None = None
    asset_identifier: str | None = None
    status: str
    score: float | None
    score_breakdown: ScoreBreakdown | None
    started_at: datetime
    finished_at: datetime | None
    answers: list[SubmissionAnswerResponse]
    conformity: list[ConformityItem] = []
    # Checklist expandido por componente (DR-0002 T3). Campos escopados viram N instâncias.
    checklist: list[ChecklistField] = []
    # Avisos não-bloqueantes da expansão (Q2: sem componentes; Q3: campo escopado sem ativo).
    warnings: list[str] = []


class SubmissionListItemResponse(BaseModel):
    id: str
    form_id: str
    form_name: str
    asset_id: str | None = None
    asset_identifier: str | None = None
    status: str
    score: float | None
    started_at: datetime
    finished_at: datetime | None


class FormScoreStat(BaseModel):
    form_id: str
    form_name: str
    avg_score: float
    count: int


class ScoreTrendPoint(BaseModel):
    date: str
    avg_score: float


class CompanyStatsResponse(BaseModel):
    total_submissions: int
    completed: int
    in_progress: int
    avg_score: float | None
    recent: list[SubmissionListItemResponse]
    score_by_form: list[FormScoreStat] = []
    score_trend: list[ScoreTrendPoint] = []


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    created_at: datetime
    read: bool = False
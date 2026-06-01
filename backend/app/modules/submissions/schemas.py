from datetime import date, datetime

from pydantic import BaseModel, Field


class SubmissionCreateRequest(BaseModel):
    form_id: str = Field(min_length=1, max_length=36)


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


class SubmissionResponse(BaseModel):
    id: str
    form_id: str
    form_version_id: str
    form_name: str
    status: str
    score: float | None
    score_breakdown: ScoreBreakdown | None
    started_at: datetime
    finished_at: datetime | None
    answers: list[SubmissionAnswerResponse]


class SubmissionListItemResponse(BaseModel):
    id: str
    form_id: str
    form_name: str
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
from pydantic import BaseModel

from app.modules.forms.schemas import FormListItemResponse
from app.modules.submissions.schemas import SubmissionListItemResponse


class SearchResponse(BaseModel):
    forms: list[FormListItemResponse]
    submissions: list[SubmissionListItemResponse]

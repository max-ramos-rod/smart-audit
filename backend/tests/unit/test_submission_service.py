from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.modules.submissions.pdf import generate_submission_pdf
from app.modules.submissions.service import SubmissionService


def make_field(field_type: str, key: str = "campo", allow_na: bool = False) -> MagicMock:
    field = MagicMock()
    field.field_type = field_type
    field.key = key
    field.config_json = {"allow_na": allow_na}
    return field


def make_weighted_submission(
    answers: list[tuple[bool | None | str, float]],
) -> MagicMock:
    """Build a mock Submission with weighted boolean fields.
    answers: list of (value, weight) where value can be True/False/None/"na".
    """
    submission = MagicMock()
    fields, values = [], []
    for i, (answer, weight) in enumerate(answers):
        field = MagicMock()
        field.field_type = "boolean"
        field.id = str(i)
        field.config_json = {"weight": weight}
        fields.append(field)
        if answer is not None:
            sv = MagicMock()
            sv.form_field_id = str(i)
            if answer == "na":
                sv.value_text = "na"
                sv.value_boolean = None
            else:
                sv.value_boolean = answer
                sv.value_text = None
            values.append(sv)
    submission.form_version.fields = fields
    submission.values = values
    return submission


def make_breakdown_submission(entries: list[bool | None | str]) -> MagicMock:
    """Submission for score_breakdown tests. None = unanswered, "na" = N/A."""
    submission = MagicMock()
    fields, values = [], []
    for i, answer in enumerate(entries):
        field = MagicMock()
        field.field_type = "boolean"
        field.id = str(i)
        fields.append(field)
        if answer is not None:
            sv = MagicMock()
            sv.form_field_id = str(i)
            if answer == "na":
                sv.value_text = "na"
                sv.value_boolean = None
            else:
                sv.value_boolean = answer
                sv.value_text = None
            values.append(sv)
    submission.form_version.fields = fields
    submission.values = values
    return submission


# ---------------------------------------------------------------------------
# normalize_value
# ---------------------------------------------------------------------------

class TestNormalizeValue:
    def test_boolean_true(self):
        assert SubmissionService.normalize_value(make_field("boolean"), True) is True

    def test_boolean_false(self):
        assert SubmissionService.normalize_value(make_field("boolean"), False) is False

    def test_boolean_non_bool_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            SubmissionService.normalize_value(make_field("boolean"), "sim")
        assert exc_info.value.status_code == 400

    def test_number_int_becomes_float(self):
        result = SubmissionService.normalize_value(make_field("number"), 42)
        assert result == 42.0
        assert isinstance(result, float)

    def test_number_float(self):
        assert SubmissionService.normalize_value(make_field("number"), 3.14) == pytest.approx(3.14)

    def test_number_string_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            SubmissionService.normalize_value(make_field("number"), "dez")
        assert exc_info.value.status_code == 400

    def test_date_from_iso_string(self):
        result = SubmissionService.normalize_value(make_field("date"), "2024-06-01")
        assert result == date(2024, 6, 1)

    def test_date_from_date_object_passes_through(self):
        d = date(2024, 6, 1)
        assert SubmissionService.normalize_value(make_field("date"), d) == d

    def test_date_invalid_type_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            SubmissionService.normalize_value(make_field("date"), 12345)
        assert exc_info.value.status_code == 400

    def test_date_invalid_string_raises(self):
        with pytest.raises((HTTPException, ValueError)):
            SubmissionService.normalize_value(make_field("date"), "nao-e-data")

    def test_select_dict_passes_through(self):
        value = {"option": "opcao_a"}
        assert SubmissionService.normalize_value(make_field("select"), value) == value

    def test_text_string(self):
        assert SubmissionService.normalize_value(make_field("text"), "resposta") == "resposta"

    def test_text_non_string_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            SubmissionService.normalize_value(make_field("text"), 123)
        assert exc_info.value.status_code == 400

    def test_photo_string(self):
        url = "https://bucket.s3.amazonaws.com/foto.jpg"
        assert SubmissionService.normalize_value(make_field("photo"), url) == url

    def test_none_returns_none_for_text(self):
        assert SubmissionService.normalize_value(make_field("text"), None) is None

    def test_none_for_boolean_raises(self):
        # boolean rejeita None — a checagem isinstance(bool) ocorre antes do fallback None
        with pytest.raises(HTTPException) as exc_info:
            SubmissionService.normalize_value(make_field("boolean"), None)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# calculate_score
# ---------------------------------------------------------------------------

def make_submission(boolean_answers: list[bool | None]) -> MagicMock:
    """
    Builds a mock Submission with boolean fields only.
    Pass None to simulate an unanswered field (no SubmissionValue created).
    """
    submission = MagicMock()
    fields = []
    values = []
    for i, answer in enumerate(boolean_answers):
        field = MagicMock()
        field.field_type = "boolean"
        field.id = str(i)
        fields.append(field)
        if answer is not None:
            sv = MagicMock()
            sv.form_field_id = str(i)
            sv.value_boolean = answer
            values.append(sv)
    submission.form_version.fields = fields
    submission.values = values
    return submission


class TestCalculateScore:
    def test_all_true_is_100(self):
        sub = make_submission([True, True, True])
        assert SubmissionService.calculate_score(sub) == 100.0

    def test_all_false_is_0(self):
        sub = make_submission([False, False])
        assert SubmissionService.calculate_score(sub) == 0.0

    def test_half_true(self):
        sub = make_submission([True, False])
        assert SubmissionService.calculate_score(sub) == 50.0

    def test_two_thirds_true(self):
        sub = make_submission([True, True, False])
        assert SubmissionService.calculate_score(sub) == pytest.approx(66.67)

    def test_no_boolean_fields_returns_none(self):
        submission = MagicMock()
        text_field = MagicMock()
        text_field.field_type = "text"
        submission.form_version.fields = [text_field]
        submission.values = []
        assert SubmissionService.calculate_score(submission) is None

    def test_unanswered_booleans_excluded_from_score(self):
        # 2 boolean fields, only 1 answered (True) — score should be 100%, not 50%
        sub = make_submission([True, None])
        assert SubmissionService.calculate_score(sub) == 100.0

    def test_all_unanswered_returns_none(self):
        sub = make_submission([None, None])
        assert SubmissionService.calculate_score(sub) is None

    def test_mixed_field_types_only_counts_booleans(self):
        submission = MagicMock()
        bool_field = MagicMock()
        bool_field.field_type = "boolean"
        bool_field.id = "1"
        text_field = MagicMock()
        text_field.field_type = "text"
        text_field.id = "2"
        submission.form_version.fields = [bool_field, text_field]
        sv = MagicMock()
        sv.form_field_id = "1"
        sv.value_boolean = True
        submission.values = [sv]
        assert SubmissionService.calculate_score(submission) == 100.0


# ---------------------------------------------------------------------------
# extract_value
# ---------------------------------------------------------------------------

class TestExtractValue:
    def test_boolean_true(self):
        sv = MagicMock()
        sv.value_boolean = True
        assert SubmissionService.extract_value(sv, "boolean") is True

    def test_boolean_false(self):
        sv = MagicMock()
        sv.value_boolean = False
        assert SubmissionService.extract_value(sv, "boolean") is False

    def test_number_float(self):
        sv = MagicMock()
        sv.value_number = 9.5
        assert SubmissionService.extract_value(sv, "number") == pytest.approx(9.5)

    def test_number_none(self):
        sv = MagicMock()
        sv.value_number = None
        assert SubmissionService.extract_value(sv, "number") is None

    def test_date(self):
        sv = MagicMock()
        sv.value_date = date(2024, 1, 15)
        assert SubmissionService.extract_value(sv, "date") == date(2024, 1, 15)

    def test_select_with_json(self):
        sv = MagicMock()
        sv.value_json = {"option": "A"}
        assert SubmissionService.extract_value(sv, "select") == {"option": "A"}

    def test_select_none(self):
        # sem value_json cai no fallback value_text; ambos None -> retorna None
        sv = MagicMock()
        sv.value_json = None
        sv.value_text = None
        assert SubmissionService.extract_value(sv, "select") is None

    def test_text(self):
        sv = MagicMock()
        sv.value_text = "resposta livre"
        assert SubmissionService.extract_value(sv, "text") == "resposta livre"

    def test_photo(self):
        sv = MagicMock()
        sv.value_text = "https://bucket/foto.jpg"
        assert SubmissionService.extract_value(sv, "photo") == "https://bucket/foto.jpg"

    def test_boolean_na(self):
        sv = MagicMock()
        sv.value_text = "na"
        assert SubmissionService.extract_value(sv, "boolean") == "na"

    def test_evidence_with_json(self):
        sv = MagicMock()
        sv.value_json = {"files": ["a.jpg"]}
        assert SubmissionService.extract_value(sv, "evidence") == {"files": ["a.jpg"]}


# ---------------------------------------------------------------------------
# normalize_value — section and N/A extensions
# ---------------------------------------------------------------------------

class TestNormalizeValueExtended:
    def test_section_always_returns_none(self):
        assert SubmissionService.normalize_value(make_field("section"), True) is None
        assert SubmissionService.normalize_value(make_field("section"), "anything") is None
        assert SubmissionService.normalize_value(make_field("section"), None) is None

    def test_boolean_na_with_allow_na_returns_na_string(self):
        field = make_field("boolean", allow_na=True)
        assert SubmissionService.normalize_value(field, "na") == "na"

    def test_boolean_na_without_allow_na_raises(self):
        field = make_field("boolean", allow_na=False)
        with pytest.raises(HTTPException) as exc_info:
            SubmissionService.normalize_value(field, "na")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# calculate_score — weighted and N/A
# ---------------------------------------------------------------------------

class TestCalculateScoreWeighted:
    def test_equal_weights_same_as_unweighted(self):
        sub = make_weighted_submission([(True, 1.0), (False, 1.0)])
        assert SubmissionService.calculate_score(sub) == pytest.approx(50.0)

    def test_higher_weight_on_true_increases_score(self):
        # True with weight 3, False with weight 1 → score = 3/4 = 75%
        sub = make_weighted_submission([(True, 3.0), (False, 1.0)])
        assert SubmissionService.calculate_score(sub) == pytest.approx(75.0)

    def test_higher_weight_on_false_decreases_score(self):
        # True with weight 1, False with weight 3 → score = 1/4 = 25%
        sub = make_weighted_submission([(True, 1.0), (False, 3.0)])
        assert SubmissionService.calculate_score(sub) == pytest.approx(25.0)

    def test_na_answer_excluded_from_score(self):
        # One True, one N/A → N/A excluded → score = 1/1 = 100%
        sub = make_weighted_submission([(True, 1.0), ("na", 1.0)])
        assert SubmissionService.calculate_score(sub) == pytest.approx(100.0)

    def test_only_na_answers_returns_none(self):
        sub = make_weighted_submission([("na", 1.0), ("na", 2.0)])
        assert SubmissionService.calculate_score(sub) is None

    def test_unanswered_excluded_from_score(self):
        # One True answered, one None (unanswered) → score = 100%
        sub = make_weighted_submission([(True, 1.0), (None, 1.0)])
        assert SubmissionService.calculate_score(sub) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# calculate_score_breakdown
# ---------------------------------------------------------------------------

class TestCalculateScoreBreakdown:
    def test_no_boolean_fields_returns_none(self):
        submission = MagicMock()
        text_field = MagicMock()
        text_field.field_type = "text"
        submission.form_version.fields = [text_field]
        submission.values = []
        assert SubmissionService.calculate_score_breakdown(submission) is None

    def test_all_conformes(self):
        sub = make_breakdown_submission([True, True, True])
        bd = SubmissionService.calculate_score_breakdown(sub)
        assert bd is not None
        assert bd.total_boolean == 3
        assert bd.conformes == 3
        assert bd.nao_conformes == 0
        assert bd.sem_resposta == 0
        assert bd.na_count == 0

    def test_na_counted_separately(self):
        sub = make_breakdown_submission([True, "na", False])
        bd = SubmissionService.calculate_score_breakdown(sub)
        assert bd is not None
        assert bd.total_boolean == 3
        assert bd.conformes == 1
        assert bd.nao_conformes == 1
        assert bd.na_count == 1
        assert bd.sem_resposta == 0

    def test_unanswered_counted_in_sem_resposta(self):
        sub = make_breakdown_submission([True, None, None])
        bd = SubmissionService.calculate_score_breakdown(sub)
        assert bd is not None
        assert bd.sem_resposta == 2
        assert bd.conformes == 1

    def test_all_unanswered_returns_zero_score_counts(self):
        sub = make_breakdown_submission([None, None])
        bd = SubmissionService.calculate_score_breakdown(sub)
        assert bd is not None
        assert bd.sem_resposta == 2
        assert bd.conformes == 0
        assert bd.nao_conformes == 0
        assert bd.na_count == 0

    def test_totals_always_sum_to_total_boolean(self):
        sub = make_breakdown_submission([True, False, "na", None, True])
        bd = SubmissionService.calculate_score_breakdown(sub)
        assert bd is not None
        assert bd.conformes + bd.nao_conformes + bd.sem_resposta + bd.na_count == bd.total_boolean


# ---------------------------------------------------------------------------
# parse_period_start
# ---------------------------------------------------------------------------

class TestParsePeriodStart:
    def test_7d_returns_roughly_7_days_ago(self):
        result = SubmissionService.parse_period_start("7d")
        assert result is not None
        delta = datetime.now(UTC) - result
        assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)

    def test_30d_returns_roughly_30_days_ago(self):
        result = SubmissionService.parse_period_start("30d")
        assert result is not None
        delta = datetime.now(UTC) - result
        assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)

    def test_90d_returns_roughly_90_days_ago(self):
        result = SubmissionService.parse_period_start("90d")
        assert result is not None
        delta = datetime.now(UTC) - result
        assert timedelta(days=89, hours=23) < delta < timedelta(days=90, hours=1)

    def test_none_returns_none(self):
        assert SubmissionService.parse_period_start(None) is None

    def test_unknown_string_returns_none(self):
        assert SubmissionService.parse_period_start("forever") is None
        assert SubmissionService.parse_period_start("all") is None


# ---------------------------------------------------------------------------
# PDF generation smoke tests
# ---------------------------------------------------------------------------

def _base_pdf_kwargs(**overrides):
    return {
        "company_name": "Acme Corp",
        "form_name": "Checklist de Segurança",
        "form_version": 1,
        "inspector_name": "João Silva",
        "status": "completed",
        "score": 80.0,
        "started_at": datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
        "finished_at": datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        "fields_with_answers": [],
        **overrides,
    }


class TestPdfGeneration:
    def test_returns_valid_pdf_bytes(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs())
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"

    def test_section_field_rendered_without_crash(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(
            fields_with_answers=[
                {"position": 1, "label": "Bloco A", "field_type": "section", "value": None},
                {"position": 2, "label": "Item", "field_type": "boolean", "value": True},
            ]
        ))
        assert pdf[:4] == b"%PDF"

    def test_na_boolean_rendered_without_crash(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(
            fields_with_answers=[
                {"position": 1, "label": "Item N/A", "field_type": "boolean", "value": "na"},
            ]
        ))
        assert pdf[:4] == b"%PDF"

    def test_no_score_breakdown_renders_without_crash(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(score_breakdown=None))
        assert pdf[:4] == b"%PDF"

    def test_with_full_score_breakdown(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(
            score_breakdown={
                "total_boolean": 4,
                "conformes": 2,
                "nao_conformes": 1,
                "sem_resposta": 0,
                "na_count": 1,
            }
        ))
        assert pdf[:4] == b"%PDF"

    def test_zero_score_renders(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(score=0.0))
        assert pdf[:4] == b"%PDF"

    def test_none_score_renders(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(score=None))
        assert pdf[:4] == b"%PDF"

    def test_evidence_field_rendered(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(
            fields_with_answers=[
                {"position": 1, "label": "Foto do local", "field_type": "evidence", "value": {"files": []}},
            ]
        ))
        assert pdf[:4] == b"%PDF"

    def test_all_field_types_rendered(self):
        pdf = generate_submission_pdf(**_base_pdf_kwargs(
            fields_with_answers=[
                {"position": 1, "label": "Seção", "field_type": "section", "value": None},
                {"position": 2, "label": "Bool ok", "field_type": "boolean", "value": True},
                {"position": 3, "label": "Bool nok", "field_type": "boolean", "value": False},
                {"position": 4, "label": "Bool na", "field_type": "boolean", "value": "na"},
                {"position": 5, "label": "Texto", "field_type": "text", "value": "resposta"},
                {"position": 6, "label": "Número", "field_type": "number", "value": 42.5},
                {"position": 7, "label": "Data", "field_type": "date", "value": date(2025, 6, 1)},
                {"position": 8, "label": "Select", "field_type": "select", "value": {"option": "A"}},
                {"position": 9, "label": "Foto", "field_type": "photo", "value": "http://x.com/f.jpg"},
                {"position": 10, "label": "Evidência", "field_type": "evidence", "value": None},
            ]
        ))
        assert pdf[:4] == b"%PDF"

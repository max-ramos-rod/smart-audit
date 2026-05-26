from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.modules.submissions.service import SubmissionService


def make_field(field_type: str, key: str = "campo") -> MagicMock:
    field = MagicMock()
    field.field_type = field_type
    field.key = key
    return field


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

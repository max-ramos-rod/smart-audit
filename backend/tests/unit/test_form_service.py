import pytest
from fastapi import HTTPException

from app.modules.forms.schemas import FormFieldCreateRequest
from app.modules.forms.service import FormService


def make_field(key: str, position: int, field_type: str = "boolean") -> FormFieldCreateRequest:
    return FormFieldCreateRequest(
        key=key,
        label=f"Label {key}",
        field_type=field_type,
        required=False,
        position=position,
    )


# ---------------------------------------------------------------------------
# validate_fields
# ---------------------------------------------------------------------------

class TestValidateFields:
    def test_empty_list_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            FormService.validate_fields([])
        assert exc_info.value.status_code == 400

    def test_duplicate_key_raises(self):
        fields = [make_field("chave", 1), make_field("chave", 2)]
        with pytest.raises(HTTPException) as exc_info:
            FormService.validate_fields(fields)
        assert exc_info.value.status_code == 400

    def test_duplicate_position_raises(self):
        fields = [make_field("a", 1), make_field("b", 1)]
        with pytest.raises(HTTPException) as exc_info:
            FormService.validate_fields(fields)
        assert exc_info.value.status_code == 400

    def test_single_field_is_valid(self):
        FormService.validate_fields([make_field("unico", 1)])

    def test_multiple_unique_fields_are_valid(self):
        fields = [make_field("a", 1), make_field("b", 2), make_field("c", 3)]
        FormService.validate_fields(fields)

    def test_all_field_types_accepted(self):
        fields = [
            make_field("bool_field", 1, "boolean"),
            make_field("text_field", 2, "text"),
            make_field("num_field", 3, "number"),
            make_field("date_field", 4, "date"),
            make_field("sel_field", 5, "select"),
            make_field("photo_field", 6, "photo"),
        ]
        FormService.validate_fields(fields)

    def test_duplicate_key_among_many_raises(self):
        fields = [
            make_field("a", 1),
            make_field("b", 2),
            make_field("a", 3),  # duplicate key
        ]
        with pytest.raises(HTTPException) as exc_info:
            FormService.validate_fields(fields)
        assert exc_info.value.status_code == 400

    def test_duplicate_position_among_many_raises(self):
        fields = [
            make_field("a", 1),
            make_field("b", 2),
            make_field("c", 2),  # duplicate position
        ]
        with pytest.raises(HTTPException) as exc_info:
            FormService.validate_fields(fields)
        assert exc_info.value.status_code == 400

    def test_evidence_and_section_types_accepted(self):
        fields = [
            make_field("s1", 1, "section"),
            make_field("ev1", 2, "evidence"),
            make_field("bool1", 3, "boolean"),
        ]
        FormService.validate_fields(fields)

    def test_section_key_uniqueness_still_enforced(self):
        fields = [
            make_field("same_key", 1, "section"),
            make_field("same_key", 2, "boolean"),
        ]
        with pytest.raises(HTTPException) as exc_info:
            FormService.validate_fields(fields)
        assert exc_info.value.status_code == 400

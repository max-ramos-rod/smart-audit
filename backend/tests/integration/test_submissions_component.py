"""DR-0002 Fases 2-4 / ADR-0016 — T1: dimensão de componente no modelo híbrido.

Prova o comportamento do novo UNIQUE(submission_id, form_field_id, asset_id):
o Postgres trata NULL como distinto, então o histórico (asset_id NULL) permanece
único por campo, enquanto componentes distintos coexistem no mesmo campo.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models.form_fields import FormField
from app.db.models.submission_values import SubmissionValue
from backend.tests.integration.test_submissions_asset import _create_asset, _create_form


async def _field_id(db_session, key: str = "item_ok") -> str:
    return await db_session.scalar(select(FormField.id).where(FormField.key == key))


async def test_unique_rejects_two_null_asset_rows_for_same_field(
    client, auth_headers, db_session
):
    # Retrocompat: asset_id NULL preserva "uma linha por campo" (comportamento atual).
    form_id = await _create_form(client, auth_headers)
    submission_id = (
        await client.post("/api/v1/submissions", headers=auth_headers, json={"form_id": form_id})
    ).json()["data"]["id"]
    field_id = await _field_id(db_session)

    db_session.add(
        SubmissionValue(submission_id=submission_id, form_field_id=field_id, value_boolean=True)
    )
    await db_session.flush()

    db_session.add(
        SubmissionValue(submission_id=submission_id, form_field_id=field_id, value_boolean=False)
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_unique_allows_distinct_assets_for_same_field(client, auth_headers, db_session):
    # Núcleo do DR-0002: o mesmo campo pode ter uma resposta por componente.
    form_id = await _create_form(client, auth_headers)
    submission_id = (
        await client.post("/api/v1/submissions", headers=auth_headers, json={"form_id": form_id})
    ).json()["data"]["id"]
    asset_a = await _create_asset(client, auth_headers, "Componente A")
    asset_b = await _create_asset(client, auth_headers, "Componente B")
    field_id = await _field_id(db_session)

    db_session.add_all(
        [
            SubmissionValue(
                submission_id=submission_id,
                form_field_id=field_id,
                asset_id=asset_a,
                value_boolean=True,
            ),
            SubmissionValue(
                submission_id=submission_id,
                form_field_id=field_id,
                asset_id=asset_b,
                value_boolean=False,
            ),
        ]
    )
    # Não deve violar o UNIQUE — asset_id distinto.
    await db_session.flush()

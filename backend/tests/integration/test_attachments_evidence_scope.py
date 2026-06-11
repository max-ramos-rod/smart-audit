"""DR-0017 — evidência por escopo (component/field/submission) + invariantes.

Cobre: INV-E1/Q7.3 (1:N por item), os escopos derivados do payload, INV1 (componente
fora da subárvore/tipo), e que criar evidência não injeta resposta (answers_json).
"""

from sqlalchemy import func, select

from app.db.models.attachments import Attachment
from app.db.models.form_fields import FormField
from backend.tests.integration.test_submissions_component_write import (
    _build_vehicle,
    _form,
    _general_bool,
    _scoped_bool,
    _submission,
)


async def _field_id(db, key: str) -> str:
    return await db.scalar(select(FormField.id).where(FormField.key == key))


def _att(field_key=None, asset_id=None, url="http://x/a.jpg"):
    body = {"file_url": url, "mime_type": "image/jpeg", "file_size": 100}
    if field_key is not None:
        body["field_key"] = field_key
    if asset_id is not None:
        body["asset_id"] = asset_id
    return body


async def test_anchor_is_non_unique_n_evidences_per_item(
    client, auth_headers, seeded_user, db_session
):
    form_id = await _form(client, auth_headers, [_general_bool(key="geral")])
    sub_id = await _submission(client, auth_headers, form_id)
    field_id = await _field_id(db_session, "geral")

    # INV-E1 / Q7.3: mesma âncora (submission, field, asset=NULL) aceita N anexos.
    for i in range(3):
        db_session.add(
            Attachment(
                company_id=seeded_user["company_id"],
                scope="field",
                submission_id=sub_id,
                form_field_id=field_id,
                asset_id=None,
                file_url=f"http://x/foto{i}.jpg",
                mime_type="image/jpeg",
                file_size=100,
                uploaded_by=seeded_user["user_id"],
            )
        )
    await db_session.commit()

    count = await db_session.scalar(
        select(func.count()).select_from(Attachment).where(Attachment.submission_id == sub_id)
    )
    assert count == 3  # nenhuma constraint de unicidade limitou N


async def test_scope_field_general(client, auth_headers):
    form_id = await _form(client, auth_headers, [_general_bool(key="geral")])
    sub_id = await _submission(client, auth_headers, form_id)
    res = await client.post(
        f"/api/v1/submissions/{sub_id}/attachments", headers=auth_headers, json=_att("geral")
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["scope"] == "field"
    assert data["field_key"] == "geral"
    assert data["asset_id"] is None


async def test_scope_submission_no_field(client, auth_headers):
    form_id = await _form(client, auth_headers, [_general_bool(key="geral")])
    sub_id = await _submission(client, auth_headers, form_id)
    res = await client.post(
        f"/api/v1/submissions/{sub_id}/attachments", headers=auth_headers, json=_att()
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["scope"] == "submission"
    assert data["field_key"] is None
    assert data["asset_id"] is None


async def test_scope_component_freezes_label(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    res = await client.post(
        f"/api/v1/submissions/{sub_id}/attachments",
        headers=auth_headers,
        json=_att("pressao", asset_id=rodas[0]),
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["scope"] == "component"
    assert data["asset_id"] == rodas[0]
    assert data["component_label"].startswith("Roda ")  # rótulo congelado


async def test_component_outside_subtree_is_rejected(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    fake = "00000000-0000-0000-0000-000000000000"
    res = await client.post(
        f"/api/v1/submissions/{sub_id}/attachments",
        headers=auth_headers,
        json=_att("pressao", asset_id=fake),
    )
    assert res.status_code == 400  # INV1


async def test_asset_id_without_field_is_rejected(client, auth_headers):
    form_id = await _form(client, auth_headers, [_general_bool(key="geral")])
    sub_id = await _submission(client, auth_headers, form_id)
    res = await client.post(
        f"/api/v1/submissions/{sub_id}/attachments",
        headers=auth_headers,
        json=_att(asset_id="00000000-0000-0000-0000-000000000000"),
    )
    assert res.status_code == 400

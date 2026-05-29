import pytest

from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem

_PHOTO_FIELD = {
    "key": "foto_extintor",
    "label": "Foto do extintor",
    "field_type": "photo",
    "required": True,
    "position": 1,
    "config_json": {},
}

_SECOND_FIELD = {
    "key": "foto_saida",
    "label": "Foto da saida de emergencia",
    "field_type": "photo",
    "required": False,
    "position": 2,
    "config_json": {},
}

_ATTACHMENT_PAYLOAD = {
    "field_key": "foto_extintor",
    "file_url": "https://files.example.com/extintor.jpg",
    "thumbnail_url": "https://files.example.com/extintor-thumb.jpg",
    "mime_type": "image/jpeg",
    "file_size": 245760,
}


async def _create_form_and_submission(client, auth_headers, fields=None):
    fields = fields or [_PHOTO_FIELD]
    form_resp = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={"name": "Checklist Evidencias", "description": "Testes de attachment", "fields": fields},
    )
    form_id = form_resp.json()["data"]["id"]

    sub_resp = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id},
    )
    assert sub_resp.status_code == 200
    return sub_resp.json()["data"]["id"]


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_attachments_empty_on_new_submission(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    resp = await client.get(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"] == []
    assert_pagination_meta(payload, total=0, page=1, page_size=20, has_next=False, total_pages=0)


async def test_list_attachments_requires_auth(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    assert_problem(
        await client.get(f"/api/v1/submissions/{submission_id}/attachments"),
        401,
        "Token de acesso nao informado.",
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_attachment_returns_correct_shape(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    resp = await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
        json=_ATTACHMENT_PAYLOAD,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["submission_id"] == submission_id
    assert data["field_key"] == "foto_extintor"
    assert data["file_url"] == _ATTACHMENT_PAYLOAD["file_url"]
    assert data["thumbnail_url"] == _ATTACHMENT_PAYLOAD["thumbnail_url"]
    assert data["mime_type"] == "image/jpeg"
    assert data["file_size"] == 245760
    assert data["id"]
    assert data["created_at"]


async def test_create_attachment_without_thumbnail(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    resp = await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
        json={
            "field_key": "foto_extintor",
            "file_url": "https://files.example.com/img.png",
            "mime_type": "image/png",
            "file_size": 10240,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["thumbnail_url"] is None


async def test_create_attachment_updates_answers_json(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
        json=_ATTACHMENT_PAYLOAD,
    )

    detail_resp = await client.get(
        f"/api/v1/submissions/{submission_id}",
        headers=auth_headers,
    )
    assert detail_resp.status_code == 200
    answers = detail_resp.json()["data"]["answers"]
    keys = [a["field_key"] for a in answers]
    assert "foto_extintor" in keys


async def test_create_two_attachments_on_different_fields(client, auth_headers):
    submission_id = await _create_form_and_submission(
        client, auth_headers, fields=[_PHOTO_FIELD, _SECOND_FIELD]
    )

    for field_key, url in [
        ("foto_extintor", "https://files.example.com/ext.jpg"),
        ("foto_saida", "https://files.example.com/saida.jpg"),
    ]:
        resp = await client.post(
            f"/api/v1/submissions/{submission_id}/attachments",
            headers=auth_headers,
            json={"field_key": field_key, "file_url": url, "mime_type": "image/jpeg", "file_size": 1024},
        )
        assert resp.status_code == 200

    list_resp = await client.get(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert len(payload["data"]) == 2
    assert_pagination_meta(payload, total=2, page=1, page_size=20, has_next=False, total_pages=1)


async def test_list_attachments_after_create(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
        json=_ATTACHMENT_PAYLOAD,
    )

    list_resp = await client.get(
        f"/api/v1/submissions/{submission_id}/attachments?page=1&page_size=10",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert len(payload["data"]) == 1
    assert_pagination_meta(payload, total=1, page=1, page_size=10, has_next=False, total_pages=1)
    assert payload["data"][0]["field_key"] == "foto_extintor"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


async def test_create_attachment_invalid_field_key(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    assert_problem(
        await client.post(
            f"/api/v1/submissions/{submission_id}/attachments",
            headers=auth_headers,
            json={**_ATTACHMENT_PAYLOAD, "field_key": "campo_inexistente"},
        ),
        400,
        "Campo da evidencia nao encontrado.",
    )


async def test_create_attachment_submission_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"

    assert_problem(
        await client.post(
            f"/api/v1/submissions/{fake_id}/attachments",
            headers=auth_headers,
            json=_ATTACHMENT_PAYLOAD,
        ),
        404,
        "Inspecao nao encontrada.",
    )


async def test_create_attachment_requires_auth(client, auth_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    assert_problem(
        await client.post(
            f"/api/v1/submissions/{submission_id}/attachments",
            json=_ATTACHMENT_PAYLOAD,
        ),
        401,
        "Token de acesso nao informado.",
    )


async def test_create_attachment_cross_company_returns_404(client, auth_headers, inspector_headers):
    submission_id = await _create_form_and_submission(client, auth_headers)

    # inspector_headers belongs to a different company seed — submission not visible
    resp = await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=inspector_headers,
        json=_ATTACHMENT_PAYLOAD,
    )
    # 404 because the repo filters by company_id — submission not found from other tenant
    assert resp.status_code == 404

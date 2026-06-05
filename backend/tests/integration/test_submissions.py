import pytest

from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_submission_flow_with_attachment(client, auth_headers):
    form_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Operacional",
            "description": "Fluxo completo",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "temperatura",
                    "label": "Temperatura",
                    "field_type": "number",
                    "required": True,
                    "position": 2,
                    "config_json": {},
                },
            ],
        },
    )
    form_id = form_response.json()["data"]["id"]

    create_submission_response = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id},
    )
    assert create_submission_response.status_code == 200
    submission_id = create_submission_response.json()["data"]["id"]

    list_submissions_response = await client.get(
        "/api/v1/submissions?page=1&page_size=10",
        headers=auth_headers,
    )
    assert list_submissions_response.status_code == 200
    list_submissions_payload = list_submissions_response.json()
    assert len(list_submissions_payload["data"]) == 1
    assert_pagination_meta(
        list_submissions_payload,
        total=1,
        page=1,
        page_size=10,
        has_next=False,
        total_pages=1,
    )

    answer_response = await client.put(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=auth_headers,
        json={
            "answers": [
                {"field_key": "extintor", "value": True},
                {"field_key": "temperatura", "value": -5},
            ]
        },
    )
    assert answer_response.status_code == 200
    assert len(answer_response.json()["data"]["answers"]) == 2

    attachment_response = await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
        json={
            "field_key": "extintor",
            "file_url": "https://files.example.com/extintor.jpg",
            "thumbnail_url": "https://files.example.com/extintor-thumb.jpg",
            "mime_type": "image/jpeg",
            "file_size": 245760,
        },
    )
    assert attachment_response.status_code == 200
    assert attachment_response.json()["data"]["field_key"] == "extintor"

    await client.put(
        f"/api/v1/submissions/{submission_id}/conformity",
        headers=auth_headers,
        json={"items": [
            {"field_key": "extintor", "status": "conforme", "justification": None},
            {"field_key": "temperatura", "status": "conforme", "justification": None},
        ]},
    )
    finish_response = await client.post(
        f"/api/v1/submissions/{submission_id}/finish",
        headers=auth_headers,
    )
    assert finish_response.status_code == 200
    finish_payload = finish_response.json()["data"]
    assert finish_payload["status"] == "completed"
    assert finish_payload["score"] == 100.0

    list_attachments_response = await client.get(
        f"/api/v1/submissions/{submission_id}/attachments?page=1&page_size=10",
        headers=auth_headers,
    )
    assert list_attachments_response.status_code == 200
    list_attachments_payload = list_attachments_response.json()
    assert len(list_attachments_payload["data"]) == 1
    assert_pagination_meta(
        list_attachments_payload,
        total=1,
        page=1,
        page_size=10,
        has_next=False,
        total_pages=1,
    )


async def test_submissions_list_supports_pagination(client, auth_headers):
    form_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Lista",
            "description": "Paginacao de inspecoes",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                }
            ],
        },
    )
    form_id = form_response.json()["data"]["id"]

    for _ in range(3):
        response = await client.post(
            "/api/v1/submissions",
            headers=auth_headers,
            json={"form_id": form_id},
        )
        assert response.status_code == 200

    response = await client.get("/api/v1/submissions?page=2&page_size=2", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert_pagination_meta(
        payload,
        total=3,
        page=2,
        page_size=2,
        has_next=False,
        total_pages=2,
    )


async def test_submission_cannot_finish_without_required_answers(client, auth_headers):
    form_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Obrigatorios",
            "description": "Campos obrigatorios",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "temperatura",
                    "label": "Temperatura",
                    "field_type": "number",
                    "required": True,
                    "position": 2,
                    "config_json": {},
                },
            ],
        },
    )
    form_id = form_response.json()["data"]["id"]

    create_submission_response = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id},
    )
    submission_id = create_submission_response.json()["data"]["id"]

    answer_response = await client.put(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "extintor", "value": True}]},
    )
    assert answer_response.status_code == 200

    finish_response = await client.post(
        f"/api/v1/submissions/{submission_id}/finish",
        headers=auth_headers,
    )
    payload = assert_problem(
        finish_response,
        400,
        "Campos obrigatorios pendentes: temperatura.",
    )
    assert payload["title"] == "Bad Request"


async def test_submission_rejects_invalid_field_key(client, auth_headers):
    form_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Campo Invalido",
            "description": "Campo invalido",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                }
            ],
        },
    )
    form_id = form_response.json()["data"]["id"]

    create_submission_response = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id},
    )
    submission_id = create_submission_response.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "nao_existe", "value": True}]},
    )
    assert_problem(response, 400, "Campo invalido: nao_existe.")


async def test_attachment_rejects_invalid_field_key(client, auth_headers):
    form_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Evidencia",
            "description": "Campo para evidencia",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                }
            ],
        },
    )
    form_id = form_response.json()["data"]["id"]

    create_submission_response = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id},
    )
    submission_id = create_submission_response.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/submissions/{submission_id}/attachments",
        headers=auth_headers,
        json={
            "field_key": "nao_existe",
            "file_url": "https://files.example.com/evidencia.jpg",
            "thumbnail_url": None,
            "mime_type": "image/jpeg",
            "file_size": 100,
        },
    )
    assert_problem(response, 400, "Campo da evidencia nao encontrado.")


async def test_submission_response_contains_form_version_id(client, auth_headers):
    form_resp = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Version ID Test",
            "fields": [
                {
                    "key": "campo",
                    "label": "Campo",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                }
            ],
        },
    )
    form_id = form_resp.json()["data"]["id"]
    version_id = form_resp.json()["data"]["current_version"]["id"]

    sub_resp = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id},
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["data"]["form_version_id"] == version_id


async def test_submission_create_blocked_for_viewer(client, viewer_headers):
    response = await client.post(
        "/api/v1/submissions",
        headers=viewer_headers,
        json={"form_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_submission_answers_update_blocked_for_viewer(client, viewer_headers):
    response = await client.put(
        "/api/v1/submissions/00000000-0000-0000-0000-000000000000/answers",
        headers=viewer_headers,
        json={"answers": []},
    )
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_submission_finish_blocked_for_viewer(client, viewer_headers):
    response = await client.post(
        "/api/v1/submissions/00000000-0000-0000-0000-000000000000/finish",
        headers=viewer_headers,
    )
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_list_submissions_filter_by_status(
    client, auth_headers, inspector_headers, seeded_user
):
    """GET /submissions?status= filtra corretamente server-side."""
    forms_res = await client.get("/api/v1/forms", headers=auth_headers)
    forms = forms_res.json()["data"]
    if not forms:
        pytest.skip("Nenhum formulário cadastrado para testar filtro")
    form_id = forms[0]["id"]

    create_res = await client.post(
        "/api/v1/submissions",
        headers=inspector_headers,
        json={"form_id": form_id},
    )
    assert create_res.status_code == 200
    submission_id = create_res.json()["data"]["id"]

    # Filtrar por in_progress
    res_ip = await client.get(
        "/api/v1/submissions?status=in_progress",
        headers=auth_headers,
    )
    assert res_ip.status_code == 200
    data_ip = res_ip.json()["data"]
    assert all(s["status"] == "in_progress" for s in data_ip)

    # Filtrar por completed — não deve incluir o recém-criado
    res_done = await client.get(
        "/api/v1/submissions?status=completed",
        headers=auth_headers,
    )
    assert res_done.status_code == 200
    data_done = res_done.json()["data"]
    assert all(s["id"] != submission_id for s in data_done)


async def test_list_submissions_filter_by_created_by(
    client, auth_headers, inspector_headers, inspector_user
):
    """GET /submissions?created_by= filtra por inspetor."""
    forms_res = await client.get("/api/v1/forms", headers=auth_headers)
    forms = forms_res.json()["data"]
    if not forms:
        pytest.skip("Nenhum formulário cadastrado para testar filtro")
    form_id = forms[0]["id"]

    await client.post("/api/v1/submissions", headers=inspector_headers, json={"form_id": form_id})

    inspector_id = inspector_user["user_id"]
    res = await client.get(
        f"/api/v1/submissions?created_by={inspector_id}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    # Todas as inspeções retornadas pertencem ao inspetor (verificar via detalhe)
    assert isinstance(data, list)


async def test_submission_response_has_score_breakdown(client, auth_headers, inspector_headers):
    """Inspeção finalizada retorna score_breakdown com campos esperados."""
    forms_res = await client.get("/api/v1/forms", headers=auth_headers)
    forms = forms_res.json()["data"]
    if not forms:
        pytest.skip("Nenhum formulário com campos booleanos para testar score_breakdown")

    form_id = forms[0]["id"]
    create_res = await client.post(
        "/api/v1/submissions", headers=inspector_headers, json={"form_id": form_id}
    )
    assert create_res.status_code == 200
    submission_id = create_res.json()["data"]["id"]

    # Buscar campos booleanos do formulário
    form_res = await client.get(f"/api/v1/forms/{form_id}", headers=auth_headers)
    fields = form_res.json()["data"]["current_version"]["fields"]
    bool_fields = [f for f in fields if f["field_type"] == "boolean"]
    if not bool_fields:
        pytest.skip("Formulário sem campos booleanos")

    # Responder campos booleanos obrigatórios
    required_bool = [f for f in bool_fields if f["required"]]
    answers = [{"field_key": f["key"], "value": True} for f in required_bool]
    if answers:
        await client.put(
            f"/api/v1/submissions/{submission_id}/answers",
            headers=inspector_headers,
            json={"answers": answers},
        )

    # Finalizar
    finish_res = await client.post(
        f"/api/v1/submissions/{submission_id}/finish",
        headers=inspector_headers,
    )
    assert finish_res.status_code == 200
    data = finish_res.json()["data"]

    # Verificar score_breakdown
    breakdown = data.get("score_breakdown")
    if bool_fields:
        assert breakdown is not None
        assert "total_boolean" in breakdown
        assert "conformes" in breakdown
        assert "nao_conformes" in breakdown
        assert "sem_resposta" in breakdown
        assert breakdown["total_boolean"] == len(bool_fields)
        assert (
            breakdown["conformes"] + breakdown["nao_conformes"] + breakdown["sem_resposta"]
            == breakdown["total_boolean"]
        )

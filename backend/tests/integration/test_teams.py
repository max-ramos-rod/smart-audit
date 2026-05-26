from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_teams_create_list_detail_update_and_delete(client, auth_headers):
    create_response = await client.post(
        "/api/v1/teams",
        headers=auth_headers,
        json={"name": "Equipe Eletrica"},
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["name"] == "Equipe Eletrica"
    assert created["members"] == []
    team_id = created["id"]

    list_response = await client.get("/api/v1/teams?page=1&page_size=10", headers=auth_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["data"]) == 1
    assert list_payload["data"][0]["member_count"] == 0
    assert_pagination_meta(list_payload, total=1, page=1, page_size=10, has_next=False, total_pages=1)

    detail_response = await client.get(f"/api/v1/teams/{team_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["name"] == "Equipe Eletrica"
    assert detail["members"] == []

    update_response = await client.patch(
        f"/api/v1/teams/{team_id}",
        headers=auth_headers,
        json={"name": "Equipe Manutencao"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Equipe Manutencao"

    delete_response = await client.delete(f"/api/v1/teams/{team_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    assert_problem(
        await client.get(f"/api/v1/teams/{team_id}", headers=auth_headers),
        404,
        "Equipe nao encontrada.",
    )


async def test_teams_add_and_remove_member(client, auth_headers, seeded_user):
    team_response = await client.post(
        "/api/v1/teams",
        headers=auth_headers,
        json={"name": "Equipe Seguranca"},
    )
    team_id = team_response.json()["data"]["id"]

    add_response = await client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=auth_headers,
        json={"user_id": seeded_user["user_id"]},
    )
    assert add_response.status_code == 200
    members = add_response.json()["data"]["members"]
    assert len(members) == 1
    assert members[0]["user_id"] == seeded_user["user_id"]

    remove_response = await client.delete(
        f"/api/v1/teams/{team_id}/members/{seeded_user['user_id']}",
        headers=auth_headers,
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["data"]["members"] == []


async def test_teams_add_duplicate_member_is_rejected(client, auth_headers, seeded_user):
    team_id = (
        await client.post(
            "/api/v1/teams",
            headers=auth_headers,
            json={"name": "Equipe Duplicata"},
        )
    ).json()["data"]["id"]

    await client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=auth_headers,
        json={"user_id": seeded_user["user_id"]},
    )

    assert_problem(
        await client.post(
            f"/api/v1/teams/{team_id}/members",
            headers=auth_headers,
            json={"user_id": seeded_user["user_id"]},
        ),
        400,
        "Usuario ja e membro desta equipe.",
    )


async def test_teams_add_member_from_another_company_is_rejected(
    client, auth_headers, viewer_user
):
    team_id = (
        await client.post(
            "/api/v1/teams",
            headers=auth_headers,
            json={"name": "Equipe Isolada"},
        )
    ).json()["data"]["id"]

    assert_problem(
        await client.post(
            f"/api/v1/teams/{team_id}/members",
            headers=auth_headers,
            json={"user_id": viewer_user["user_id"]},
        ),
        400,
        "Usuario nao pertence a esta empresa.",
    )


async def test_teams_remove_nonexistent_member_returns_404(client, auth_headers):
    team_id = (
        await client.post(
            "/api/v1/teams",
            headers=auth_headers,
            json={"name": "Equipe Vazia"},
        )
    ).json()["data"]["id"]

    assert_problem(
        await client.delete(
            f"/api/v1/teams/{team_id}/members/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        ),
        404,
        "Usuario nao e membro desta equipe.",
    )


async def test_teams_create_blocked_for_inspector(client, inspector_headers):
    assert_problem(
        await client.post("/api/v1/teams", headers=inspector_headers, json={"name": "Negada"}),
        403,
        "Usuario sem permissao para executar esta acao.",
    )


async def test_teams_get_nonexistent_returns_404(client, auth_headers):
    assert_problem(
        await client.get("/api/v1/teams/00000000-0000-0000-0000-000000000000", headers=auth_headers),
        404,
        "Equipe nao encontrada.",
    )


async def test_teams_requires_auth(client):
    assert_problem(
        await client.get("/api/v1/teams"),
        401,
        "Token de acesso nao informado.",
    )

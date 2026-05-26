def assert_problem(response, status_code, detail):
    assert response.status_code == status_code
    payload = response.json()
    assert payload["status"] == status_code
    assert payload["detail"] == detail
    assert payload["instance"]
    assert response.headers["content-type"].startswith("application/problem+json")
    return payload


def assert_pagination_meta(payload, *, total, page, page_size, has_next, total_pages):
    meta = payload["meta"]
    assert meta["total"] == total
    assert meta["page"] == page
    assert meta["page_size"] == page_size
    assert meta["has_next"] == has_next
    assert meta["total_pages"] == total_pages


def test_login_and_me_returns_authenticated_user(client, seeded_user):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        },
    )

    assert login_response.status_code == 200
    payload = login_response.json()["data"]
    assert payload["user"]["email"] == seeded_user["email"]
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert me_response.status_code == 200
    me_payload = me_response.json()["data"]
    assert me_payload["email"] == seeded_user["email"]


def test_me_companies_and_context_return_single_company_context(client, seeded_user):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        },
    )
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    companies_response = client.get("/api/v1/me/companies", headers=headers)
    assert companies_response.status_code == 200
    companies_payload = companies_response.json()
    assert len(companies_payload["data"]) == 1
    assert companies_payload["data"][0]["id"] == seeded_user["company_id"]
    assert companies_payload["meta"] == {}

    context_response = client.get("/api/v1/me/context", headers=headers)
    assert context_response.status_code == 200
    context_payload = context_response.json()["data"]
    assert context_payload["user"]["email"] == seeded_user["email"]
    assert context_payload["active_company"]["id"] == seeded_user["company_id"]
    assert context_payload["membership"]["role"] == "OWNER"
    assert len(context_payload["available_companies"]) == 1
    assert context_payload["requires_company_selection"] is False


def test_me_context_requires_selection_for_multi_company_user(client, multi_company_user):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": multi_company_user["email"],
            "password": multi_company_user["password"],
        },
    )
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    companies_response = client.get("/api/v1/me/companies", headers=headers)
    assert companies_response.status_code == 200
    companies_payload = companies_response.json()["data"]
    assert len(companies_payload) == 2

    context_response = client.get("/api/v1/me/context", headers=headers)
    assert context_response.status_code == 200
    context_payload = context_response.json()["data"]
    assert context_payload["active_company"] is None
    assert context_payload["membership"] is None
    assert len(context_payload["available_companies"]) == 2
    assert context_payload["requires_company_selection"] is True

    selected_context_response = client.get(
        "/api/v1/me/context",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Company-Id": multi_company_user["company_a_id"],
        },
    )
    assert selected_context_response.status_code == 200
    selected_context_payload = selected_context_response.json()["data"]
    assert selected_context_payload["active_company"]["id"] == multi_company_user["company_a_id"]
    assert selected_context_payload["membership"]["role"] == "OWNER"
    assert selected_context_payload["requires_company_selection"] is False


def test_login_rejects_invalid_password(client, seeded_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": seeded_user["email"],
            "password": "wrong-password",
        },
    )

    assert_problem(response, 401, "Email ou senha invalidos.")


def test_multi_company_user_must_inform_company_header(client, multi_company_user):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": multi_company_user["email"],
            "password": multi_company_user["password"],
        },
    )
    token = login_response.json()["data"]["access_token"]

    response = client.get(
        "/api/v1/forms",
        headers={"Authorization": f"Bearer {token}"},
    )

    payload = assert_problem(
        response,
        400,
        "Informe o header X-Company-Id para selecionar a empresa ativa.",
    )
    assert payload["title"] == "Bad Request"

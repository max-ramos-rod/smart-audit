from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.security import hash_password
from app.db.models import Company, Membership, User
from app.db.session import get_db, engine
from app.main import app


@pytest.fixture()
def disable_rate_limiting():
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture()
def db_connection() -> Generator[Connection, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture()
def db_session(db_connection: Connection) -> Generator[Session, None, None]:
    session = Session(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session, disable_rate_limiting) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def seeded_user(db_session: Session) -> dict[str, str]:
    unique_suffix = uuid4().hex[:8]
    user = User(
        name="Test User",
        email=f"test-{unique_suffix}@smartaudit.local",
        password_hash=hash_password("test123456"),
        is_active=True,
    )
    company = Company(
        name=f"Test Company {unique_suffix}",
        slug=f"test-company-{unique_suffix}",
        plan="starter",
        is_active=True,
    )
    db_session.add_all([user, company])
    db_session.flush()

    membership = Membership(
        company_id=company.id,
        user_id=user.id,
        role="OWNER",
    )
    db_session.add(membership)
    db_session.commit()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "password": "test123456",
        "company_id": str(company.id),
    }


@pytest.fixture()
def inspector_user(db_session: Session) -> dict[str, str]:
    unique_suffix = uuid4().hex[:8]
    user = User(
        name="Inspector User",
        email=f"inspector-{unique_suffix}@smartaudit.local",
        password_hash=hash_password("test123456"),
        is_active=True,
    )
    company = Company(
        name=f"Inspector Company {unique_suffix}",
        slug=f"inspector-company-{unique_suffix}",
        plan="starter",
        is_active=True,
    )
    db_session.add_all([user, company])
    db_session.flush()

    membership = Membership(
        company_id=company.id,
        user_id=user.id,
        role="INSPECTOR",
    )
    db_session.add(membership)
    db_session.commit()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "password": "test123456",
        "company_id": str(company.id),
    }


@pytest.fixture()
def multi_company_user(db_session: Session) -> dict[str, str]:
    unique_suffix = uuid4().hex[:8]
    user = User(
        name="Multi Company User",
        email=f"multi-{unique_suffix}@smartaudit.local",
        password_hash=hash_password("test123456"),
        is_active=True,
    )
    company_a = Company(
        name=f"Company A {unique_suffix}",
        slug=f"company-a-{unique_suffix}",
        plan="starter",
        is_active=True,
    )
    company_b = Company(
        name=f"Company B {unique_suffix}",
        slug=f"company-b-{unique_suffix}",
        plan="starter",
        is_active=True,
    )
    db_session.add_all([user, company_a, company_b])
    db_session.flush()

    db_session.add_all(
        [
            Membership(company_id=company_a.id, user_id=user.id, role="OWNER"),
            Membership(company_id=company_b.id, user_id=user.id, role="OWNER"),
        ]
    )
    db_session.commit()

    return {
        "email": user.email,
        "password": "test123456",
        "company_a_id": str(company_a.id),
        "company_b_id": str(company_b.id),
    }


@pytest.fixture()
def viewer_user(db_session: Session) -> dict[str, str]:
    unique_suffix = uuid4().hex[:8]
    user = User(
        name="Viewer User",
        email=f"viewer-{unique_suffix}@smartaudit.local",
        password_hash=hash_password("test123456"),
        is_active=True,
    )
    company = Company(
        name=f"Viewer Company {unique_suffix}",
        slug=f"viewer-company-{unique_suffix}",
        plan="starter",
        is_active=True,
    )
    db_session.add_all([user, company])
    db_session.flush()

    membership = Membership(
        company_id=company.id,
        user_id=user.id,
        role="VIEWER",
    )
    db_session.add(membership)
    db_session.commit()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "password": "test123456",
        "company_id": str(company.id),
    }


@pytest.fixture()
def viewer_headers(client: TestClient, viewer_user: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": viewer_user["email"],
            "password": viewer_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Company-Id": viewer_user["company_id"],
    }


@pytest.fixture()
def auth_headers(client: TestClient, seeded_user: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Company-Id": seeded_user["company_id"],
    }


@pytest.fixture()
def inspector_headers(client: TestClient, inspector_user: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": inspector_user["email"],
            "password": inspector_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Company-Id": inspector_user["company_id"],
    }

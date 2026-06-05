from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.limiter import limiter
from app.core.security import hash_password
from app.db.models import Company, Membership, User
from app.db.session import engine, get_db
from app.main import app


@pytest.fixture()
def disable_rate_limiting():
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest_asyncio.fixture()
async def db_connection() -> AsyncGenerator[AsyncConnection, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    try:
        yield connection
    finally:
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture()
async def db_session(db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture()
async def client(
    db_session: AsyncSession, disable_rate_limiting
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def seeded_user(db_session: AsyncSession) -> dict[str, str]:
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
    await db_session.flush()

    membership = Membership(
        company_id=company.id,
        user_id=user.id,
        role="OWNER",
    )
    db_session.add(membership)
    await db_session.commit()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "password": "test123456",
        "company_id": str(company.id),
    }


@pytest_asyncio.fixture()
async def inspector_user(db_session: AsyncSession) -> dict[str, str]:
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
    await db_session.flush()

    membership = Membership(
        company_id=company.id,
        user_id=user.id,
        role="INSPECTOR",
    )
    db_session.add(membership)
    await db_session.commit()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "password": "test123456",
        "company_id": str(company.id),
    }


@pytest_asyncio.fixture()
async def multi_company_user(db_session: AsyncSession) -> dict[str, str]:
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
    await db_session.flush()

    db_session.add_all(
        [
            Membership(company_id=company_a.id, user_id=user.id, role="OWNER"),
            Membership(company_id=company_b.id, user_id=user.id, role="OWNER"),
        ]
    )
    await db_session.commit()

    return {
        "email": user.email,
        "password": "test123456",
        "company_a_id": str(company_a.id),
        "company_b_id": str(company_b.id),
    }


@pytest_asyncio.fixture()
async def viewer_user(db_session: AsyncSession) -> dict[str, str]:
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
    await db_session.flush()

    membership = Membership(
        company_id=company.id,
        user_id=user.id,
        role="VIEWER",
    )
    db_session.add(membership)
    await db_session.commit()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "password": "test123456",
        "company_id": str(company.id),
    }


@pytest_asyncio.fixture()
async def viewer_headers(client: AsyncClient, viewer_user: dict[str, str]) -> dict[str, str]:
    response = await client.post(
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


@pytest_asyncio.fixture()
async def auth_headers(client: AsyncClient, seeded_user: dict[str, str]) -> dict[str, str]:
    response = await client.post(
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


@pytest_asyncio.fixture()
async def inspector_headers(
    client: AsyncClient, inspector_user: dict[str, str]
) -> dict[str, str]:
    response = await client.post(
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

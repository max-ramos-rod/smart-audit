from io import BytesIO

from backend.tests.integration.test_auth import assert_problem

_TINY_IMAGE = b"fake-image-bytes"
_11_MB = b"x" * (10 * 1024 * 1024 + 1)


async def test_upload_jpeg_returns_url_and_metadata(client, auth_headers):
    response = await client.post(
        "/api/v1/uploads",
        headers=auth_headers,
        files={"file": ("photo.jpg", BytesIO(_TINY_IMAGE), "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["url"].endswith(".jpg")
    assert data["mime_type"] == "image/jpeg"
    assert data["file_size"] == len(_TINY_IMAGE)


async def test_upload_png_returns_url(client, auth_headers):
    response = await client.post(
        "/api/v1/uploads",
        headers=auth_headers,
        files={"file": ("photo.png", BytesIO(_TINY_IMAGE), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["data"]["url"].endswith(".png")


async def test_upload_webp_returns_url(client, auth_headers):
    response = await client.post(
        "/api/v1/uploads",
        headers=auth_headers,
        files={"file": ("photo.webp", BytesIO(_TINY_IMAGE), "image/webp")},
    )
    assert response.status_code == 200
    assert response.json()["data"]["url"].endswith(".webp")


async def test_upload_rejects_invalid_mime_type(client, auth_headers):
    assert_problem(
        await client.post(
            "/api/v1/uploads",
            headers=auth_headers,
            files={"file": ("doc.txt", BytesIO(b"text"), "text/plain")},
        ),
        400,
        "Tipo de arquivo nao permitido. "
        "Use JPEG, PNG, WebP, MP4, MOV, AVI, MP3, WAV, OGG, M4A ou PDF.",
    )


async def test_upload_rejects_oversized_file(client, auth_headers):
    assert_problem(
        await client.post(
            "/api/v1/uploads",
            headers=auth_headers,
            files={"file": ("big.jpg", BytesIO(_11_MB), "image/jpeg")},
        ),
        400,
        "Arquivo muito grande. Limite de 10 MB para este tipo.",
    )


async def test_upload_requires_auth(client):
    assert_problem(
        await client.post(
            "/api/v1/uploads",
            files={"file": ("photo.jpg", BytesIO(_TINY_IMAGE), "image/jpeg")},
        ),
        401,
        "Token de acesso nao informado.",
    )

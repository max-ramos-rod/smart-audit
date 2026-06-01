import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status

from app.core.config import get_settings
from app.core.responses import success_response
from app.db.models.memberships import Membership
from app.modules.memberships.dependencies import get_current_membership

router = APIRouter(prefix="/uploads", tags=["uploads"])

_ALLOWED_MIME: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/x-msvideo": "avi",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "application/pdf": "pdf",
}

_MAX_BYTES_IMAGE = 10 * 1024 * 1024   # 10 MB
_MAX_BYTES_PDF   = 20 * 1024 * 1024   # 20 MB
_MAX_BYTES_AUDIO = 50 * 1024 * 1024   # 50 MB
_MAX_BYTES_VIDEO = 200 * 1024 * 1024  # 200 MB

_MIME_LIMITS: dict[str, int] = {
    "image/jpeg": _MAX_BYTES_IMAGE,
    "image/png": _MAX_BYTES_IMAGE,
    "image/webp": _MAX_BYTES_IMAGE,
    "video/mp4": _MAX_BYTES_VIDEO,
    "video/quicktime": _MAX_BYTES_VIDEO,
    "video/x-msvideo": _MAX_BYTES_VIDEO,
    "audio/mpeg": _MAX_BYTES_AUDIO,
    "audio/wav": _MAX_BYTES_AUDIO,
    "audio/ogg": _MAX_BYTES_AUDIO,
    "audio/mp4": _MAX_BYTES_AUDIO,
    "application/pdf": _MAX_BYTES_PDF,
}


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    membership: Membership = Depends(get_current_membership),
) -> dict[str, object]:
    settings = get_settings()

    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                "Tipo de arquivo nao permitido. "
                "Use JPEG, PNG, WebP, MP4, MOV, AVI, MP3, WAV, OGG, M4A ou PDF."
            ),
        )

    content = await file.read()
    max_bytes = _MIME_LIMITS[file.content_type]
    if len(content) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo muito grande. Limite de {mb} MB para este tipo.",
        )

    company_id = str(membership.company_id)
    ext = _ALLOWED_MIME[file.content_type]
    filename = f"{uuid.uuid4().hex}.{ext}"

    dest_dir = os.path.join(settings.upload_dir, company_id)
    os.makedirs(dest_dir, exist_ok=True)

    with open(os.path.join(dest_dir, filename), "wb") as fh:
        fh.write(content)

    url = f"{settings.upload_base_url.rstrip('/')}/{company_id}/{filename}"
    return success_response({
        "url": url,
        "mime_type": file.content_type,
        "file_size": len(content),
    })

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
}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    membership: Membership = Depends(get_current_membership),
) -> dict[str, object]:
    settings = get_settings()

    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Tipo de arquivo nao permitido. Use JPEG, PNG ou WebP.",
        )

    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Arquivo muito grande. Limite de 10 MB.",
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

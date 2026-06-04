from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    company_id: str
    actor_id: str
    target_user_id: str | None
    action: str
    meta: dict | None
    created_at: str

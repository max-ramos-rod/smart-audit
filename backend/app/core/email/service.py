"""EmailService: the single entry point modules call.

Modules express *intent* (send a password reset, send an invite) instead of
building MIME messages or touching SMTP — the same way services call named
repository methods instead of raw ORM. Transport and templates stay hidden.
"""

from app.core.email import templates
from app.core.email.sender import EmailSender, get_email_sender


class EmailService:
    def __init__(self, sender: EmailSender | None = None) -> None:
        self._sender = sender or get_email_sender()

    async def send_password_reset(self, to: str, reset_url: str, ttl_hours: int) -> None:
        await self._sender.send(templates.password_reset(to, reset_url, ttl_hours))

    async def send_user_invite(
        self, to: str, invite_url: str, company_name: str, ttl_hours: int
    ) -> None:
        await self._sender.send(templates.user_invite(to, invite_url, company_name, ttl_hours))

"""Email transport layer: provider abstraction + implementations.

The `EmailSender` protocol decouples *what* to send (EmailMessage) from *how*
it is delivered. Swap the transport (SMTP, console, future Resend/SES) without
touching callers. `get_email_sender()` picks the implementation from settings,
mirroring the `get_settings()` lru_cache pattern.
"""

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from typing import Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str | None = None


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class SmtpEmailSender:
    """Production transport. Sends via SMTP with STARTTLS when credentials are set.

    `smtplib` is blocking, so the send runs off the event loop via
    `asyncio.to_thread`. Failures are swallowed and logged — sending email must
    never break the request flow (e.g. the anti-enumeration reset endpoint).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, message: EmailMessage) -> None:
        try:
            await asyncio.to_thread(self._send_sync, message)
        except Exception:
            logger.exception("Falha ao enviar e-mail para %s", message.to)

    def _send_sync(self, message: EmailMessage) -> None:
        s = self._settings
        msg: MIMEText | MIMEMultipart
        if message.html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(message.text_body, "plain", "utf-8"))
            msg.attach(MIMEText(message.html_body, "html", "utf-8"))
        else:
            msg = MIMEText(message.text_body, "plain", "utf-8")
        msg["Subject"] = message.subject
        msg["From"] = s.smtp_from
        msg["To"] = message.to
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
            if s.smtp_user and s.smtp_password:
                smtp.starttls()
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)


class ConsoleEmailSender:
    """Dev fallback (no SMTP_HOST): logs the message instead of sending.

    Logs the plain-text body so links remain visible for local debugging.
    Never use in production — bodies may contain reset/invite tokens.
    """

    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "EMAIL (console) | to=%s | subject=%s\n%s",
            message.to,
            message.subject,
            message.text_body,
        )


@lru_cache
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.smtp_host:
        return SmtpEmailSender(settings)
    return ConsoleEmailSender()

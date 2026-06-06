"""Email templates: subject + plain-text + HTML per message type.

Templates are pure functions that take data and return an EmailMessage. Keep
formatting out of the service/business layer. Each template provides both a
text and an HTML body — the multipart/alternative pair improves deliverability
(many spam filters penalize text-only or HTML-only messages).
"""

from app.core.email.sender import EmailMessage

_BRAND = "Smart Audit"
_BRAND_COLOR = "#2563eb"


def _html_wrap(*, title: str, intro: str, cta_label: str, cta_url: str, note: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<body style="margin:0;padding:24px;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">
        <tr><td style="background:{_BRAND_COLOR};padding:18px 28px;color:#ffffff;font-size:18px;font-weight:700;">
          {_BRAND}
        </td></tr>
        <tr><td style="padding:28px;">
          <h1 style="margin:0 0 12px;font-size:20px;color:#0f172a;">{title}</h1>
          <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#475569;">{intro}</p>
          <a href="{cta_url}"
             style="display:inline-block;background:{_BRAND_COLOR};color:#ffffff;text-decoration:none;
                    padding:12px 24px;border-radius:8px;font-size:14px;font-weight:600;">{cta_label}</a>
          <p style="margin:24px 0 0;font-size:12px;line-height:1.6;color:#94a3b8;">{note}</p>
          <p style="margin:16px 0 0;font-size:12px;line-height:1.6;color:#94a3b8;">
            Se o botão não funcionar, copie e cole este endereço no navegador:<br>
            <span style="color:{_BRAND_COLOR};word-break:break-all;">{cta_url}</span>
          </p>
        </td></tr>
      </table>
      <p style="margin:16px 0 0;font-size:11px;color:#94a3b8;">{_BRAND} · Plataforma Operacional</p>
    </td></tr>
  </table>
</body>
</html>"""


def password_reset(to: str, reset_url: str, ttl_hours: int) -> EmailMessage:
    subject = f"{_BRAND} — redefinição de senha"
    text = (
        f"Você solicitou a redefinição da sua senha no {_BRAND}.\n\n"
        f"Acesse o link abaixo para criar uma nova senha (válido por {ttl_hours}h):\n\n"
        f"{reset_url}\n\n"
        "Se você não fez esta solicitação, ignore este e-mail."
    )
    html = _html_wrap(
        title="Redefinição de senha",
        intro=f"Você solicitou a redefinição da sua senha no {_BRAND}.",
        cta_label="Redefinir senha",
        cta_url=reset_url,
        note=(
            f"O link é válido por {ttl_hours}h e pode ser usado uma única vez. "
            "Se você não fez esta solicitação, ignore este e-mail."
        ),
    )
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)


def user_invite(to: str, invite_url: str, company_name: str, ttl_hours: int) -> EmailMessage:
    subject = f"{_BRAND} — convite para {company_name}"
    text = (
        f"Você foi convidado para acessar {company_name} no {_BRAND}.\n\n"
        f"Acesse o link abaixo para definir sua senha e entrar (válido por {ttl_hours}h):\n\n"
        f"{invite_url}\n\n"
        "Se você não esperava este convite, ignore este e-mail."
    )
    html = _html_wrap(
        title=f"Convite para {company_name}",
        intro=f"Você foi convidado para acessar {company_name} no {_BRAND}.",
        cta_label="Definir senha e entrar",
        cta_url=invite_url,
        note=(
            f"O link é válido por {ttl_hours}h e pode ser usado uma única vez. "
            "Se você não esperava este convite, ignore este e-mail."
        ),
    )
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)

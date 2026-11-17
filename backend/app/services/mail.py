"""Outbound account mail (reference page 32: «تصميم رسائل البريد — نص موجز
ورابط آمن، بلا تفاصيل مالية»).

Two constraints shape this module:

* The message body is brief and carries a single secure link. It never contains
  a financial figure, a report value or any other business data — the link is
  the only thing it conveys.
* When no SMTP transport is configured the caller is told so explicitly. The
  module never reports a delivery that did not happen.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

BRAND_AR = "ستارت أب سفير القابضة"
BRAND_EN = "Start Up Sphere Holding"


@dataclass(frozen=True)
class EmailContent:
    subject: str
    body: str


def _url(path: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}{path}"


def password_reset_email(locale: str, token: str) -> EmailContent:
    link = _url(f"/reset-password?token={token}")
    minutes = settings.password_reset_minutes
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — reset your password",
            body=(
                f"A password reset was requested for your {BRAND_EN} account.\n\n"
                f"Set a new password using this single-use link (valid for {minutes} minutes):\n"
                f"{link}\n\n"
                "If you did not request this, ignore the message; your password is unchanged."
            ),
        )
    return EmailContent(
        subject=f"{BRAND_AR} — إعادة تعيين كلمة المرور",
        body=(
            f"طُلب إعادة تعيين كلمة المرور لحسابك في {BRAND_AR}.\n\n"
            f"عيّن كلمة مرور جديدة من خلال هذا الرابط أحادي الاستخدام (صالح {minutes} دقيقة):\n"
            f"{link}\n\n"
            "إذا لم تطلب ذلك فتجاهل الرسالة، وكلمة مرورك لم تتغير."
        ),
    )


def invitation_email(locale: str, token: str, role_label: str) -> EmailContent:
    link = _url(f"/reset-password?token={token}")
    minutes = settings.password_reset_minutes
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — set up your account",
            body=(
                f"An account was created for you on the {BRAND_EN} platform"
                f"{f' with the role {role_label}' if role_label else ''}.\n\n"
                f"Set your password using this single-use link (valid for {minutes} minutes):\n"
                f"{link}\n\n"
                "For your security no password is ever sent by email."
            ),
        )
    return EmailContent(
        subject=f"{BRAND_AR} — إعداد حسابك",
        body=(
            f"أُنشئ لك حساب على منصة {BRAND_AR}.\n\n"
            f"عيّن كلمة المرور من خلال هذا الرابط أحادي الاستخدام (صالح {minutes} دقيقة):\n"
            f"{link}\n\n"
            "لأمانك لا تُرسل كلمة المرور في البريد أبدًا."
        ),
    )


def send(to_email: str, content: EmailContent) -> bool:
    """Send a message.

    Returns ``False`` when no transport is configured or the delivery fails, so
    the caller can tell the user the link must be delivered out-of-band rather
    than claiming a message that was never sent.
    """
    if not settings.mail_configured:
        return False
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = content.subject
    message.set_content(content.body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        # The account change already committed; a mail outage must not surface
        # as a 500. The caller reports that the link was not delivered.
        logger.warning("Mail delivery to %s failed: %s", to_email, exc)
        return False
    return True

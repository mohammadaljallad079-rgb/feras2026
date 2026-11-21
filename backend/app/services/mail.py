"""Outbound mail.

Two kinds of message live here, and the brief constrains each differently:

* **Account mail** (reference page 32: «تصميم رسائل البريد — نص موجز ورابط آمن،
  بلا تفاصيل مالية»). The body is brief and carries a single secure link, and it
  never contains a financial figure, a report value or any other business data.
* **Business notifications** — the messages the Word specification names for
  workflow events: «ويصله بريد» when a service request is routed to a specialist
  (Table 5), «نسخة بريد لمدير الشركة والمختص» when a public request is converted
  (Table 6), «مهمة في لوحة مطوّر الأعمال وبريد» for an assistant referral
  (Table 5/10), and the §7.5 deadline reminder. These carry a short subject and
  the minimum detail needed to act; they still never carry an amount or a report
  value.

One constraint is common: when no SMTP transport is configured the caller is
told so explicitly. The module never reports a delivery that did not happen.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Iterable
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


def notify(recipients: Iterable[str | None], content: EmailContent) -> int:
    """Send one message to each distinct, non-empty address.

    A workflow event may address several people (the Word specification asks for
    «نسخة بريد لمدير الشركة والمختص»). Each delivery is independent, and the
    return value is how many actually went out — so a caller never reports a
    notification that the transport did not send.
    """
    sent = 0
    seen: set[str] = set()
    for email in recipients:
        if not email or email in seen:
            continue
        seen.add(email)
        if send(email, content):
            sent += 1
    return sent


# --- Business notification templates ---------------------------------------
# These carry a short subject and only the detail needed to act. Like the
# account mail they never carry an amount, a currency or a report value.


def service_request_routed_email(
    locale: str, *, subject: str, company: str, service_type: str
) -> EmailContent:
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — a service request was routed to you",
            body=(
                f"A service request was addressed to you.\n\n"
                f"Subject: {subject}\nCompany: {company}\nService type: {service_type}\n\n"
                "Open the platform's Service requests screen to reply or update the status."
            ),
        )
    return EmailContent(
        subject=f"{BRAND_AR} — طلب خدمة موجَّه إليك",
        body=(
            f"وُجّه إليك طلب خدمة.\n\n"
            f"الموضوع: {subject}\nالشركة: {company}\nنوع الخدمة: {service_type}\n\n"
            "افتح شاشة «طلبات الخدمات» في المنصة للرد أو تحديث الحالة."
        ),
    )


def complaint_email(locale: str, *, body: str, company: str) -> EmailContent:
    """Table 5: the marketer's «إرسال شكوى للمالك» — addressed to the owner only,
    with no copy to anyone else."""
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — a complaint was sent to you",
            body=f"A complaint was sent to you from {company}.\n\n{body}\n\nOpen the platform's Service requests screen.",
        )
    return EmailContent(
        subject=f"{BRAND_AR} — شكوى واردة إليك",
        body=f"وصلتك شكوى من {company}.\n\n{body}\n\nافتح شاشة «طلبات الخدمات» في المنصة.",
    )


def directive_email(locale: str, *, title: str, body: str) -> EmailContent:
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — a new executive directive",
            body=f"A new directive was addressed to you.\n\n{title}\n\n{body}\n\nOpen the Directives screen to confirm receipt.",
        )
    return EmailContent(
        subject=f"{BRAND_AR} — توجيه تنفيذي جديد",
        body=f"وُجّه إليك توجيه جديد.\n\n{title}\n\n{body}\n\nافتح شاشة «التوجيهات» لتأكيد الاستلام.",
    )


def conversion_copy_email(
    locale: str, *, item: str, target_ar: str, target_en: str
) -> EmailContent:
    """Table 6: the copy mailed to the receiving company's manager and, for a
    routed service request, the specialist."""
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — a website request became a {target_en}",
            body=(
                f"A website submission was reviewed and recorded as a {target_en}.\n\n"
                f"Item: {item}\n\nOpen the platform to follow it up."
            ),
        )
    return EmailContent(
        subject=f"{BRAND_AR} — طلب من الموقع تحوّل إلى {target_ar}",
        body=(
            f"روعي طلب وارد من الموقع العام وسُجّل بصفته {target_ar}.\n\n"
            f"البند: {item}\n\nافتح المنصة لمتابعته."
        ),
    )


def assistant_task_email(locale: str, *, title: str) -> EmailContent:
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — a task from the smart assistant",
            body=f"The owner asked the assistant to assign you a task.\n\n{title}\n\nIt appears in your dashboard's «Assistant tasks» card. The assistant does not execute the plan.",
        )
    return EmailContent(
        subject=f"{BRAND_AR} — مهمة من المساعد الذكي",
        body=f"طلب المالك من المساعد إحالتها إليك.\n\n{title}\n\nتظهر في بطاقة «مهام من المساعد» في لوحتك. المساعد لا ينفّذ الخطة.",
    )


def report_deadline_email(
    locale: str, *, company: str, period: str, days_left: int
) -> EmailContent:
    """§7.5: the reminder that reaches the manager three days before the due
    date, on the due date, and daily once the period is late."""
    if days_left > 0:
        when_ar, when_en = f"يستحق بعد {days_left} أيام", f"due in {days_left} day(s)"
    elif days_left == 0:
        when_ar, when_en = "يستحق اليوم", "due today"
    else:
        when_ar, when_en = f"متأخر {abs(days_left)} أيام", f"{abs(days_left)} day(s) late"
    if locale == "en":
        return EmailContent(
            subject=f"{BRAND_EN} — monthly report {period} reminder",
            body=(
                f"The monthly report for {period} — {company} is {when_en}.\n\n"
                "Open the platform's Monthly reports screen to fill it in and send it to the accountant."
            ),
        )
    return EmailContent(
        subject=f"{BRAND_AR} — تذكير بتقرير {period}",
        body=(
            f"التقرير الشهري للفترة {period} — {company} {when_ar}.\n\n"
            "افتح شاشة «التقارير الشهرية» في المنصة لتعبئته وإرساله إلى المحاسب."
        ),
    )

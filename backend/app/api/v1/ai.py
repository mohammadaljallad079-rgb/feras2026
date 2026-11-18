"""Assistant endpoints.

Answers are grounded only in permission-filtered records, with sources and a
confidence level, or they return an explicit configuration status. A missing
provider key never produces a fabricated answer. The provider settings screen
(PDF page 17) exposes a masked key, a connection test and a model class, and is
restricted to the owner.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import GroundedContext, SYSTEM_PROMPT, get_provider
from app.ai.retrieval import gather_context
from app.api.deps import allowed_company_ids, require
from app.core.config import settings
from app.core.db import get_db
from app.models.business import Company, MonthlyReport, ReportingPeriod
from app.models.enums import CompanyStatus, ReportStatus, RequestStatus
from app.models.identity import User
from app.models.operations import (
    AccountingEntry,
    AdvisorMessage,
    AiProviderSetting,
    AiQuery,
    ExecutiveDirective,
    Lead,
    ServiceRequest,
    WebsiteSubmission,
)
from app.schemas import (
    AiAnswer,
    AiAskRequest,
    AiProviderSettingsIn,
    AiProviderSettingsOut,
    AiReferRequest,
    AiSettingsTestResult,
    AiSource,
    AiSummaryNote,
    AiSummaryOut,
    AiSummarySection,
)
from app.services import ai_settings, audit, mail

router = APIRouter(prefix="/ai", tags=["ai"])

# Statuses that mean "not closed for the period" in the reporting state machine.
_NOT_CLOSED = (ReportStatus.DRAFT, ReportStatus.SUBMITTED, ReportStatus.RETURNED)


@router.get("/status")
def status(actor: User = Depends(require("ai:use")), db: Session = Depends(get_db)) -> dict:
    """A missing key yields a clear configuration status, not a fake success."""
    row = ai_settings.get_or_create(db)
    provider, model, _, key = ai_settings.effective(row)
    configured = bool(key)
    return {
        "provider": provider,
        "model": model,
        "configured": configured,
        "message_ar": (
            "المساعد مهيأ."
            if configured
            else "المساعد غير مهيأ: مفتاح مزوّد الذكاء الاصطناعي غير مُعد."
        ),
    }


@router.post("/ask", response_model=AiAnswer)
def ask(
    payload: AiAskRequest,
    actor: User = Depends(require("ai:use")),
    db: Session = Depends(get_db),
) -> AiAnswer:
    row = ai_settings.get_or_create(db)
    provider_name, model, base_url, api_key = ai_settings.effective(row)
    configured = bool(api_key)

    ctx: GroundedContext = gather_context(db, actor, company_id=payload.company_id, period_id=payload.period_id)

    note = None
    if configured and ctx.has_data:
        try:
            answer, confidence, note = _answer_with_prompt(ctx, payload.prompt, provider_name, model, base_url, api_key)
        except Exception as exc:  # provider failure must be visible, never faked
            db.rollback()
            raise HTTPException(status_code=502, detail={"error": "ai_provider_failed", "detail": str(exc)})
    else:
        answer, confidence, note = _deterministic_answer(ctx, configured)

    record = AiQuery(
        user_id=actor.id,
        prompt=payload.prompt,
        answer=answer,
        provider=provider_name,
        model=model,
        confidence=confidence,
        sources=json.dumps(ctx.sources, ensure_ascii=False),
        company_id=payload.company_id,
        period_id=payload.period_id,
    )
    db.add(record)
    audit.record(db, action="ai.ask", actor=actor, target_type="ai_query", target_id=record.id, company_id=payload.company_id)
    db.commit()

    return AiAnswer(
        answer=answer,
        confidence=confidence,
        sources=[AiSource(**s) for s in ctx.sources],
        provider=provider_name,
        model=model,
        configured=configured,
        note=note,
    )


# --- Owner summary (PDF page 17: executive summary with source and period) ---

@router.get("/summary", response_model=AiSummaryOut)
def summary(
    period_id: int | None = None,
    actor: User = Depends(require("ai:use")),
    db: Session = Depends(get_db),
) -> AiSummaryOut:
    """Deterministic executive summary.

    Every line is derived from permitted records only; no figure is produced by
    a language model, so nothing here can be fabricated.
    """
    allowed = allowed_company_ids(db, actor)

    company_stmt = select(Company).where(Company.status == CompanyStatus.ACTIVE)
    if allowed is not None:
        company_stmt = company_stmt.where(Company.id.in_(allowed or {-1}))
    active_companies = db.execute(company_stmt.order_by(Company.id)).scalars().all()
    # §7.1: a period is opened for every active subsidiary and for the Holding
    # itself, so the Holding is included in the "no report yet" check but not in
    # the subsidiary count the scope line states.
    active_subsidiaries = [c for c in active_companies if not c.is_holding]

    period = db.get(ReportingPeriod, period_id) if period_id else db.execute(
        select(ReportingPeriod).order_by(ReportingPeriod.id.desc())
    ).scalars().first()

    report_stmt = select(MonthlyReport)
    if period is not None:
        report_stmt = report_stmt.where(MonthlyReport.period_id == period.id)
    if allowed is not None:
        report_stmt = report_stmt.where(MonthlyReport.company_id.in_(allowed or {-1}))
    reports = db.execute(report_stmt).scalars().all()

    approved = [r for r in reports if r.status == ReportStatus.APPROVED]
    forwarded = [r for r in reports if r.status == ReportStatus.FORWARDED]
    # "Late" is a report that is not yet approved or forwarded for the period,
    # plus any active company that has submitted nothing for it at all.
    late = [r for r in reports if r.status in _NOT_CLOSED]
    reporting_company_ids = {r.company_id for r in reports}
    late_missing = [c for c in active_companies if c.id not in reporting_company_ids]
    late_count = len(late) + len(late_missing)

    def count(model, *conditions) -> int:
        stmt = select(func.count(model.id))
        if allowed is not None and hasattr(model, "company_id"):
            stmt = stmt.where(model.company_id.in_(allowed or {-1}))
        for c in conditions:
            stmt = stmt.where(c)
        return db.execute(stmt).scalar_one()

    scope_ar = (
        f"الفترة: {period.label_ar} — الشركات النشطة: {len(active_subsidiaries)} — "
        f"التقارير المعتمدة: {len(approved)} — المتأخرة: {late_count} — "
        "كل مبلغ بعملة شركته."
    )
    scope_en = (
        f"Period: {period.label_en} — active companies: {len(active_subsidiaries)} — "
        f"approved reports: {len(approved)} — late: {late_count} — "
        "every amount in its own company currency."
    )

    source_rows = [
        {
            "label_ar": f"تقرير {r.company.name_ar}",
            "label_en": f"{r.company.name_en} report",
            "kind": "report",
            "url": f"/reports/{r.id}",
            "status": r.status,
            "currency": r.currency,
        }
        for r in (forwarded or approved)[:10]
    ]

    open_requests = count(ServiceRequest, ServiceRequest.status != RequestStatus.COMPLETED.value)
    alerts_ar: list[str] = []
    if late_count:
        alerts_ar.append(f"التقارير المتأخرة أو غير المُسلَّمة للفترة الحالية: {late_count}.")
    if open_requests:
        alerts_ar.append(f"طلبات الخدمة المفتوحة: {open_requests}.")

    # §5.1/§7.5: an alert about an unsent report carries «فتح السجل» — the record
    # itself — so the owner can open it instead of reading a dead-end warning.
    # Only a period whose due date has passed counts as «بعد موعده».
    notes: list[AiSummaryNote] = []
    period_label = period.label_ar if period else ""
    period_label_en = period.label_en if period else ""
    past_due = bool(period and period.due_on and period.due_on < date.today())
    if past_due:
        for r in late:
            notes.append(
                AiSummaryNote(
                    text_ar=f"لم يُرسل تقرير {period_label} بعد موعده — {r.company.name_ar}",
                    text_en=f"The {period_label_en} report is past its due date — {r.company.name_en}",
                    url=f"/reports/{r.id}",
                )
            )
        for c in late_missing:
            notes.append(
                AiSummaryNote(
                    text_ar=f"لم يُرسل تقرير {period_label} بعد موعده — {c.name_ar}",
                    text_en=f"The {period_label_en} report is past its due date — {c.name_en}",
                    url="/reports",
                )
            )

    sections = [
        AiSummarySection(
            key="situation",
            title_ar="ملخص الوضع",
            title_en="Situation summary",
            lines_ar=[
                f"الفترة الحالية {period.label_ar}، والاستحقاق {period.due_on.isoformat() if period.due_on else '—'}.",
                f"الشركات النشطة {len(active_subsidiaries)}، منها {len(reporting_company_ids)} سلّمت تقريرًا لهذه الفترة.",
                f"تقارير معتمدة {len(approved)}، وتقارير مُرسلة للإدارة {len(forwarded)}، والمتأخرة {late_count}.",
                f"قيود محاسبية: {count(AccountingEntry)} — عملاء محتملون: {count(Lead)} — "
                f"توجيهات: {count(ExecutiveDirective)} — طلبات موقع: {count(WebsiteSubmission)} — "
                f"رسائل المستشار: {count(AdvisorMessage)}.",
            ],
            lines_en=[
                f"Current period {period.label_en}, due {period.due_on.isoformat() if period.due_on else '—'}.",
                f"Active companies: {len(active_subsidiaries)}; {len(reporting_company_ids)} have submitted a report for this period.",
                f"Approved reports: {len(approved)}; sent to management: {len(forwarded)}; late: {late_count}.",
                f"Accounting entries: {count(AccountingEntry)} — leads: {count(Lead)} — "
                f"directives: {count(ExecutiveDirective)} — website submissions: {count(WebsiteSubmission)} — "
                f"advisor messages: {count(AdvisorMessage)}.",
            ],
        ),
        AiSummarySection(
            key="analysis_source",
            title_ar="مصدر التحليل",
            title_en="Source of analysis",
            lines_ar=[
                "التقارير الشهرية المعتمدة والمُرسلة للإدارة لهذه الفترة.",
                "طلبات الخدمات والعملاء المحتملون والفرص والتوجيهات المسجلة.",
                "لا يُنتج أي رقم من نموذج لغوي؛ كل سطر مشتق من السجلات المصرّح بها.",
            ],
            lines_en=[
                "Monthly reports approved and sent to management for this period.",
                "Recorded service requests, leads, opportunities and directives.",
                "No figure comes from a language model; every line is derived from permitted records.",
            ],
        ),
        AiSummarySection(
            key="alerts",
            title_ar="تنبيهات وملاحظات",
            title_en="Alerts and notes",
            lines_ar=alerts_ar,
            lines_en=(
                ([f"Reports late or not yet submitted for the current period: {late_count}."] if late_count else [])
                + ([f"Open service requests: {open_requests}."] if open_requests else [])
            ),
        ),
        AiSummarySection(
            key="next_month",
            title_ar="نصيحة الشهر القادم",
            title_en="Next month advice",
            lines_ar=[
                f"راجع العقود النشطة والعملاء المتكررين لدى {c.name_ar} وحدّد فرصة واحدة."
                for c in active_companies
            ],
            lines_en=[
                f"Review active contracts and repeat clients at {c.name_en} and pick one opportunity."
                for c in active_companies
            ],
        ),
    ]

    # §5.1: the owner's summary is «ملخص المالك الذكي»; a manager sees «ملخص
    # شركتك» scoped to their own company only.
    is_owner = allowed is None
    return AiSummaryOut(
        title_ar="ملخص المالك الذكي" if is_owner else "ملخص شركتك",
        title_en="Owner smart summary" if is_owner else "Your company summary",
        period_label_ar=period.label_ar if period else "—",
        period_label_en=period.label_en if period else "—",
        scope_ar=scope_ar,
        scope_en=scope_en,
        sections=sections,
        sources=source_rows,
        notes=notes,
    )


# --- Referral to the business developer (Table 5) ---
@router.post("/refer")
def refer_to_business_developer(
    payload: AiReferRequest,
    actor: User = Depends(require("ai:use")),
    db: Session = Depends(get_db),
) -> dict:
    """Table 5: «نعم، أحلها لمطوّر الأعمال» — the assistant does not execute the
    plan. It creates a task for the business developer and records the action."""
    from app.models.enums import DirectiveStatus
    from app.models.identity import Role, UserRole
    from app.models.operations import ExecutiveDirective

    bd = db.execute(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.slug == "business_developer", User.is_active.is_(True))
        .order_by(User.id)
    ).scalars().first()
    if bd is None:
        raise HTTPException(status_code=409, detail="No business developer account exists")
    directive = ExecutiveDirective(
        title=payload.title or "مهمة من المساعد الذكي",
        body=payload.body or "خطة عمل مقترحة من ملخص المالك الذكي.",
        created_by_id=actor.id,
        recipient_id=bd.id,
        status=DirectiveStatus.SENT.value,
        sent_at=datetime.now(timezone.utc),
        is_assistant_task=True,
    )
    db.add(directive)
    db.flush()
    audit.record(db, action="ai.refer", actor=actor, target_type="directive", target_id=directive.id)
    db.commit()
    # Table 5/10: «يصله بريد وتظهر مهمة له في لوحته».
    mail.notify([bd.email], mail.assistant_task_email(bd.locale or "ar", title=directive.title))
    return {"ok": True, "directive_id": directive.id, "assignee_id": bd.id}


# --- Owner-only provider settings (PDF page 17) ---

@router.get("/settings", response_model=AiProviderSettingsOut)
def get_settings(
    actor: User = Depends(require("ai:configure")), db: Session = Depends(get_db)
) -> AiProviderSettingsOut:
    row = ai_settings.get_or_create(db)
    provider, model, base_url, key = ai_settings.effective(row)
    audit.record(db, action="ai.settings.view", actor=actor, target_type="ai_provider_setting", target_id=row.id)
    db.commit()
    return AiProviderSettingsOut(
        provider=provider,
        model=model,
        base_url=base_url,
        has_api_key=bool(key),
        api_key_hint=ai_settings.mask(key),
        configured=bool(key),
        model_classes=settings.ai_model_class_list,
        env_key_locked=bool(settings.openai_api_key),
    )


@router.put("/settings", response_model=AiProviderSettingsOut)
def put_settings(
    payload: AiProviderSettingsIn,
    actor: User = Depends(require("ai:configure")),
    db: Session = Depends(get_db),
) -> AiProviderSettingsOut:
    row = ai_settings.get_or_create(db)
    if payload.provider and payload.provider != "openai":
        raise HTTPException(status_code=422, detail={"error": "unsupported_provider"})
    if payload.provider:
        row.provider = payload.provider
    if payload.model:
        row.model = payload.model
    if payload.base_url:
        row.base_url = payload.base_url
    # An empty api_key means "leave unchanged"; the key is never echoed back.
    if payload.api_key:
        row.api_key_encrypted = payload.api_key
    if payload.clear_api_key:
        row.api_key_encrypted = None
    row.updated_by_id = actor.id
    audit.record(db, action="ai.settings.update", actor=actor, target_type="ai_provider_setting", target_id=row.id)
    db.commit()
    provider, model, base_url, key = ai_settings.effective(row)
    return AiProviderSettingsOut(
        provider=provider,
        model=model,
        base_url=base_url,
        has_api_key=bool(key),
        api_key_hint=ai_settings.mask(key),
        configured=bool(key),
        model_classes=settings.ai_model_class_list,
        env_key_locked=bool(settings.openai_api_key),
    )


@router.post("/settings/test", response_model=AiSettingsTestResult)
def test_settings(
    actor: User = Depends(require("ai:configure")), db: Session = Depends(get_db)
) -> AiSettingsTestResult:
    """A real round-trip to the configured provider.

    A failure is reported as a failure. There is no code path that reports a
    successful connection when no request succeeded.
    """
    row = ai_settings.get_or_create(db)
    provider_name, model, base_url, api_key = ai_settings.effective(row)
    if not api_key:
        return AiSettingsTestResult(
            ok=False,
            provider=provider_name,
            model=model,
            message_ar="لا يوجد مفتاح مُعد، لذلك لم يُجرَ أي اتصال.",
            message_en="No API key is configured, so no connection was attempted.",
        )
    try:
        provider = get_provider(provider_name, model=model, base_url=base_url, api_key=api_key)
        reply = provider.complete("Reply with the single word OK.", "ping")
    except httpx.HTTPStatusError as exc:
        return AiSettingsTestResult(
            ok=False,
            provider=provider_name,
            model=model,
            message_ar=f"رفض المزوّد الطلب (رمز {exc.response.status_code}).",
            message_en=f"The provider rejected the request (HTTP {exc.response.status_code}).",
        )
    except Exception as exc:
        return AiSettingsTestResult(
            ok=False,
            provider=provider_name,
            model=model,
            message_ar="تعذّر الاتصال بالمزوّد.",
            message_en=f"The provider could not be reached: {exc}",
        )
    return AiSettingsTestResult(
        ok=True,
        provider=provider_name,
        model=model,
        message_ar="تم الاتصال بالمزوّد بنجاح.",
        message_en=f"Provider reachable: {reply.strip()[:40]}",
    )


def _deterministic_answer(ctx: GroundedContext, configured: bool) -> tuple[str, str, str | None]:
    if not configured:
        return (
            "المساعد غير مهيأ: مفتاح مزوّد الذكاء الاصطناعي غير مُعد على الخادم.",
            "unconfigured",
            "ai_provider_not_configured",
        )
    if not ctx.has_data:
        return (
            "لا توجد سجلات مصرّح بها لديّ للإجابة على هذا السؤال. لم يتم اختلاق أي بيانات.",
            "no_data",
            "no_permitted_sources",
        )
    return ("تم إعداد المزوّد.", "low", "provider_configured")


def _answer_with_prompt(
    ctx: GroundedContext, prompt: str, provider_name: str, model: str, base_url: str, api_key: str
) -> tuple[str, str, str | None]:
    facts = "\n".join(f"- {f}" for f in ctx.facts)
    provider = get_provider(provider_name, model=model, base_url=base_url, api_key=api_key)
    answer = provider.complete(SYSTEM_PROMPT, f"FACTS:\n{facts}\n\nQUESTION: {prompt}")
    confidence = "grounded" if len(ctx.facts) >= 2 else "low"
    return answer, confidence, None

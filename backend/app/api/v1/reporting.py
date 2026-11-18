"""Monthly reporting workflow: a strict, audited, transactional state machine.

draft -> submitted -> (returned -> submitted)* -> approved -> forwarded
Approved/forwarded reports are locked: no field writes are accepted.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, holding_company_id, require, require_any
from app.core.db import get_db
from app.models.business import (
    Company,
    FormField,
    MonthlyReport,
    ReportingPeriod,
    ReportEvent,
    ReportValue,
)
from app.models.enums import ReportStatus
from app.models.operations import StoredFile
from app.models.identity import User
from app.schemas import (
    PeriodCreate,
    PeriodOut,
    ReportCreate,
    ReportEventOut,
    ReportOut,
    ReportReturn,
    ReportValuesUpdate,
)
from app.services import audit

router = APIRouter(tags=["reporting"])

LOCKED = {ReportStatus.APPROVED.value, ReportStatus.FORWARDED.value}


# --- Periods ----------------------------------------------------------------
@router.get("/periods", response_model=list[PeriodOut])
def list_periods(
    _: User = Depends(require_any("report:view_own", "report:view_all")),
    db: Session = Depends(get_db),
) -> list[PeriodOut]:
    rows = db.execute(select(ReportingPeriod).order_by(ReportingPeriod.year.desc(), ReportingPeriod.month.desc())).scalars().all()
    return [PeriodOut.model_validate(p) for p in rows]


@router.post("/periods", response_model=PeriodOut, status_code=status.HTTP_201_CREATED)
def open_period(
    payload: PeriodCreate,
    actor: User = Depends(require("report:period_manage")),
    db: Session = Depends(get_db),
) -> PeriodOut:
    if db.execute(
        select(ReportingPeriod).where(
            ReportingPeriod.year == payload.year, ReportingPeriod.month == payload.month
        )
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Period already exists")
    period = ReportingPeriod(**payload.model_dump())
    db.add(period)
    db.flush()
    audit.record(db, action="period.open", actor=actor, target_type="period", target_id=period.id)
    db.commit()
    db.refresh(period)
    return PeriodOut.model_validate(period)


# --- Reports ----------------------------------------------------------------
def _load(db: Session, report_id: int) -> MonthlyReport:
    report = db.get(MonthlyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _is_holding_author(db: Session, user: User, report: MonthlyReport) -> bool:
    """§7.1: the business developer fills the Holding's own report.

    A holder of ``report:view_all`` without ``report:review`` — the owner and the
    business developer — normally reads only the reports that were formally sent
    to management. The Holding's report is the exception for the developer, who
    authors it: it must open in its draft and returned states so it can be filled
    and sent. A subsidiary draft is never reached this way.
    """
    if "report:submit" not in _perms(user):
        return False
    holding_id = holding_company_id(db)
    return holding_id is not None and report.company_id == holding_id


def _load_visible(db: Session, report_id: int, user: User) -> MonthlyReport:
    """Load a report the caller is entitled to read, or 404.

    §5.1 / §7.1: the owner and the business developer see a report only once the
    accountant has sent it to management («بعد الاعتماد يرسل المحاسب للإدارة.
    عندها فقط يراه المالك ومطوّر الأعمال»), i.e. the ``forwarded`` state. The
    list endpoint already hides the other states from them; this keeps the detail
    and history routes consistent with it instead of exposing those states by id.
    The Holding's report is the exception for its author (§7.1).
    """
    report = _load(db, report_id)
    perms = _perms(user)
    if "report:view_all" in perms and "report:review" not in perms:
        if report.status != ReportStatus.FORWARDED.value and not _is_holding_author(db, user, report):
            raise HTTPException(status_code=404, detail="Report not found")
    return report


def _applies(field: FormField, company: Company | None) -> bool:
    """A field applies when its company/sector scope matches, or is unset."""
    if field.company_id is not None and (company is None or field.company_id != company.id):
        return False
    if field.sector_scope and (company is None or field.sector_scope != company.sector):
        return False
    return True


def _assert_report_company_access(db: Session, user: User, report: MonthlyReport) -> None:
    """Company isolation for a report read or review, mirroring ``list_reports``.

    A holder of ``report:view_all`` — the owner, the accountant, the business
    developer — reaches every company's reports (the accountant is the holding's
    reviewer and the owner/developer read what was sent to management), so the
    list, the detail and the export must agree. A manager holding only
    ``report:view_own`` stays inside the companies granted to them.
    """
    _assert_report_scope(db, user, report.company_id)


def _assert_report_scope(db: Session, user: User, company_id: int) -> None:
    if "report:view_all" in _perms(user):
        return
    assert_company_access(db, user, company_id)


def _is_empty(value: ReportValue) -> bool:
    if value.value_number is not None:
        return False
    return not (value.value_text or "").strip()


def _transition(db: Session, report: MonthlyReport, to_status: str, actor: User, reason: str | None = None) -> None:
    db.add(
        ReportEvent(
            report_id=report.id,
            from_status=report.status,
            to_status=to_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    report.status = to_status


@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    company_id: int | None = None,
    period_id: int | None = None,
    report_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_any("report:view_own", "report:view_all")),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    stmt = select(MonthlyReport)
    # A manager sees only their own company's reports; reviewers/owners see all
    # (still subject to company isolation for non-owners).
    perms = _perms(user)
    if "report:view_all" not in perms:
        allowed = allowed_company_ids(db, user)
        if allowed is not None:
            stmt = stmt.where(MonthlyReport.company_id.in_(allowed or {-1}))
    elif "report:review" not in perms:
        # §5.1 / §7.1: the owner and the business developer see only the reports
        # the accountant has sent to management («عندها فقط يراه المالك ومطوّر
        # الأعمال»), i.e. the forwarded state — not drafts and not merely approved
        # ones (Table 8 marks «معتمد» as the accountant's). The Holding's report is
        # the exception for its author (§7.1): the developer sees its own Holding
        # report in every state so it can be filled and sent.
        holding_id = holding_company_id(db)
        if holding_id is not None and "report:submit" in perms:
            stmt = stmt.where(
                or_(
                    MonthlyReport.status == ReportStatus.FORWARDED.value,
                    and_(
                        MonthlyReport.company_id == holding_id,
                        MonthlyReport.status != ReportStatus.FORWARDED.value,
                    ),
                )
            )
        else:
            stmt = stmt.where(MonthlyReport.status == ReportStatus.FORWARDED.value)
    if company_id is not None:
        _assert_report_scope(db, user, company_id)
        stmt = stmt.where(MonthlyReport.company_id == company_id)
    if period_id is not None:
        stmt = stmt.where(MonthlyReport.period_id == period_id)
    if report_status is not None:
        stmt = stmt.where(MonthlyReport.status == report_status)
    rows = db.execute(stmt.order_by(MonthlyReport.id.desc())).scalars().all()
    return [ReportOut.model_validate(r) for r in rows]


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    actor: User = Depends(require("report:submit")),
    db: Session = Depends(get_db),
) -> ReportOut:
    assert_company_access(db, actor, payload.company_id)
    company = db.get(Company, payload.company_id)
    period = db.get(ReportingPeriod, payload.period_id)
    if company is None or period is None:
        raise HTTPException(status_code=404, detail="Company or period not found")
    if period.status != "open":
        raise HTTPException(status_code=409, detail="Reporting period is closed")
    if db.execute(
        select(MonthlyReport).where(
            MonthlyReport.company_id == payload.company_id, MonthlyReport.period_id == payload.period_id
        )
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Report already exists for this period")
    report = MonthlyReport(
        company_id=payload.company_id,
        period_id=payload.period_id,
        commentary=payload.commentary,
        currency=company.currency,
    )
    db.add(report)
    db.flush()
    audit.record(db, action="report.create", actor=actor, target_type="report", target_id=report.id, company_id=company.id)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    user: User = Depends(require_any("report:view_own", "report:view_all")),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = _load_visible(db, report_id, user)
    _assert_report_company_access(db, user, report)
    return ReportOut.model_validate(report)


@router.get("/reports/{report_id}/history", response_model=list[ReportEventOut])
def report_history(
    report_id: int,
    user: User = Depends(require_any("report:view_own", "report:view_all")),
    db: Session = Depends(get_db),
) -> list[ReportEventOut]:
    report = _load_visible(db, report_id, user)
    _assert_report_company_access(db, user, report)
    rows = db.execute(
        select(ReportEvent).where(ReportEvent.report_id == report_id).order_by(ReportEvent.id)
    ).scalars().all()
    return [ReportEventOut.model_validate(r) for r in rows]


@router.put("/reports/{report_id}/values", response_model=ReportOut)
def save_values(
    report_id: int,
    payload: ReportValuesUpdate,
    actor: User = Depends(require("report:submit")),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = _load(db, report_id)
    assert_company_access(db, actor, report.company_id)
    if report.status in LOCKED:
        raise HTTPException(status_code=409, detail="Approved or forwarded reports are locked")
    if report.status == ReportStatus.SUBMITTED.value:
        raise HTTPException(status_code=409, detail="Submitted reports cannot be edited before review")

    fields = {
        f.id: f
        for f in db.execute(
            select(FormField).where(FormField.id.in_([v.field_id for v in payload.values] or [-1]))
        ).scalars().all()
    }
    if len(fields) != len({v.field_id for v in payload.values}):
        raise HTTPException(status_code=422, detail="Unknown form field")

    existing = {v.field_id: v for v in report.values}
    for item in payload.values:
        field = fields[item.field_id]
        value = existing.get(item.field_id)
        if value is None:
            value = ReportValue(report_id=report.id, field_id=field.id)
            db.add(value)
        # Snapshot the definition version so a later schema change cannot rewrite history.
        value.field_version = field.version
        if field.field_type in {"number", "amount"}:
            value.value_number = item.value_number
            value.value_text = None
        else:
            value.value_text = item.value_text
            value.value_number = None

    if payload.commentary is not None:
        report.commentary = payload.commentary
    if payload.bank_statement_file_id is not None:
        # The manager must be able to attach the statement their company owns.
        if db.get(StoredFile, payload.bank_statement_file_id) is None:
            raise HTTPException(status_code=422, detail="Unknown bank statement file")
        report.bank_statement_file_id = payload.bank_statement_file_id
    audit.record(db, action="report.save_values", actor=actor, target_type="report", target_id=report.id, company_id=report.company_id)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.post("/reports/{report_id}/submit", response_model=ReportOut)
def submit_report(
    report_id: int,
    actor: User = Depends(require("report:submit")),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = _load(db, report_id)
    assert_company_access(db, actor, report.company_id)
    if report.status not in {ReportStatus.DRAFT.value, ReportStatus.RETURNED.value}:
        raise HTTPException(status_code=409, detail="Only draft or returned reports can be submitted")

    # Required-field validation against the active form definitions that apply
    # to this report's company/sector.
    report_company = db.get(Company, report.company_id)
    required = db.execute(
        select(FormField).where(
            FormField.is_active.is_(True),
            FormField.is_required.is_(True),
            FormField.parent_id.is_(None),
        )
    ).scalars().all()
    provided = {v.field_id: v for v in report.values}
    missing = [
        f.id
        for f in required
        if _applies(f, report_company)
        and (f.id not in provided or _is_empty(provided[f.id]))
    ]
    if missing:
        raise HTTPException(status_code=422, detail={"error": "missing_required_fields", "field_ids": missing})
    if report.bank_statement_file_id is None:
        raise HTTPException(status_code=422, detail={"error": "bank_statement_required"})

    _transition(db, report, ReportStatus.SUBMITTED.value, actor)
    report.submitted_by_id = actor.id
    report.submitted_at = datetime.now(timezone.utc)
    audit.record(db, action="report.submit", actor=actor, target_type="report", target_id=report.id, company_id=report.company_id)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.post("/reports/{report_id}/return", response_model=ReportOut)
def return_report(
    report_id: int,
    payload: ReportReturn,
    actor: User = Depends(require("report:review")),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = _load(db, report_id)
    _assert_report_company_access(db, actor, report)
    if report.status != ReportStatus.SUBMITTED.value:
        raise HTTPException(status_code=409, detail="Only submitted reports can be returned")
    _transition(db, report, ReportStatus.RETURNED.value, actor, reason=payload.reason)
    report.returned_reason = payload.reason
    report.reviewed_by_id = actor.id
    report.reviewed_at = datetime.now(timezone.utc)
    audit.record(db, action="report.return", actor=actor, target_type="report", target_id=report.id, company_id=report.company_id, meta={"reason": payload.reason})
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.post("/reports/{report_id}/approve", response_model=ReportOut)
def approve_report(
    report_id: int,
    actor: User = Depends(require("report:review")),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = _load(db, report_id)
    _assert_report_company_access(db, actor, report)
    if report.status != ReportStatus.SUBMITTED.value:
        raise HTTPException(status_code=409, detail="Only submitted reports can be approved")
    _transition(db, report, ReportStatus.APPROVED.value, actor)
    report.reviewed_by_id = actor.id
    report.reviewed_at = datetime.now(timezone.utc)
    report.locked_at = datetime.now(timezone.utc)
    audit.record(db, action="report.approve", actor=actor, target_type="report", target_id=report.id, company_id=report.company_id)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.post("/reports/{report_id}/forward", response_model=ReportOut)
def forward_report(
    report_id: int,
    actor: User = Depends(require("report:forward")),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = _load(db, report_id)
    _assert_report_company_access(db, actor, report)
    if report.status != ReportStatus.APPROVED.value:
        raise HTTPException(status_code=409, detail="Only approved reports can be forwarded")
    _transition(db, report, ReportStatus.FORWARDED.value, actor)
    report.forwarded_at = datetime.now(timezone.utc)
    audit.record(db, action="report.forward", actor=actor, target_type="report", target_id=report.id, company_id=report.company_id)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.get("/reports/{report_id}/export")
def export_report(
    report_id: int,
    actor: User = Depends(require("report:export")),
    db: Session = Depends(get_db),
):
    """Excel export. Values are written with the company currency, never summed
    across currencies."""
    import io

    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook

    report = _load_visible(db, report_id, actor)
    _assert_report_company_access(db, actor, report)
    fields = {f.id: f for f in db.execute(select(FormField)).scalars().all()}

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append(["Report ID", report.id])
    ws.append(["Company ID", report.company_id])
    ws.append(["Period ID", report.period_id])
    ws.append(["Status", report.status])
    ws.append(["Currency", report.currency])
    ws.append([])
    ws.append(["Field (AR)", "Field (EN)", "Version", "Text value", "Numeric value", "Currency"])
    for v in report.values:
        field = fields.get(v.field_id)
        ws.append(
            [
                field.name_ar if field else v.field_id,
                field.name_en if field else "",
                v.field_version,
                v.value_text,
                float(v.value_number) if v.value_number is not None else None,
                report.currency,
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    audit.record(db, action="report.export", actor=actor, target_type="report", target_id=report.id, company_id=report.company_id)
    db.commit()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report-{report.id}.xlsx"},
    )


def _perms(user: User) -> set[str]:
    out: set[str] = set()
    for ur in user.roles:
        if ur.role:
            out |= ur.role.permission_codes
    return out

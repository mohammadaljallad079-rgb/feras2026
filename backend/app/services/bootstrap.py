"""Idempotent bootstrap of the platform's structural records.

Two things must exist for the brief's monthly-report cycle (§7.1, §7.4) to work
on a fresh install, and neither is demo business data:

* the canonical report fields the brief names — core company fields, the extra
  industrial fields, and the Holding's own fields;
* the Holding's own company record, which §7.1 reports on like a subsidiary and
  §7.4 gives its own fields.

Both are created through the same tables the form builder and the companies
screen use, so they can be edited afterwards exactly like anything else.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.report_fields import (
    CORE_FIELDS,
    HOLDING_COMPANY,
    HOLDING_FIELDS,
    INDUSTRIAL_FIELDS,
    INDUSTRIAL_SECTOR_AR,
)
from app.models.business import Company, FormField
from app.models.enums import CompanyStatus


def ensure_holding_company(db: Session) -> Company:
    """Create the Holding's own company record once, and return it."""
    company = db.execute(select(Company).where(Company.is_holding.is_(True))).scalars().first()
    if company is not None:
        return company
    company = Company(
        **HOLDING_COMPANY,
        status=CompanyStatus.ACTIVE.value,
        is_holding=True,
    )
    db.add(company)
    db.flush()
    return company


def _ensure_field(
    db: Session,
    *,
    code: str,
    name_ar: str,
    name_en: str,
    field_type: str,
    is_required: bool,
    parent_id: int | None,
    sector_scope: str | None,
    company_id: int | None,
    display_order: int,
) -> FormField:
    field = db.execute(select(FormField).where(FormField.code == code)).scalars().first()
    if field is None:
        field = FormField(
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            field_type=field_type,
            is_required=is_required,
            parent_id=parent_id,
            sector_scope=sector_scope,
            company_id=company_id,
            display_order=display_order,
            version=1,
        )
        db.add(field)
        db.flush()
    return field


def ensure_report_fields(db: Session) -> None:
    """Seed the report fields the brief names, without overwriting edits."""
    holding = ensure_holding_company(db)

    def seed(rows, *, sector_scope=None, company_id=None, order_start=0) -> None:
        by_code: dict[str, int] = {}
        for i, (code, ar, en, ftype, required, parent_code) in enumerate(rows):
            parent_id = by_code.get(parent_code) if parent_code else None
            field = _ensure_field(
                db,
                code=code,
                name_ar=ar,
                name_en=en,
                field_type=ftype,
                is_required=required,
                parent_id=parent_id,
                sector_scope=sector_scope,
                company_id=company_id,
                display_order=order_start + i,
            )
            by_code[code] = field.id

    seed(CORE_FIELDS, order_start=10)
    seed(INDUSTRIAL_FIELDS, sector_scope=INDUSTRIAL_SECTOR_AR, order_start=40)
    seed(HOLDING_FIELDS, company_id=holding.id, order_start=60)
    db.flush()

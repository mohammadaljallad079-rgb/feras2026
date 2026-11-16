"""Company registry, reporting periods, dynamic form builder, monthly reports."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    CompanyStatus,
    FieldType,
    PeriodStatus,
    ReportStatus,
)
from app.models.identity import TimestampMixin


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(64))
    sector: Mapped[str] = mapped_column(String(128), index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manager_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ownership_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100.00"))
    currency: Mapped[str] = mapped_column(String(8), default="SAR")
    status: Mapped[str] = mapped_column(String(16), default=CompanyStatus.DRAFT.value, index=True)
    logo_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_visible: Mapped[bool] = mapped_column(Boolean, default=False)

    manager: Mapped["object | None"] = relationship("User", foreign_keys=[manager_user_id], lazy="joined")


class ReportingPeriod(Base, TimestampMixin):
    __tablename__ = "reporting_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    label_ar: Mapped[str] = mapped_column(String(64))
    label_en: Mapped[str] = mapped_column(String(64))
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer)
    opens_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default=PeriodStatus.OPEN.value, index=True)

    __table_args__ = (UniqueConstraint("year", "month", name="uq_period_year_month"),)


class FormField(Base, TimestampMixin):
    """A versioned definition of one configurable reporting field."""

    __tablename__ = "form_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name_ar: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    field_type: Mapped[str] = mapped_column(String(16), default=FieldType.TEXT.value)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("form_fields.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sector_scope: Mapped[str | None] = mapped_column(String(128), nullable=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Bumped whenever a definition changes so historical reports keep their shape.
    version: Mapped[int] = mapped_column(Integer, default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class MonthlyReport(Base, TimestampMixin):
    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint("company_id", "period_id", name="uq_report_company_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=ReportStatus.DRAFT.value, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="SAR")
    commentary: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_statement_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Company] = relationship(lazy="joined")
    period: Mapped[ReportingPeriod] = relationship(lazy="joined")
    values: Mapped[list["ReportValue"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", lazy="selectin"
    )


class ReportValue(Base):
    __tablename__ = "report_values"
    __table_args__ = (UniqueConstraint("report_id", "field_id", name="uq_report_field"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("form_fields.id", ondelete="RESTRICT"), index=True)
    # Snapshot of the definition at capture time so later edits cannot corrupt history.
    field_version: Mapped[int] = mapped_column(Integer, default=1)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    report: Mapped[MonthlyReport] = relationship(back_populates="values")
    field: Mapped[FormField] = relationship(lazy="joined")


class ReportEvent(Base):
    """Append-only transition log for a report (submit/return/approve/forward)."""

    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("monthly_reports.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

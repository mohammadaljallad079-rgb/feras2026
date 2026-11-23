"""Files, service requests, leads, opportunities, directives, HR, website, advisor."""

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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    AdvisorMessageStatus,
    AccountingStatus,
    DirectiveStatus,
    EmployeeStatus,
    LeadStatus,
    OpportunityStatus,
    RequestPriority,
    RequestStatus,
    SubmissionStatus,
)
from app.models.identity import TimestampMixin


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    storage_name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountingEntry(Base, TimestampMixin):
    __tablename__ = "accounting_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), index=True)
    reference: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(8), default="SAR")
    entry_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default=AccountingStatus.DRAFT.value, index=True)
    # The three sections of PDF page 9 each carry their own extra columns:
    # expenses have a party and a settlement, invoices a tax line, commissions a
    # direction (incoming/outgoing).
    party: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Table 5: an expense carries a settlement state (مسدد / غير مسدد) and a
    # commission a settlement state (مستحقة / مدفوعة / مستلمة). Both are stored
    # in this single column; the form labels it per entry kind.
    payment_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Table 5, «إيراد / فاتورة جديدة»: the client's tax registration number
    # (manual entry only) and the service item being invoiced.
    tax_registration_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service_item: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ServiceRequest(Base, TimestampMixin):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Table 5: «نوع الخدمة *» (accounting, design, study/help, marketing).
    service_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    priority: Mapped[str] = mapped_column(String(16), default=RequestPriority.NORMAL.value)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=RequestStatus.NEW.value, index=True)
    # §11 «المسوّق يرسل الشكوى للمالك وحده»: a complaint is addressed to the owner
    # and must not surface to anyone else, so it is flagged rather than left to
    # company scope — a manager or developer scoped to the same company would
    # otherwise see it.
    is_complaint: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), index=True)


class ServiceRequestReply(Base):
    __tablename__ = "service_request_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    is_status_change: Mapped[bool] = mapped_column(Boolean, default=False)
    new_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Table 6, «عميل محتمل جديد»: «وسيلة التواصل» — how the lead prefers to be
    # reached (email / phone / other), kept apart from the contact value itself.
    contact_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    follow_up_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=LeadStatus.NEW.value, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Table 5, «فرصة جديدة»: the country is required and a study file may be
    # attached; Table 3 lists both, with the record's source.
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attachment_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="SAR")
    status: Mapped[str] = mapped_column(String(16), default=OpportunityStatus.DRAFT.value, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Opportunity file (owner request, additive and optional) -------------
    # The brief fixes the table columns and the decision workflow but says
    # nothing about the analysis behind a decision. These columns hold it
    # without changing the six columns §5.1 prints, and every one is nullable
    # so an opportunity created the spec's way is still complete.
    # «تصنيف الفرصة»: commercial or investment (Table 3 names both).
    category: Mapped[str | None] = mapped_column(String(24), nullable=True)
    # «المطلوب من المجموعة»: what the holding is asked to provide.
    requested_from_group: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Financials: the forecast the outcome is later measured against.
    investment_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    # Whole percent, e.g. 12.5 for 12.5%.
    expected_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    cashflow_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Risk and its mitigation, stated in words rather than scored: a score would
    # invent a rating scale the brief never defines.
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # «المسؤول عن المتابعة والموعد القادم» — assigned by the owner with the
    # decision; no new approval level, only an accountable person and a date.
    next_step_owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    next_step_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # The realised outcome, entered after approval so the file can be compared
    # with its forecast.
    actual_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    next_step_owner: Mapped["User | None"] = relationship(
        "User", foreign_keys=[next_step_owner_id], lazy="joined"
    )

    @property
    def next_step_owner_name(self) -> str | None:
        if self.next_step_owner is None:
            return None
        return self.next_step_owner.full_name_ar or self.next_step_owner.full_name_en

    attachment: Mapped["StoredFile | None"] = relationship(
        "StoredFile", foreign_keys=[attachment_file_id], lazy="joined"
    )

    @property
    def attachment_name(self) -> str | None:
        return getattr(self.attachment, "original_name", None)


class ExecutiveDirective(Base, TimestampMixin):
    __tablename__ = "executive_directives"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    follow_up_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=DirectiveStatus.DRAFT.value, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Table 6, «نعم، أحلها لمطوّر الأعمال»: the assistant referral creates a
    # directive for the business developer and a task on their dashboard. The
    # flag lets that dashboard count only these tasks, not every directive.
    is_assistant_task: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(255))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salary: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="SAR")
    contract_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Table 5, «إضافة موظف»: a contract summary plus two uploaded documents —
    # the official documents and the employment contract.
    contract_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_documents_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    employment_contract_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default=EmployeeStatus.ACTIVE.value, index=True)
    hired_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    official_documents: Mapped["StoredFile | None"] = relationship(
        "StoredFile", foreign_keys=[official_documents_file_id], lazy="joined"
    )
    employment_contract: Mapped["StoredFile | None"] = relationship(
        "StoredFile", foreign_keys=[employment_contract_file_id], lazy="joined"
    )

    @property
    def official_documents_name(self) -> str | None:
        return getattr(self.official_documents, "original_name", None)

    @property
    def employment_contract_name(self) -> str | None:
        return getattr(self.employment_contract, "original_name", None)


class EmployeeEvent(Base):
    __tablename__ = "employee_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text)
    effective_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    attachment_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiProviderSetting(Base, TimestampMixin):
    """Server-side AI provider configuration.

    The API key is never returned to any client: only ``has_api_key`` and a
    masked hint are exposed. The key is resolved from the environment or from
    this row, so an owner can change provider/model/class without a redeploy.
    """

    __tablename__ = "ai_provider_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    base_url: Mapped[str] = mapped_column(String(255), default="https://api.openai.com/v1")
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class WebsiteSubmission(Base, TimestampMixin):
    __tablename__ = "website_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_no: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Service requests carry the requested service type; opportunities carry a
    # project country and a subject; job applications carry an area of expertise.
    service_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expertise: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    # Optional study file (opportunity) or CV (job application); private.
    attachment_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=SubmissionStatus.NEW.value, index=True)
    converted_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    converted_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    attachment: Mapped["StoredFile | None"] = relationship(
        "StoredFile", foreign_keys=[attachment_file_id], lazy="joined"
    )

    @property
    def attachment_name(self) -> str | None:
        """§6.5: the details modal names the attachment, never its content."""
        return getattr(self.attachment, "original_name", None)


class WebsiteSubmissionEvent(Base, TimestampMixin):
    """Append-only status/assignment history for a website submission."""

    __tablename__ = "website_submission_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("website_submissions.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AdvisorMessage(Base, TimestampMixin):
    __tablename__ = "advisor_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default=AdvisorMessageStatus.UNREAD.value, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiQuery(Base):
    """Audit trail for assistant calls, including grounding sources."""

    __tablename__ = "ai_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

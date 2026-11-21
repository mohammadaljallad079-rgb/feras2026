"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth -------------------------------------------------------------------
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class PasswordResetIssued(BaseModel):
    reset_token: str | None = None
    message: str


# --- Users / roles ----------------------------------------------------------
class RoleOut(ORMModel):
    id: int
    slug: str
    name_ar: str
    name_en: str
    description: str | None = None
    is_system: bool
    permission_codes: list[str] = []


class RoleCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name_ar: str
    name_en: str
    description: str | None = None
    permissions: list[str]


class RoleUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class UserOut(ORMModel):
    id: int
    email: str
    full_name_ar: str
    full_name_en: str
    locale: str
    is_active: bool
    roles: list[str] = []
    company_ids: list[int] = []
    last_login_at: datetime | None = None


class UserDirectoryOut(BaseModel):
    """Minimal identity for pickers (recipient, assignee).

    Screens that only need to name a colleague — a directive recipient, a lead
    assignee, a service-request recipient — read this instead of the admin
    ``/users`` listing, so they do not need ``user:view`` and never receive
    e-mail addresses, roles or company scopes they have no business seeing.
    """

    id: int
    full_name_ar: str
    full_name_en: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name_ar: str
    full_name_en: str
    locale: str = "ar"
    role_slugs: list[str]
    company_ids: list[int] = []


class UserUpdate(BaseModel):
    full_name_ar: str | None = None
    full_name_en: str | None = None
    locale: str | None = None
    is_active: bool | None = None
    role_slugs: list[str] | None = None
    company_ids: list[int] | None = None


class UserInviteResult(BaseModel):
    user: UserOut
    setup_token: str
    setup_url: str


# --- Companies --------------------------------------------------------------
class CompanyBase(BaseModel):
    name_ar: str
    name_en: str
    country: str
    sector: str
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    manager_user_id: int | None = None
    ownership_percent: Decimal = Decimal("100.00")
    currency: str = "SAR"
    public_visible: bool = False
    commercial_register_no: str | None = None
    public_activity_ar: str | None = None
    public_activity_en: str | None = None
    website_url: str | None = None


class CompanyCreate(CompanyBase):
    # §6.2: the wizard does not ask for a code; the platform assigns one when it
    # is omitted, and accepts an explicit code when a caller supplies it.
    code: str | None = None
    status: str = "draft"


class CompanyUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    country: str | None = None
    sector: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    manager_user_id: int | None = None
    ownership_percent: Decimal | None = None
    currency: str | None = None
    public_visible: bool | None = None
    activation_notes: str | None = None
    commercial_register_no: str | None = None
    logo_file_id: int | None = None
    public_activity_ar: str | None = None
    public_activity_en: str | None = None
    website_url: str | None = None


class CompanyOut(ORMModel):
    id: int
    code: str
    name_ar: str
    name_en: str
    country: str
    sector: str
    contact_email: str | None
    contact_phone: str | None
    manager_user_id: int | None
    ownership_percent: Decimal
    currency: str
    status: str
    logo_file_id: int | None
    logo_url: str | None = None
    commercial_register_no: str | None = None
    manager_name_ar: str | None = None
    manager_name_en: str | None = None
    activated_at: datetime | None
    closed_at: datetime | None
    activation_notes: str | None = None
    # §7.1/§7.4: distinguishes the Holding's own report record from a subsidiary.
    is_holding: bool = False
    public_visible: bool
    public_activity_ar: str | None = None
    public_activity_en: str | None = None
    website_url: str | None = None
    created_at: datetime


# --- Reporting periods / forms ---------------------------------------------
class PeriodCreate(BaseModel):
    label_ar: str
    label_en: str
    year: int
    month: int
    opens_on: date
    due_on: date


class PeriodOut(ORMModel):
    id: int
    label_ar: str
    label_en: str
    year: int
    month: int
    opens_on: date
    due_on: date
    status: str


class FormFieldCreate(BaseModel):
    # Table 5: the builder asks for the names, type, scope and flags — not a
    # code. When a caller omits it, the platform derives one.
    code: str | None = None
    name_ar: str
    name_en: str
    field_type: str = "text"
    is_required: bool = False
    parent_id: int | None = None
    sector_scope: str | None = None
    company_id: int | None = None
    display_order: int = 0


class FormFieldUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    field_type: str | None = None
    is_required: bool | None = None
    parent_id: int | None = None
    sector_scope: str | None = None
    company_id: int | None = None
    is_active: bool | None = None
    display_order: int | None = None


class FormFieldOut(ORMModel):
    id: int
    code: str
    name_ar: str
    name_en: str
    field_type: str
    is_required: bool
    parent_id: int | None
    sector_scope: str | None
    company_id: int | None
    is_active: bool
    version: int
    display_order: int


# --- Monthly reports --------------------------------------------------------
class ReportValueIn(BaseModel):
    field_id: int
    value_text: str | None = None
    value_number: Decimal | None = None


class ReportCreate(BaseModel):
    company_id: int
    period_id: int
    commentary: str | None = None


class ReportValuesUpdate(BaseModel):
    commentary: str | None = None
    values: list[ReportValueIn]
    bank_statement_file_id: int | None = None


class ReportReturn(BaseModel):
    reason: str = Field(min_length=3)


class ReportValueOut(ORMModel):
    field_id: int
    field_version: int
    field_name_ar: str | None = None
    field_name_en: str | None = None
    value_text: str | None
    value_number: Decimal | None


class ReportEventOut(ORMModel):
    from_status: str | None
    to_status: str
    actor_id: int | None
    reason: str | None
    created_at: datetime


class ReportOut(ORMModel):
    id: int
    company_id: int
    period_id: int
    status: str
    currency: str
    commentary: str | None
    bank_statement_file_id: int | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    returned_reason: str | None
    forwarded_at: datetime | None
    locked_at: datetime | None
    created_at: datetime
    values: list[ReportValueOut] = []


# --- Accounting -------------------------------------------------------------
class AccountingCreate(BaseModel):
    kind: str
    company_id: int
    reference: str
    description: str
    amount: Decimal
    # §5.3: «العملة الافتراضية BHD» — the holding books are kept in dinars.
    currency: str = "BHD"
    entry_date: date
    party: str | None = None
    tax_amount: Decimal | None = None
    direction: str | None = None
    payment_status: str | None = None
    # Table 5, «إيراد / فاتورة جديدة»: the client's tax registration number
    # (manual entry) and the service item.
    tax_registration_no: str | None = None
    service_item: str | None = None
    document_file_id: int | None = None


class AccountingUpdate(BaseModel):
    description: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    entry_date: date | None = None
    status: str | None = None
    party: str | None = None
    tax_amount: Decimal | None = None
    direction: str | None = None
    payment_status: str | None = None
    tax_registration_no: str | None = None
    service_item: str | None = None
    document_file_id: int | None = None


class AccountingOut(ORMModel):
    id: int
    kind: str
    company_id: int
    reference: str
    description: str
    amount: Decimal
    currency: str
    entry_date: date
    status: str
    party: str | None = None
    tax_amount: Decimal | None = None
    direction: str | None = None
    payment_status: str | None = None
    tax_registration_no: str | None = None
    service_item: str | None = None
    document_file_id: int | None
    created_at: datetime


# --- Service requests -------------------------------------------------------
class ServiceRequestCreate(BaseModel):
    subject: str
    body: str | None = None
    # Table 5 marks «نوع الخدمة» required: it is the routing key.
    service_type: str
    company_id: int
    # The owner picks the receiving specialist explicitly; a manager does not,
    # and the request is then routed to a specialist by service type (§6.4).
    recipient_id: int | None = None
    priority: str = "normal"
    deadline: date | None = None


class ServiceRequestUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    deadline: date | None = None
    recipient_id: int | None = None


class ComplaintCreate(BaseModel):
    """Table 5: the marketer's complaint to the owner — free text, mandatory."""

    body: str = Field(min_length=1)
    subject: str | None = None
    company_id: int | None = None


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1)
    new_status: str | None = None


class ReplyOut(ORMModel):
    id: int
    author_id: int
    body: str
    is_status_change: bool
    new_status: str | None
    created_at: datetime


class ServiceRequestOut(ORMModel):
    id: int
    subject: str
    body: str | None
    service_type: str | None = None
    company_id: int
    created_by_id: int
    recipient_id: int
    priority: str
    deadline: date | None
    status: str
    created_at: datetime
    is_complaint: bool = False


# --- Leads ------------------------------------------------------------------
class LeadCreate(BaseModel):
    name: str
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    # Table 6 R3 marks «الخدمة المطلوبة *» mandatory: it is what the receiving
    # company's manager is asked to serve.
    requested_service: str = Field(min_length=1)
    source: str | None = None
    contact_method: str | None = None
    company_id: int
    follow_up_at: date | None = None
    notes: str | None = None
    assigned_to_id: int | None = None


class LeadUpdate(BaseModel):
    status: str | None = None
    follow_up_at: date | None = None
    notes: str | None = None
    assigned_to_id: int | None = None
    requested_service: str | None = None


class LeadOut(ORMModel):
    id: int
    name: str
    contact_email: str | None
    contact_phone: str | None
    requested_service: str | None
    source: str | None
    contact_method: str | None
    company_id: int
    follow_up_at: date | None
    status: str
    notes: str | None
    assigned_to_id: int | None
    created_at: datetime


# --- Opportunities ----------------------------------------------------------
class OpportunityCreate(BaseModel):
    title: str
    company_id: int
    description: str | None = None
    # Table 5 R5: the new-opportunity modal marks «الدولة *» as mandatory, so the
    # API refuses an opportunity that names no country. «ملف الدراسة» stays
    # optional; Table 3 lists the country, the file and the source per row.
    country: str = Field(min_length=1)
    attachment_file_id: int | None = None
    source: str | None = None
    estimated_value: Decimal | None = None
    currency: str = "SAR"


class OpportunityDecision(BaseModel):
    decision: str
    note: str | None = None


class OpportunityOut(ORMModel):
    id: int
    title: str
    company_id: int
    description: str | None
    country: str | None = None
    attachment_file_id: int | None = None
    attachment_name: str | None = None
    source: str | None = None
    estimated_value: Decimal | None
    currency: str
    status: str
    created_by_id: int
    submitted_at: datetime | None
    decided_by_id: int | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime


# --- Directives -------------------------------------------------------------
class DirectiveCreate(BaseModel):
    title: str
    body: str
    recipient_id: int
    company_id: int | None = None
    follow_up_on: date | None = None


class DirectiveOut(ORMModel):
    id: int
    title: str
    body: str
    created_by_id: int
    recipient_id: int
    company_id: int | None
    follow_up_on: date | None
    status: str
    sent_at: datetime | None
    received_at: datetime | None
    completed_at: datetime | None
    escalation_note: str | None
    created_at: datetime
    # Table 5/10: «نعم، أحلها لمطوّر الأعمال» produces a task, which the
    # developer's dashboard shows as an assistant task rather than a directive.
    is_assistant_task: bool = False


# --- Employees --------------------------------------------------------------
class EmployeeCreate(BaseModel):
    name_ar: str
    name_en: str
    job_title: str
    company_id: int
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    salary: Decimal | None = None
    currency: str = "SAR"
    contract_type: str | None = None
    # Table 5, «إضافة موظف»: a contract summary plus two uploaded documents —
    # the official documents and the employment contract.
    contract_summary: str | None = None
    official_documents_file_id: int | None = None
    employment_contract_file_id: int | None = None
    hired_on: date | None = None


class EmployeeUpdate(BaseModel):
    job_title: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    salary: Decimal | None = None
    contract_type: str | None = None
    contract_summary: str | None = None
    official_documents_file_id: int | None = None
    employment_contract_file_id: int | None = None
    status: str | None = None


class EmployeeOut(ORMModel):
    id: int
    name_ar: str
    name_en: str
    job_title: str
    company_id: int
    contact_email: str | None
    contact_phone: str | None
    salary: Decimal | None
    currency: str
    contract_type: str | None
    contract_summary: str | None = None
    official_documents_file_id: int | None = None
    official_documents_name: str | None = None
    employment_contract_file_id: int | None = None
    employment_contract_name: str | None = None
    status: str
    hired_on: date | None
    created_at: datetime


class EmployeeEventCreate(BaseModel):
    kind: str
    detail: str
    effective_on: date | None = None
    attachment_file_id: int | None = None


class EmployeeEventOut(ORMModel):
    id: int
    employee_id: int
    kind: str
    detail: str
    effective_on: date | None
    attachment_file_id: int | None
    created_at: datetime


# --- Website submissions ----------------------------------------------------
class PublicSubmission(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=64)
    message: str | None = None
    # Per-kind fields (brief §8). All optional at the base level; the router
    # enforces what each kind requires so the same schema serves the three forms.
    service_type: str | None = Field(default=None, max_length=128)
    country: str | None = Field(default=None, max_length=64)
    subject: str | None = Field(default=None, max_length=255)
    expertise: str | None = Field(default=None, max_length=255)
    company_id: int | None = None
    consent: bool = False


class SubmissionOut(ORMModel):
    id: int
    reference_no: str | None
    kind: str
    name: str
    email: str
    phone: str | None
    message: str | None
    service_type: str | None
    country: str | None
    subject: str | None
    expertise: str | None
    consent: bool
    company_id: int | None
    attachment_file_id: int | None
    assigned_user_id: int | None
    internal_notes: str | None
    status: str
    converted_type: str | None
    converted_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
    # §6.5: the details modal names the attachment. The file content is not
    # inlined; only its original name is exposed here.
    attachment_name: str | None = None


class SubmissionConvert(BaseModel):
    """Table 7 / §6.5: the "take action" outcome depends on the submission kind.

    A service request is routed from the modal and therefore carries the
    receiving company and the service type; an opportunity and a job
    application are converted without further input.
    """

    # Optional: the submission kind decides the outcome; this is only a fallback
    # for callers that pass it explicitly.
    target: str | None = None
    company_id: int | None = None
    service_type: str | None = None


class SubmissionUpdate(BaseModel):
    status: str | None = None
    assigned_user_id: int | None = None
    internal_notes: str | None = None


class SubmissionEventOut(ORMModel):
    id: int
    from_status: str | None
    to_status: str | None
    note: str | None
    actor_user_id: int | None
    created_at: datetime


class VisibilityUpdate(BaseModel):
    public_visible: bool


# --- Public site content (CMS) ----------------------------------------------
class SiteSettingOut(ORMModel):
    id: int
    key: str
    value_ar: str | None
    value_en: str | None


class SiteSettingUpdate(BaseModel):
    value_ar: str | None = None
    value_en: str | None = None


class SiteSectionOut(ORMModel):
    id: int
    key: str
    title_ar: str | None
    title_en: str | None
    body_ar: str | None
    body_en: str | None
    image_file_id: int | None
    sort_order: int
    is_visible: bool
    needs_review: bool


class SiteSectionUpdate(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    body_ar: str | None = None
    body_en: str | None = None
    image_file_id: int | None = None
    sort_order: int | None = None
    is_visible: bool | None = None
    needs_review: bool | None = None


class SiteSlideOut(ORMModel):
    id: int
    eyebrow_ar: str | None
    eyebrow_en: str | None
    title_ar: str
    title_en: str
    body_ar: str | None
    body_en: str | None
    image_file_id: int | None
    cta_primary_label_ar: str | None
    cta_primary_label_en: str | None
    cta_primary_href: str | None
    cta_secondary_label_ar: str | None
    cta_secondary_label_en: str | None
    cta_secondary_href: str | None
    sort_order: int
    is_active: bool


class SiteSlideCreate(BaseModel):
    eyebrow_ar: str | None = None
    eyebrow_en: str | None = None
    title_ar: str
    title_en: str
    body_ar: str | None = None
    body_en: str | None = None
    image_file_id: int | None = None
    cta_primary_label_ar: str | None = None
    cta_primary_label_en: str | None = None
    cta_primary_href: str | None = None
    cta_secondary_label_ar: str | None = None
    cta_secondary_label_en: str | None = None
    cta_secondary_href: str | None = None
    sort_order: int = 0
    is_active: bool = True


class SiteSlideUpdate(BaseModel):
    eyebrow_ar: str | None = None
    eyebrow_en: str | None = None
    title_ar: str | None = None
    title_en: str | None = None
    body_ar: str | None = None
    body_en: str | None = None
    image_file_id: int | None = None
    cta_primary_label_ar: str | None = None
    cta_primary_label_en: str | None = None
    cta_primary_href: str | None = None
    cta_secondary_label_ar: str | None = None
    cta_secondary_label_en: str | None = None
    cta_secondary_href: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class SiteServiceOut(ORMModel):
    id: int
    slug: str
    name_ar: str
    name_en: str
    description_ar: str | None
    description_en: str | None
    icon: str | None
    sort_order: int
    is_active: bool
    needs_review: bool


class SiteServiceCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    name_ar: str
    name_en: str
    description_ar: str | None = None
    description_en: str | None = None
    icon: str | None = None
    sort_order: int = 0
    is_active: bool = True


class SiteServiceUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    description_ar: str | None = None
    description_en: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    needs_review: bool | None = None


class SiteNavLinkOut(ORMModel):
    id: int
    location: str
    label_ar: str
    label_en: str
    href: str
    sort_order: int
    is_active: bool


class SiteNavLinkCreate(BaseModel):
    location: str
    label_ar: str
    label_en: str
    href: str
    sort_order: int = 0
    is_active: bool = True


class SiteNavLinkUpdate(BaseModel):
    label_ar: str | None = None
    label_en: str | None = None
    href: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class PublicCompanyOut(BaseModel):
    """The only company fields the public website may expose (brief §5.D)."""

    code: str
    name_ar: str
    name_en: str
    sector: str
    country: str
    logo_url: str | None = None
    activity_ar: str | None = None
    activity_en: str | None = None
    website_url: str | None = None


class CompanyProfileUpdate(BaseModel):
    """Table 7: the public activity text and the optional live-site link."""

    public_activity_ar: str | None = None
    public_activity_en: str | None = None
    website_url: str | None = Field(default=None, max_length=255)


class SiteBootstrap(BaseModel):
    """Everything the public site needs for one render, in one request."""

    settings: dict[str, dict[str, str | None]]
    sections: list[SiteSectionOut]
    slides: list[SiteSlideOut]
    services: list[SiteServiceOut]
    header_nav: list[SiteNavLinkOut]
    footer_nav: list[SiteNavLinkOut]
    opportunity_countries: list[dict[str, str]]
    # §13 privacy policy, from the approved deck so the page and the seed copy
    # cannot drift apart.
    privacy: dict[str, Any]


# --- Advisor ----------------------------------------------------------------
class AdvisorMessageCreate(BaseModel):
    recipient_id: int
    category: str
    subject: str
    body: str
    company_id: int | None = None


class AdvisorMessageOut(ORMModel):
    id: int
    author_id: int
    recipient_id: int
    category: str
    subject: str
    body: str
    company_id: int | None
    status: str
    read_at: datetime | None
    created_at: datetime


# --- Files ------------------------------------------------------------------
class FileOut(ORMModel):
    id: int
    original_name: str
    content_type: str
    size_bytes: int
    is_confidential: bool
    company_id: int | None
    created_at: datetime


# --- AI ---------------------------------------------------------------------
class AiAskRequest(BaseModel):
    prompt: str = Field(min_length=2)
    company_id: int | None = None
    period_id: int | None = None


class AiReferRequest(BaseModel):
    """Table 5: the owner refers the assistant's plan to the business developer."""

    title: str | None = None
    body: str | None = None


class AiSource(BaseModel):
    kind: str
    ref: str
    label: str
    url: str | None = None


class AiAnswer(BaseModel):
    answer: str
    confidence: str
    sources: list[AiSource]
    provider: str
    model: str
    configured: bool
    note: str | None = None


class AiSummarySection(BaseModel):
    key: str
    title_ar: str
    title_en: str
    lines_ar: list[str]
    lines_en: list[str]


class AiSummarySource(BaseModel):
    label_ar: str
    label_en: str
    kind: str
    url: str
    status: str
    currency: str


class AiSummaryNote(BaseModel):
    """§5.1: an alert line that carries a record to open («فتح السجل»)."""

    text_ar: str
    text_en: str
    url: str


class AiSummaryOut(BaseModel):
    # §5.1: «ملخص المالك الذكي» for the owner, «ملخص شركتك» for a manager.
    title_ar: str = "ملخص المالك الذكي"
    title_en: str = "Owner smart summary"
    period_label_ar: str
    period_label_en: str
    scope_ar: str
    scope_en: str
    sections: list[AiSummarySection]
    sources: list[AiSummarySource]
    notes: list[AiSummaryNote] = []


class AiProviderSettingsIn(BaseModel):
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = Field(default=None, min_length=8)
    clear_api_key: bool = False


class AiProviderSettingsOut(BaseModel):
    provider: str
    model: str
    base_url: str
    has_api_key: bool
    api_key_hint: str | None
    configured: bool
    model_classes: list[str]
    env_key_locked: bool


class AiSettingsTestResult(BaseModel):
    ok: bool
    provider: str
    model: str
    message_ar: str
    message_en: str


# --- Dashboard --------------------------------------------------------------
class DashboardCard(BaseModel):
    key: str
    label_ar: str
    label_en: str
    value: str | int
    hint_ar: str | None = None
    hint_en: str | None = None
    # PDF page 5: the owner's KPIs are clickable and lead to the relevant screen.
    href: str | None = None


class DashboardAction(BaseModel):
    """A dashboard shortcut that navigates to the screen that performs the work."""

    label_ar: str
    label_en: str
    href: str
    # §5.2: the manager's isolation probe is rendered in its own «اختبار العزل»
    # section rather than among the quick actions.
    group: str | None = None


class DashboardOut(BaseModel):
    role: str
    title_ar: str
    title_en: str
    cards: list[DashboardCard]
    sections: list[dict] = []
    # PDF pages 22-23: the manager's dashboard leads with the current period and
    # its deadline, and offers the actions that start the monthly work.
    banner_ar: str | None = None
    banner_en: str | None = None
    banner_tone: str | None = None
    actions: list[DashboardAction] = []

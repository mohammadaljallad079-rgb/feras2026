"""Enumerations shared by models and schemas."""

from __future__ import annotations

import enum


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class CompanyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class PeriodStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class ReportStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RETURNED = "returned"
    APPROVED = "approved"
    FORWARDED = "forwarded"


class AccountingKind(StrEnum):
    EXPENSE = "expense"
    INVOICE = "invoice"
    COMMISSION = "commission"


class AccountingStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


class RequestPriority(StrEnum):
    # Table 5, «طلب خدمة جديد»: the priority choice is «عادية» or «عاجلة».
    NORMAL = "normal"
    URGENT = "urgent"


class ServiceType(StrEnum):
    """Table 5, «نوع الخدمة *»: the four service types a request can carry.

    The request is routed to the specialist by this type (§6.4)."""

    ACCOUNTING = "accounting"
    DESIGN = "design"
    STUDY = "study"
    MARKETING = "marketing"


class RequestStatus(StrEnum):
    # Table 5, «رد / تحديث الحالة»: exactly these four states.
    NEW = "new"
    IN_PROGRESS = "in_progress"
    AWAITING_REPLY = "awaiting_reply"
    COMPLETED = "completed"


class LeadStatus(StrEnum):
    # The owner's brief (Table 5) names exactly these six lead statuses.
    NEW = "new"
    CONTACTED = "contacted"
    FOLLOWING_UP = "following_up"
    QUALIFIED = "qualified"
    NOT_SUITABLE = "not_suitable"
    CLOSED = "closed"


class OpportunityStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class DirectiveStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    COMPLETED = "completed"


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


class EmployeeEventKind(StrEnum):
    """Table 5: «إضافة إجازة / إنذار / عهدة» — the four record kinds."""

    ANNUAL_LEAVE = "annual_leave"
    SICK_LEAVE = "sick_leave"
    WARNING = "warning"
    CUSTODY = "custody"
    MOVEMENT = "movement"
    PROMOTION = "promotion"

    @classmethod
    def leave_kinds(cls) -> set[str]:
        """Annual and sick leave carry the attachments the owner may not see."""
        return {cls.ANNUAL_LEAVE.value, cls.SICK_LEAVE.value}


class FieldType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    AMOUNT = "amount"
    DATE = "date"
    BOOLEAN = "boolean"
    TEXTAREA = "textarea"


class SubmissionKind(StrEnum):
    """§1/§6.5/Table 12: the public site carries exactly three forms."""

    SERVICE_REQUEST = "service_request"
    OPPORTUNITY = "opportunity"
    JOB_APPLICATION = "job_application"


class SubmissionStatus(StrEnum):
    NEW = "new"
    IN_REVIEW = "in_review"
    NEEDS_FOLLOWUP = "needs_followup"
    CONVERTED = "converted"
    COMPLETED = "completed"
    CLOSED = "closed"
    REJECTED = "rejected"


class AdvisorCategory(StrEnum):
    RECOMMENDATION = "recommendation"
    REPORT = "report"
    SUGGESTION = "suggestion"


class AdvisorMessageStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    ACTIONED = "actioned"

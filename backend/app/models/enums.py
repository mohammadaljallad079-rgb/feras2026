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
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RequestStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    ANSWERED = "answered"
    CLOSED = "closed"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


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


class FieldType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    AMOUNT = "amount"
    DATE = "date"
    BOOLEAN = "boolean"
    TEXTAREA = "textarea"


class SubmissionKind(StrEnum):
    CONTACT = "contact"
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

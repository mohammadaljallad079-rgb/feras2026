"""Model registry — importing this module registers every table on ``Base``."""

from app.models.business import (  # noqa: F401
    Company,
    FormField,
    MonthlyReport,
    ReportingPeriod,
    ReportEvent,
    ReportValue,
)
from app.models.identity import (  # noqa: F401
    AuditEvent,
    PasswordResetToken,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserCompany,
    UserRole,
)
from app.models.operations import (  # noqa: F401
    AccountingEntry,
    AdvisorMessage,
    AiProviderSetting,
    AiQuery,
    Employee,
    EmployeeEvent,
    ExecutiveDirective,
    Lead,
    Opportunity,
    ServiceRequest,
    ServiceRequestReply,
    StoredFile,
    WebsiteSubmission,
)

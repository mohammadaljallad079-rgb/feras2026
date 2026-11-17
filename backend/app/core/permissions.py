"""Permission catalog and default role templates.

Every backend route depends on one of these permission codes. The frontend may
hide a control the user cannot use, but hiding is never the enforcement point:
the API re-checks the permission on every request.
"""

from __future__ import annotations

# --- Permission codes -------------------------------------------------------
COMPANY_VIEW = "company:view"
COMPANY_MANAGE = "company:manage"

USER_VIEW = "user:view"
USER_MANAGE = "user:manage"

ROLE_MANAGE = "role:manage"

REPORT_VIEW_OWN = "report:view_own"
REPORT_VIEW_ALL = "report:view_all"
REPORT_SUBMIT = "report:submit"
REPORT_REVIEW = "report:review"
REPORT_FORWARD = "report:forward"
REPORT_EXPORT = "report:export"
REPORT_PERIOD_MANAGE = "report:period_manage"

FORM_MANAGE = "form:manage"

ACCOUNTING_VIEW = "accounting:view"
ACCOUNTING_MANAGE = "accounting:manage"

SERVICE_VIEW = "service:view"
SERVICE_CREATE = "service:create"
SERVICE_ASSIGN = "service:assign"
SERVICE_REPLY = "service:reply"

LEAD_VIEW = "lead:view"
LEAD_MANAGE = "lead:manage"

OPP_VIEW = "opportunity:view"
OPP_CREATE = "opportunity:create"
OPP_DECIDE = "opportunity:decide"

DIRECTIVE_VIEW = "directive:view"
DIRECTIVE_CREATE = "directive:create"
DIRECTIVE_UPDATE = "directive:update"

HR_VIEW = "hr:view"
HR_MANAGE = "hr:manage"
HR_VIEW_CONFIDENTIAL = "hr:view_confidential"
HR_VIEW_SALARY = "hr:view_salary"

WEBSITE_VIEW = "website:view"
WEBSITE_MANAGE = "website:manage"
# Public-site CMS: content editing and the submission inbox are separate grants
# so a role can read the inbox without being able to rewrite the website.
SITE_MANAGE = "site:manage"
SITE_SUBMISSIONS = "site:submissions"
SITE_ASSIGN = "site:assign"

ADVISOR_VIEW = "advisor:view"
ADVISOR_SUBMIT = "advisor:submit"

AI_USE = "ai:use"
AI_CONFIGURE = "ai:configure"

AUDIT_VIEW = "audit:view"

ALL_PERMISSIONS: tuple[str, ...] = (
    COMPANY_VIEW, COMPANY_MANAGE,
    USER_VIEW, USER_MANAGE, ROLE_MANAGE,
    REPORT_VIEW_OWN, REPORT_VIEW_ALL, REPORT_SUBMIT, REPORT_REVIEW, REPORT_FORWARD, REPORT_EXPORT, REPORT_PERIOD_MANAGE,
    FORM_MANAGE,
    ACCOUNTING_VIEW, ACCOUNTING_MANAGE,
    SERVICE_VIEW, SERVICE_CREATE, SERVICE_ASSIGN, SERVICE_REPLY,
    LEAD_VIEW, LEAD_MANAGE,
    OPP_VIEW, OPP_CREATE, OPP_DECIDE,
    DIRECTIVE_VIEW, DIRECTIVE_CREATE, DIRECTIVE_UPDATE,
    HR_VIEW, HR_MANAGE, HR_VIEW_CONFIDENTIAL, HR_VIEW_SALARY,
    WEBSITE_VIEW, WEBSITE_MANAGE,
    SITE_MANAGE, SITE_SUBMISSIONS, SITE_ASSIGN,
    ADVISOR_VIEW, ADVISOR_SUBMIT,
    AI_USE, AI_CONFIGURE,
    AUDIT_VIEW,
)

# --- Personas named in the specification ------------------------------------
OWNER = "owner"
COMPANY_MANAGER = "company_manager"
ACCOUNTANT = "accountant"
BUSINESS_DEVELOPER = "business_developer"
MARKETER = "marketer"
DESIGNER = "designer"
ADVISOR = "advisor"
SERVICE_SPECIALIST = "service_specialist"

# Default role -> permission template. Custom roles are created on top of this.
ROLE_TEMPLATES: dict[str, dict[str, object]] = {
    OWNER: {
        "name_ar": "مالك المجموعة",
        "name_en": "Holding Owner",
        # Broad oversight, but not the accountant's review/forward duties: the
        # owner reads the reports that were formally sent to management
        # (design reference page 8), rather than every draft. Confidential HR
        # attachments are withheld from the owner too: page 14 says leave
        # attachments read «مرفق مقيد» to the owner.
        "permissions": [
            p
            for p in ALL_PERMISSIONS
            if p not in (REPORT_REVIEW, REPORT_FORWARD, HR_VIEW_CONFIDENTIAL)
        ],
    },
    COMPANY_MANAGER: {
        "name_ar": "مدير شركة",
        "name_en": "Company Manager",
        "permissions": [
            COMPANY_VIEW, USER_VIEW, REPORT_VIEW_OWN, REPORT_SUBMIT, FORM_MANAGE,
            SERVICE_VIEW, SERVICE_CREATE, SERVICE_REPLY, LEAD_VIEW,
            DIRECTIVE_VIEW, DIRECTIVE_UPDATE, HR_VIEW, HR_MANAGE,
            HR_VIEW_CONFIDENTIAL, HR_VIEW_SALARY,
            ACCOUNTING_VIEW, WEBSITE_VIEW, AI_USE,
        ],
    },
    ACCOUNTANT: {
        "name_ar": "محاسب",
        "name_en": "Accountant",
        "permissions": [
            COMPANY_VIEW, REPORT_VIEW_ALL, REPORT_REVIEW, REPORT_FORWARD, REPORT_EXPORT, REPORT_PERIOD_MANAGE,
            ACCOUNTING_VIEW, ACCOUNTING_MANAGE, SERVICE_VIEW, SERVICE_REPLY, AI_USE,
        ],
    },
    BUSINESS_DEVELOPER: {
        "name_ar": "مطوّر أعمال",
        "name_en": "Business Developer",
        "permissions": [
            COMPANY_VIEW, REPORT_VIEW_ALL, LEAD_VIEW, LEAD_MANAGE,
            OPP_VIEW, OPP_CREATE, SERVICE_VIEW, SERVICE_CREATE,
            ADVISOR_VIEW, ADVISOR_SUBMIT, WEBSITE_VIEW, WEBSITE_MANAGE,
            SITE_SUBMISSIONS, SITE_ASSIGN, AI_USE,
        ],
    },
    MARKETER: {
        "name_ar": "مسوّق",
        "name_en": "Marketer",
        "permissions": [
            COMPANY_VIEW, LEAD_VIEW, LEAD_MANAGE, SERVICE_VIEW, SERVICE_CREATE, AI_USE,
        ],
    },
    DESIGNER: {
        "name_ar": "مصمّم",
        "name_en": "Designer",
        "permissions": [
            COMPANY_VIEW, SERVICE_VIEW, SERVICE_REPLY, AI_USE,
        ],
    },
    ADVISOR: {
        "name_ar": "مستشار خارجي",
        "name_en": "External Advisor",
        "permissions": [
            COMPANY_VIEW, ADVISOR_VIEW, ADVISOR_SUBMIT, AI_USE,
        ],
    },
    SERVICE_SPECIALIST: {
        "name_ar": "أخصائي خدمات",
        "name_en": "Service Specialist",
        "permissions": [
            COMPANY_VIEW, SERVICE_VIEW, SERVICE_REPLY, AI_USE,
        ],
    },
}


def permissions_for_roles(role_slugs: list[str]) -> set[str]:
    """Union of template permissions for the given role slugs."""
    out: set[str] = set()
    for slug in role_slugs:
        tpl = ROLE_TEMPLATES.get(slug)
        if tpl:
            out.update(tpl["permissions"])  # type: ignore[arg-type]
    return out

"""Canonical monthly-report fields from the brief §7.4.

The brief names the fields every company report carries, the extra fields an
industrial company carries, and the fields that belong to the Holding's own
report. They are seeded as ordinary `form_fields` rows — the same records the
form builder edits — so the report screen renders them and the versioning rule
(«Editing does not change past reports») holds for them too.

Scope is expressed exactly as the builder expresses it: an unscoped field
applies to every company, a `sector_scope` field to one sector, and a
`company_id` field to one company (the Holding).
"""

from __future__ import annotations

# --- Core company fields (every company) -----------------------------------
# (code, name_ar, name_en, field_type, is_required, parent_code)
CORE_FIELDS: list[tuple[str, str, str, str, bool, str | None]] = [
    ("monthly_revenue", "الإيراد الشهري", "Monthly revenue", "amount", False, None),
    ("expenses", "المصاريف", "Expenses", "amount", False, None),
    ("salaries", "الرواتب", "Salaries", "amount", True, "expenses"),
    ("office_rent", "إيجار مكتب", "Office rent", "amount", False, "expenses"),
    ("outstanding_receivables", "إجمالي الذمم المدينة القائمة", "Total outstanding receivables", "amount", False, None),
    ("bank_balance", "الرصيد البنكي بنهاية الشهر", "Bank balance at month end", "amount", True, None),
    ("owner_withdrawals", "هل حدثت سحوبات للمالك هذا الشهر؟", "Did owner withdrawals occur this month?", "boolean", False, None),
]

# --- Extra fields for an industrial company (§7.4) -------------------------
INDUSTRIAL_SECTOR_AR = "صناعي"
INDUSTRIAL_FIELDS: list[tuple[str, str, str, str, bool, str | None]] = [
    ("monthly_production", "إجمالي الإنتاج الشهري", "Total monthly production", "amount", False, None),
    ("industrial_orders", "الطلبات الصناعية المنفذة", "Industrial orders completed", "number", False, None),
    ("raw_material_cost", "تكلفة المواد الخام", "Raw material cost", "amount", False, None),
]

# --- The Holding's own report (§7.4) ---------------------------------------
HOLDING_FIELDS: list[tuple[str, str, str, str, bool, str | None]] = [
    ("group_owner_withdrawals", "سحوبات مالك المجموعة", "Group owner withdrawals", "amount", False, None),
    ("owner_deposits", "إيداعات / تمويل المالك", "Owner deposits / funding", "amount", False, None),
    ("holding_service_payments", "مدفوعات القابضة للخدمات", "Holding payments for services", "amount", False, None),
    ("service_delivery_cost", "تكلفة تقديم الخدمات", "Cost of providing services", "amount", False, None),
    ("amounts_due_from_clients", "المبالغ المستحقة لدى العملاء", "Amounts due from clients", "amount", False, None),
]

# The Holding's own company record. §7.1: it keeps a report like a subsidiary,
# and §7.4 gives it its own fields, so it needs a company row to hang them on.
HOLDING_COMPANY = {
    "code": "HOLDING",
    "name_ar": "شركة ستارت أب سفير القابضة ذ.م.م",
    "name_en": "START UP SPHERE HOLDING CO W.L.L",
    "country": "مملكة البحرين",
    "sector": "قابضة",
    "currency": "BHD",
    "ownership_percent": "100.00",
    "contact_email": "info@sup-edu.com",
    "contact_phone": "+973 17626990",
}

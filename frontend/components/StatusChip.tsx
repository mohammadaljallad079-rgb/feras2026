"use client";

import { useAuth } from "@/lib/auth";
import { t } from "@/lib/i18n";

/** Status chip vocabulary shared by every module. */
const STATUS_MAP: Record<string, "ok" | "warn" | "bad" | "neutral"> = {
  active: "ok",
  approved: "ok",
  forwarded: "ok",
  completed: "ok",
  won: "ok",
  reviewed: "ok",
  read: "ok",
  converted: "ok",
  draft: "neutral",
  open: "ok",
  new: "warn",
  submitted: "warn",
  returned: "warn",
  under_review: "warn",
  in_progress: "warn",
  awaiting_reply: "warn",
  received: "warn",
  sent: "warn",
  on_leave: "warn",
  deferred: "warn",
  unread: "warn",
  contacted: "warn",
  following_up: "warn",
  not_suitable: "bad",
  closed: "neutral",
  rejected: "bad",
  lost: "bad",
  terminated: "bad",
  overdue: "bad",
  restricted: "bad",
};

const LABELS: Record<string, { ar: string; en: string }> = {
  draft: { ar: "مسودة", en: "Draft" },
  active: { ar: "مفعّلة", en: "Active" },
  closed: { ar: "مغلقة", en: "Closed" },
  open: { ar: "مفتوحة", en: "Open" },
  submitted: { ar: "مُرسل", en: "Submitted" },
  returned: { ar: "مُعاد", en: "Returned" },
  approved: { ar: "معتمد", en: "Approved" },
  forwarded: { ar: "مُرسل للإدارة", en: "Sent to management" },
  reviewed: { ar: "مُراجع", en: "Reviewed" },
  rejected: { ar: "مرفوض", en: "Rejected" },
  under_review: { ar: "قيد المراجعة", en: "Under review" },
  deferred: { ar: "مؤجّل", en: "Deferred" },
  new: { ar: "جديد", en: "New" },
  in_progress: { ar: "قيد التنفيذ", en: "In progress" },
  awaiting_reply: { ar: "بانتظار رد", en: "Awaiting reply" },
  sent: { ar: "مُرسل", en: "Sent" },
  received: { ar: "مستلَم", en: "Received" },
  completed: { ar: "منجز", en: "Completed" },
  contacted: { ar: "تم التواصل", en: "Contacted" },
  following_up: { ar: "قيد المتابعة", en: "Following up" },
  qualified: { ar: "مؤهَّل", en: "Qualified" },
  not_suitable: { ar: "غير مناسب", en: "Not suitable" },
  won: { ar: "مكتسب", en: "Won" },
  lost: { ar: "مفقود", en: "Lost" },
  on_leave: { ar: "في إجازة", en: "On leave" },
  terminated: { ar: "منتهي", en: "Terminated" },
  converted: { ar: "محوَّل", en: "Converted" },
  unread: { ar: "غير مقروء", en: "Unread" },
  read: { ar: "مقروء", en: "Read" },
  low: { ar: "منخفضة", en: "Low" },
  normal: { ar: "عادية", en: "Normal" },
  high: { ar: "عالية", en: "High" },
  urgent: { ar: "عاجلة", en: "Urgent" },
  expense: { ar: "مصروف", en: "Expense" },
  invoice: { ar: "فاتورة", en: "Invoice" },
  commission: { ar: "عمولة", en: "Commission" },
};

/**
 * Table 8 names the report states in full — «مسودة»، «مرسل للمحاسبة»،
 * «أُعيد للتعديل»، «معتمد»، «مرسل للإدارة». The generic `submitted`/`returned`
 * chips belong to other modules (service requests, opportunities), so reports
 * carry their own vocabulary.
 */
export const REPORT_STATUS_LABELS: Record<string, { ar: string; en: string }> = {
  draft: { ar: "مسودة", en: "Draft" },
  submitted: { ar: "مرسل للمحاسبة", en: "Submitted to accounting" },
  returned: { ar: "أُعيد للتعديل", en: "Returned for edit" },
  approved: { ar: "معتمد", en: "Approved" },
  forwarded: { ar: "مرسل للإدارة", en: "Sent to management" },
};

/** The Arabic/English label for a status code, for pickers and plain text. */
export function statusLabel(value: string, locale: string): string {
  return LABELS[value]?.[locale as "ar" | "en"] ?? value;
}

export function StatusChip({ value }: { value: string }) {
  const { locale } = useAuth();
  const tone = STATUS_MAP[value] ?? "neutral";
  const cls =
    tone === "ok" ? "chip-ok" : tone === "warn" ? "chip-warn" : tone === "bad" ? "chip-bad" : "chip-neutral";
  const label = LABELS[value]?.[locale] ?? value;
  return <span className={cls}>{label}</span>;
}

/** Table 8 status chip: the report's own five states, with the shared tones. */
export function ReportStatusChip({ value }: { value: string }) {
  const { locale } = useAuth();
  const tone = STATUS_MAP[value] ?? "neutral";
  const cls =
    tone === "ok" ? "chip-ok" : tone === "warn" ? "chip-warn" : tone === "bad" ? "chip-bad" : "chip-neutral";
  const label = REPORT_STATUS_LABELS[value]?.[locale] ?? value;
  return <span className={cls}>{label}</span>;
}

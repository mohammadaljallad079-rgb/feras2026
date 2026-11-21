"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, loadError, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { Modal } from "@/components/Modal";
import { StatusChip } from "@/components/StatusChip";
import { Toast } from "@/components/Toast";

type ServiceRequest = {
  id: number;
  subject: string;
  body: string | null;
  service_type: string | null;
  company_id: number;
  created_by_id: number;
  recipient_id: number;
  priority: string;
  deadline: string | null;
  status: string;
  created_at: string;
};

type Reply = {
  id: number;
  request_id: number;
  author_id: number;
  body: string;
  is_status_change: boolean;
  new_status: string | null;
  created_at: string;
};

type User = { id: number; full_name_ar: string; full_name_en: string };

// Table 5, «رد / تحديث الحالة»: exactly these four states.
const STATUSES = ["new", "in_progress", "awaiting_reply", "completed"];
// Table 5, «نوع الخدمة *».
const SERVICE_TYPES = [
  { value: "accounting", ar: "محاسبة", en: "Accounting" },
  { value: "design", ar: "تصميم", en: "Design" },
  { value: "study", ar: "دراسة أو مساعدة", en: "Study or help" },
  { value: "marketing", ar: "تسويق واستشارة تسويقية", en: "Marketing and consulting" },
];

// Table 5, «رد / تحديث الحالة»: the four states, labelled for the picker.
const STATUS_LABELS: Record<string, { ar: string; en: string }> = {
  new: { ar: "جديد", en: "New" },
  in_progress: { ar: "قيد التنفيذ", en: "In progress" },
  awaiting_reply: { ar: "بانتظار رد", en: "Awaiting reply" },
  completed: { ar: "مكتمل", en: "Completed" },
};

export default function ServiceRequestsPage() {
  const { locale, can } = useAuth();
  const searchParams = useSearchParams();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [rows, setRows] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [thread, setThread] = useState<Reply[]>([]);
  const [reply, setReply] = useState("");
  const [newStatus, setNewStatus] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({ subject: "", body: "", service_type: "accounting", company_id: "", recipient_id: "", priority: "normal", deadline: "" });
  const [formOpen, setFormOpen] = useState(false);
  // Table 6 R2 «رد / تحديث الحالة»: a window with «الرد *» mandatory and an
  // optional status, applied to the request whose thread is open.
  const [replyOpen, setReplyOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.get<ServiceRequest[]>("/api/v1/service-requests"));
    } catch (e) {
      setError(loadError(e, locale));
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
    api.get<User[]>("/api/v1/users/directory").then(setUsers).catch(() => undefined);
  }, [load]);

  // The AI assistant's source record links here as ?open=<id>; open that
  // request's thread and bring it into view so the link lands on the record.
  const deepLink = searchParams.get("open");
  useEffect(() => {
    if (!deepLink || rows.length === 0) return;
    const id = Number(deepLink);
    void openThread(id);
    document.getElementById(`service-request-${id}`)?.scrollIntoView({ block: "start" });
    // openThread is stable for this purpose; re-running on rows only would reopen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deepLink, rows.length]);

  async function openThread(id: number) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    setThread(await api.get<Reply[]>(`/api/v1/service-requests/${id}/thread`).catch(() => []));
  }

  async function sendReply(id: number) {
    if (!reply.trim()) return;
    await api.post(`/api/v1/service-requests/${id}/replies`, {
      body: reply || (locale === "ar" ? "تحديث الحالة" : "Status update"),
      new_status: newStatus || null,
    });
    setReply("");
    setNewStatus("");
    setReplyOpen(false);
    setMessage(locale === "ar" ? "أُضيف الرد إلى سلسلة الطلب." : "The reply was added to the request thread.");
    setThread(await api.get<Reply[]>(`/api/v1/service-requests/${id}/thread`).catch(() => []));
    await load();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/service-requests", {
        ...form,
        service_type: form.service_type,
        company_id: Number(form.company_id),
        // Table 5: only the owner chooses the receiving specialist; a manager
        // leaves it empty and the server routes by service type.
        recipient_id: form.recipient_id ? Number(form.recipient_id) : null,
        deadline: form.deadline || null,
      });
      setForm({ subject: "", body: "", service_type: "accounting", company_id: "", recipient_id: "", priority: "normal", deadline: "" });
      setFormOpen(false);
      setMessage(locale === "ar" ? "تم إنشاء الطلب." : "Request created.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر إنشاء الطلب." : "Could not create the request.");
    }
  }

  const companyName = (id: number) =>
    companies.find((c) => c.id === id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? id;
  const userName = (id: number) => {
    const u = users.find((x) => x.id === id);
    return u ? (locale === "ar" ? u.full_name_ar : u.full_name_en) : `#${id}`;
  };

  return (
    <section>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-title">{locale === "ar" ? "طلبات الخدمات" : "Service requests"}</h1>
          <p className="muted">
            {locale === "ar"
              ? "الطلبات تُوجَّه للمختص، ويختار المالك المستلم عند إنشاء طلبه."
              : "Requests go to a specialist; the owner chooses the recipient when creating the request."}
          </p>
        </div>
        {can("service:create") && (
          <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
            {locale === "ar" ? "طلب خدمة جديد" : "New service request"}
          </button>
        )}
      </header>

      {formOpen && (
        <Modal
          title={locale === "ar" ? "طلب خدمة جديد" : "New service request"}
          onClose={() => setFormOpen(false)}
        >
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="label" htmlFor="sr-subject">{locale === "ar" ? "الموضوع" : "Subject"}</label>
              <input id="sr-subject" className="input" required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="sr-service-type">{locale === "ar" ? "نوع الخدمة" : "Service type"}<span aria-hidden="true"> *</span></label>
              <select id="sr-service-type" className="input" required value={form.service_type} onChange={(e) => setForm({ ...form, service_type: e.target.value })}>
                {SERVICE_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>{locale === "ar" ? s.ar : s.en}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="sr-company">{locale === "ar" ? "الشركة" : "Company"}</label>
              <select id="sr-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
                <option value="">—</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>
                ))}
              </select>
            </div>
            {can("service:assign") && (
              <div>
                <label className="label" htmlFor="sr-recipient">
                  {locale === "ar" ? "المختص المستلم" : "Receiving specialist"}
                <span aria-hidden="true"> *</span></label>
                {/* Table 6 R1: «للمالك: المختص المستلم *» — mandatory for the owner,
                    while a company manager's request is routed by service type. */}
                <select id="sr-recipient" className="input" required value={form.recipient_id} onChange={(e) => setForm({ ...form, recipient_id: e.target.value })}>
                  <option value="">{locale === "ar" ? "— اختر المختص —" : "— Choose a specialist —"}</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{locale === "ar" ? u.full_name_ar : u.full_name_en}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="label" htmlFor="sr-priority">{locale === "ar" ? "الأولوية" : "Priority"}</label>
              <select id="sr-priority" className="input" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                <option value="normal">{locale === "ar" ? "عادية" : "Normal"}</option>
                <option value="urgent">{locale === "ar" ? "عاجلة" : "Urgent"}</option>
              </select>
            </div>
            <div className="sm:col-span-3">
              <label className="label" htmlFor="sr-body">{locale === "ar" ? "وصف الاحتياج" : "Description of the need"}</label>
              <textarea id="sr-body" className="input min-h-20" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
            </div>
            <div>
              {/* Table 6: «الموعد المطلوب» — the date the requester needs it by. */}
              <label className="label" htmlFor="sr-deadline">{locale === "ar" ? "الموعد المطلوب" : "Required date"}</label>
              <input id="sr-deadline" type="date" className="input" dir="ltr" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
            </div>
            <div className="flex items-end justify-end gap-2 sm:col-span-3">
              <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ" : "Save"}</button>
            </div>
          </form>
        </Modal>
      )}

      {replyOpen && openId !== null && can("service:reply") && (
        <Modal
          title={locale === "ar" ? "رد / تحديث الحالة" : "Reply / update status"}
          onClose={() => setReplyOpen(false)}
        >
          <div className="grid gap-3">
            <div>
              <label className="label" htmlFor="sr-reply-body">
                {locale === "ar" ? "الرد" : "Reply"}
                <span aria-hidden="true"> *</span>
              </label>
              <textarea
                id="sr-reply-body"
                className="input min-h-20"
                required
                value={reply}
                onChange={(e) => setReply(e.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="sr-reply-status">{locale === "ar" ? "الحالة" : "Status"}</label>
              <select id="sr-reply-status" className="input" value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                <option value="">{locale === "ar" ? "بلا تغيير" : "No change"}</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]?.[locale === "ar" ? "ar" : "en"] ?? s}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setReplyOpen(false)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={!reply.trim()}
                onClick={() => void sendReply(openId)}
              >
                {locale === "ar" ? "إرسال" : "Send"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <ul className="space-y-4">
          {rows.map((r) => (
            <li key={r.id} id={`service-request-${r.id}`} className="card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="section-title">{r.subject}</h2>
                  <p className="muted">
                    {companyName(r.company_id)} · {locale === "ar" ? "المستلم" : "Recipient"}: {userName(r.recipient_id)}
                    {r.service_type
                      ? ` · ${locale === "ar" ? "نوع الخدمة" : "Service type"}: ${
                          SERVICE_TYPES.find((s) => s.value === r.service_type)?.[locale === "ar" ? "ar" : "en"] ?? r.service_type
                        }`
                      : ""}
                  </p>
                  {r.body && <p className="mt-2">{r.body}</p>}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusChip value={r.priority} />
                  <StatusChip value={r.status} />
                  <span className="muted tabular-nums" dir="ltr">{r.deadline ?? "—"}</span>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button type="button" className="btn-ghost" onClick={() => void openThread(r.id)} aria-expanded={openId === r.id}>
                  {locale === "ar" ? "سجل الردود" : "Reply thread"}
                </button>
              </div>

              {openId === r.id && (
                <div className="mt-3 border-t border-line pt-3">
                  <ul className="space-y-2">
                    {thread.length === 0 && <li className="muted">{locale === "ar" ? "لا ردود بعد." : "No replies yet."}</li>}
                    {thread.map((t) => (
                      <li key={t.id} className="rounded-control bg-pearl p-3">
                        <p className="text-secondary muted">
                          {userName(t.author_id)} · <span dir="ltr">{t.created_at.slice(0, 16).replace("T", " ")}</span>
                        </p>
                        <p>{t.body}</p>
                        {t.is_status_change && t.new_status && (
                          <p className="mt-1">
                            <StatusChip value={t.new_status} />
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                  {can("service:reply") && (
                    <button
                      type="button"
                      className="btn-primary mt-3"
                      onClick={() => {
                        setReply("");
                        setNewStatus("");
                        setReplyOpen(true);
                      }}
                    >
                      {locale === "ar" ? "رد / تحديث الحالة" : "Reply / update status"}
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </DataStates>
      <Toast message={message} />
    </section>
  );
}

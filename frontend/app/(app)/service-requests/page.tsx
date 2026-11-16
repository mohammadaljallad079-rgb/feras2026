"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

type ServiceRequest = {
  id: number;
  subject: string;
  body: string | null;
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

const STATUSES = ["new", "in_progress", "answered", "closed"];

export default function ServiceRequestsPage() {
  const { locale, can } = useAuth();
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
  const [form, setForm] = useState({ subject: "", body: "", company_id: "", recipient_id: "", priority: "normal", deadline: "" });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.get<ServiceRequest[]>("/api/v1/service-requests"));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
    api.get<User[]>("/api/v1/users").then(setUsers).catch(() => undefined);
  }, [load]);

  async function openThread(id: number) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    setThread(await api.get<Reply[]>(`/api/v1/service-requests/${id}/thread`).catch(() => []));
  }

  async function sendReply(id: number) {
    if (!reply && !newStatus) return;
    await api.post(`/api/v1/service-requests/${id}/replies`, {
      body: reply || (locale === "ar" ? "تحديث الحالة" : "Status update"),
      new_status: newStatus || null,
    });
    setReply("");
    setNewStatus("");
    setThread(await api.get<Reply[]>(`/api/v1/service-requests/${id}/thread`).catch(() => []));
    await load();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/service-requests", {
        ...form,
        company_id: Number(form.company_id),
        recipient_id: Number(form.recipient_id),
        deadline: form.deadline || null,
      });
      setForm({ subject: "", body: "", company_id: "", recipient_id: "", priority: "normal", deadline: "" });
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
      <header className="mb-4">
        <h1 className="page-title">{locale === "ar" ? "طلبات الخدمات" : "Service requests"}</h1>
        <p className="muted">
          {locale === "ar"
            ? "الطلبات تُوجَّه للمختص، ويختار المالك المستلم عند إنشاء طلبه."
            : "Requests go to a specialist; the owner chooses the recipient when creating the request."}
        </p>
      </header>

      {message && (
        <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">
          {message}
        </p>
      )}

      {can("service:create") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="label" htmlFor="sr-subject">{locale === "ar" ? "الموضوع" : "Subject"}</label>
            <input id="sr-subject" className="input" required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
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
          <div>
            <label className="label" htmlFor="sr-recipient">{locale === "ar" ? "المستلم" : "Recipient"}</label>
            <select id="sr-recipient" className="input" required value={form.recipient_id} onChange={(e) => setForm({ ...form, recipient_id: e.target.value })}>
              <option value="">—</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{locale === "ar" ? u.full_name_ar : u.full_name_en}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="sr-priority">{locale === "ar" ? "الأولوية" : "Priority"}</label>
            <select id="sr-priority" className="input" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option value="low">{locale === "ar" ? "منخفضة" : "Low"}</option>
              <option value="normal">{locale === "ar" ? "عادية" : "Normal"}</option>
              <option value="high">{locale === "ar" ? "عالية" : "High"}</option>
              <option value="urgent">{locale === "ar" ? "عاجلة" : "Urgent"}</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="sr-deadline">{locale === "ar" ? "الموعد" : "Deadline"}</label>
            <input id="sr-deadline" type="date" className="input" dir="ltr" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          </div>
          <div className="sm:col-span-3">
            <label className="label" htmlFor="sr-body">{locale === "ar" ? "التفاصيل" : "Details"}</label>
            <textarea id="sr-body" className="input min-h-20" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div>
            <button type="submit" className="btn-primary">{locale === "ar" ? "إنشاء طلب" : "Create request"}</button>
          </div>
        </form>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <ul className="space-y-4">
          {rows.map((r) => (
            <li key={r.id} className="card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="section-title">{r.subject}</h2>
                  <p className="muted">
                    {companyName(r.company_id)} · {locale === "ar" ? "المستلم" : "Recipient"}: {userName(r.recipient_id)}
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
                    <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                      <input
                        className="input"
                        placeholder={locale === "ar" ? "رد…" : "Reply…"}
                        value={reply}
                        onChange={(e) => setReply(e.target.value)}
                      />
                      <select className="input w-auto" value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                        <option value="">{locale === "ar" ? "تحديث الحالة" : "Update status"}</option>
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                      <button type="button" className="btn-primary" onClick={() => void sendReply(r.id)}>
                        {locale === "ar" ? "إرسال" : "Send"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </DataStates>
    </section>
  );
}

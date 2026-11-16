"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Person = { id: number; full_name_ar: string; full_name_en: string };

type AdvisorMessage = {
  id: number;
  author_id: number;
  recipient_id: number;
  category: string;
  subject: string;
  body: string;
  company_id: number | null;
  status: string;
  read_at: string | null;
  created_at: string;
};

export default function AdvisorPage() {
  const { locale, can } = useAuth();
  const [rows, setRows] = useState<AdvisorMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState({ recipient_id: "", category: "recommendation", subject: "", body: "", company_id: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<AdvisorMessage[]>("/api/v1/advisor/messages"));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Person[]>("/api/v1/users").then(setPeople).catch(() => undefined);
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/advisor/messages", {
        ...form,
        recipient_id: Number(form.recipient_id),
        company_id: form.company_id ? Number(form.company_id) : null,
      });
      setForm({ recipient_id: "", category: "recommendation", subject: "", body: "", company_id: "" });
      setMessage(locale === "ar" ? "تم الإرسال." : "Sent.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر الإرسال." : "Could not send.");
    }
  }

  async function markRead(id: number) {
    setMessage(null);
    try {
      await api.post(`/api/v1/advisor/messages/${id}/read`);
      await load();
    } catch {
      setMessage(locale === "ar" ? "فشل الإجراء." : "The action failed.");
    }
  }

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{locale === "ar" ? "المستشار الخارجي" : "External advisor"}</h1>
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      {can("advisor:send") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="adv-recipient">{locale === "ar" ? "المستلم" : "Recipient"}</label>
            <select id="adv-recipient" className="input" required value={form.recipient_id} onChange={(e) => setForm({ ...form, recipient_id: e.target.value })}>
              <option value="">—</option>
              {people.map((u) => (
                <option key={u.id} value={u.id}>{locale === "ar" ? u.full_name_ar : u.full_name_en}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="adv-category">{locale === "ar" ? "التصنيف" : "Category"}</label>
            <select id="adv-category" className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="recommendation">{locale === "ar" ? "توصية" : "Recommendation"}</option>
              <option value="report">{locale === "ar" ? "تقرير" : "Report"}</option>
              <option value="suggestion">{locale === "ar" ? "اقتراح" : "Suggestion"}</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="adv-subject">{locale === "ar" ? "الموضوع" : "Subject"}</label>
            <input id="adv-subject" className="input" required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="adv-company">{locale === "ar" ? "الشركة (اختياري)" : "Company (optional)"}</label>
            <select id="adv-company" className="input" value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">—</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="adv-body">{locale === "ar" ? "النص" : "Body"}</label>
            <textarea id="adv-body" className="input min-h-20" required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div>
            <button type="submit" className="btn-primary">{locale === "ar" ? "إرسال" : "Send"}</button>
          </div>
        </form>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[640px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "النوع" : "Type"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "العنوان" : "Title"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النص" : "Text"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إلى" : "To"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="p-3">{r.category}</td>
                  <td className="p-3">{r.subject}</td>
                  <td className="p-3">{r.body}</td>
                  <td className="p-3">
                    {(() => {
                      const u = people.find((x) => x.id === r.recipient_id);
                      return u ? (locale === "ar" ? u.full_name_ar : u.full_name_en) : `#${r.recipient_id}`;
                    })()}
                  </td>
                  <td className="p-3"><StatusChip value={r.status} /></td>
                  <td className="p-3">
                    {r.status !== "read" && (
                      <button type="button" className="btn-ghost" onClick={() => void markRead(r.id)}>
                        {locale === "ar" ? "تحديد كمقروء" : "Mark as read"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>
    </section>
  );
}

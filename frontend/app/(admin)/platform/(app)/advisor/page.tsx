"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { DataStates } from "@/components/DataStates";
import { Modal } from "@/components/Modal";
import { Toast } from "@/components/Toast";
import { api, loadError, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Person = { id: number; full_name_ar: string; full_name_en: string };

// §5.7 / Table 5: the three categories, labelled for the «النوع» column.
const CATEGORY_LABELS: Record<string, { ar: string; en: string }> = {
  recommendation: { ar: "توصية", en: "Recommendation" },
  report: { ar: "تقرير", en: "Report" },
  suggestion: { ar: "اقتراح", en: "Suggestion" },
};

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
  const searchParams = useSearchParams();
  // §5.7: the advisor dashboard's three buttons deep-link here with the chosen
  // category, so the form opens ready for that action.
  const initialCategory = (() => {
    const c = searchParams.get("category");
    return c === "report" || c === "suggestion" ? c : "recommendation";
  })();
  const [rows, setRows] = useState<AdvisorMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  // A separate, unnarrowed list for rendering the «إلى» column: the picker list
  // is narrowed per category, so a report addressed to the Owner would otherwise
  // fall back to «#id» once the form switches to «recommendation».
  const [directory, setDirectory] = useState<Person[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState({ recipient_id: "", category: initialCategory, subject: "", body: "", company_id: "" });
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<AdvisorMessage[]>("/api/v1/advisor/messages"));
    } catch (e) {
      setError(loadError(e, locale));
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
    api.get<Person[]>("/api/v1/users/directory").then(setDirectory).catch(() => undefined);
  }, [load]);

  // Table 5: a recommendation and a suggestion go to the Business Developer; a
  // report goes to the Owner or the Business Developer. The picker offers only
  // those recipients, and the server refuses anyone else.
  const recipientRoles = form.category === "report" ? "owner,business_developer" : "business_developer";
  useEffect(() => {
    api
      .get<Person[]>(`/api/v1/users/directory?role=${recipientRoles}`)
      .then((list) => {
        setPeople(list);
        setForm((f) => (list.some((u) => String(u.id) === f.recipient_id) ? f : { ...f, recipient_id: "" }));
      })
      .catch(() => undefined);
  }, [recipientRoles]);

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
      setFormOpen(false);
      setMessage(locale === "ar" ? "تم الإرسال." : "Sent.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر الإرسال." : "Could not send.");
    }
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{locale === "ar" ? "المستشار الخارجي" : "External advisor"}</h1>
        {can("advisor:submit") && (
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={() => { setForm((f) => ({ ...f, category: "recommendation" })); setFormOpen(true); }}>
              {locale === "ar" ? "إضافة توصية" : "Add recommendation"}
            </button>
            <button type="button" className="btn-primary" onClick={() => { setForm((f) => ({ ...f, category: "report" })); setFormOpen(true); }}>
              {locale === "ar" ? "تقرير" : "Report"}
            </button>
            <button type="button" className="btn-primary" onClick={() => { setForm((f) => ({ ...f, category: "suggestion" })); setFormOpen(true); }}>
              {locale === "ar" ? "اقتراح" : "Suggestion"}
            </button>
          </div>
        )}
      </header>

      {formOpen && can("advisor:submit") && (
        <Modal
          title={
            form.category === "report"
              ? locale === "ar" ? "تقرير" : "Report"
              : form.category === "suggestion"
                ? locale === "ar" ? "اقتراح" : "Suggestion"
                : locale === "ar" ? "إضافة توصية" : "Add recommendation"
          }
          onClose={() => setFormOpen(false)}
        >
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="adv-recipient">{locale === "ar" ? "المستلم" : "Recipient"}</label>
            <select id="adv-recipient" className="input" required value={form.recipient_id} onChange={(e) => setForm({ ...form, recipient_id: e.target.value })}>
              <option value="">—</option>
              {people.map((u) => (
                <option key={u.id} value={u.id}>{locale === "ar" ? u.full_name_ar : u.full_name_en}</option>
              ))}
            </select>
          </div>
          {/* §5.7: the advisor has three actions — a recommendation (to the
              Business Developer), a report (to the Owner or Business Developer)
              and a suggestion (to the Business Developer). The chosen button
              sets the category and narrows the recipient picker below. */}
          <div className="sm:col-span-2">
            <span className="label">{locale === "ar" ? "الإجراء" : "Action"}</span>
            <div className="flex flex-wrap gap-2" role="group" aria-label={locale === "ar" ? "الإجراء" : "Action"}>
              {[
                { value: "recommendation", ar: "إضافة توصية", en: "Add a recommendation" },
                { value: "report", ar: "تقرير", en: "Report" },
                { value: "suggestion", ar: "اقتراح", en: "Suggestion" },
              ].map((c) => (
                <button
                  key={c.value}
                  type="button"
                  aria-pressed={form.category === c.value}
                  className={form.category === c.value ? "btn-primary" : "btn-ghost"}
                  onClick={() => setForm((f) => ({ ...f, category: c.value, recipient_id: "" }))}
                >
                  {locale === "ar" ? c.ar : c.en}
                </button>
              ))}
            </div>
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
            <label className="label" htmlFor="adv-body">{locale === "ar" ? "النص" : "Body"}<span aria-hidden="true"> *</span></label>
            <textarea id="adv-body" className="input min-h-20" required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div className="flex justify-end gap-2 sm:col-span-2">
            <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>
              {locale === "ar" ? "إلغاء" : "Cancel"}
            </button>
            <button type="submit" className="btn-primary">{locale === "ar" ? "إرسال" : "Send"}</button>
          </div>
        </form>
        </Modal>
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
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-line last:border-0"
                  onClick={() => {
                    if (r.status !== "read") void api.post(`/api/v1/advisor/messages/${r.id}/read`).then(load).catch(() => undefined);
                  }}
                >
                  <td className="p-3">{(CATEGORY_LABELS[r.category] ?? { ar: r.category, en: r.category })[locale]}</td>
                  <td className="p-3">{r.subject}</td>
                  <td className="p-3">{r.body}</td>
                  <td className="p-3">
                    {(() => {
                      const u = directory.find((x) => x.id === r.recipient_id) ?? people.find((x) => x.id === r.recipient_id);
                      return u ? (locale === "ar" ? u.full_name_ar : u.full_name_en) : `#${r.recipient_id}`;
                    })()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>
      <Toast message={message} />
    </section>
  );
}

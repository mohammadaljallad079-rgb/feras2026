"use client";

import { useCallback, useEffect, useState } from "react";
import { Column } from "@/components/ResourceTable";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Opportunity = {
  id: number;
  title: string;
  company_id: number;
  description: string | null;
  estimated_value: string | null;
  currency: string;
  status: string;
  created_by_id: number;
  submitted_at: string | null;
  decided_by_id: number | null;
  decided_at: string | null;
  decision_note: string | null;
  created_at: string;
};

export default function OpportunitiesPage() {
  const { locale, can } = useAuth();
  const [rows, setRows] = useState<Opportunity[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", company_id: "", description: "", estimated_value: "", currency: "SAR" });
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Opportunity[]>("/api/v1/opportunities"));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/opportunities", { ...form, company_id: Number(form.company_id) });
      setForm({ title: "", company_id: "", description: "", estimated_value: "", currency: "SAR" });
      setMessage(locale === "ar" ? "تم إنشاء الفرصة." : "Opportunity created.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر إنشاء الفرصة." : "Could not create the opportunity.");
    }
  }

  async function act(id: number, verb: "submit" | "decision", body?: unknown) {
    setMessage(null);
    try {
      await api.post(`/api/v1/opportunities/${id}/${verb}`, body);
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(err.status === 403 ? (locale === "ar" ? "لا تملك صلاحية القرار." : "You are not permitted to decide.") : locale === "ar" ? "فشل الإجراء." : "The action failed.");
    }
  }

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{locale === "ar" ? "الفرص" : "Opportunities"}</h1>
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      {can("opportunity:create") && (
        <form onSubmit={create} className="card mb-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="opp-title">{locale === "ar" ? "العنوان" : "Title"}</label>
            <input id="opp-title" className="input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="opp-company">{locale === "ar" ? "الشركة" : "Company"}</label>
            <select id="opp-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">—</option>
              {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="opp-value">{locale === "ar" ? "القيمة التقديرية" : "Estimated value"}</label>
            <input id="opp-value" className="input" dir="ltr" inputMode="decimal" value={form.estimated_value} onChange={(e) => setForm({ ...form, estimated_value: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="opp-currency">{locale === "ar" ? "العملة" : "Currency"}</label>
            <input id="opp-currency" className="input" dir="ltr" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="opp-desc">{locale === "ar" ? "الوصف" : "Description"}</label>
            <input id="opp-desc" className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <button type="submit" className="btn-primary">{locale === "ar" ? "إضافة" : "Add"}</button>
          </div>
        </form>
      )}

      {can("opportunity:decide") && (
        <div className="card mb-4">
          <label className="label" htmlFor="decision-note">{locale === "ar" ? "ملاحظة القرار" : "Decision note"}</label>
          <input id="decision-note" className="input" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[720px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "العنوان" : "Title"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الشركة" : "Company"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "القيمة" : "Value"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "تاريخ القرار" : "Decided"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="p-3">{r.title}</td>
                  <td className="p-3">{companies.find((c) => c.id === r.company_id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? r.company_id}</td>
                  <td className="p-3 tabular-nums" dir="ltr">{r.estimated_value ? `${r.estimated_value} ${r.currency}` : "—"}</td>
                  <td className="p-3"><StatusChip value={r.status} /></td>
                  <td className="p-3" dir="ltr">{r.decided_at ? r.decided_at.slice(0, 10) : "—"}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      {r.status === "draft" && can("opportunity:create") && (
                        <button type="button" className="btn-ghost" onClick={() => void act(r.id, "submit")}>
                          {locale === "ar" ? "إرسال للمالك" : "Submit to owner"}
                        </button>
                      )}
                      {["submitted", "under_review"].includes(r.status) && can("opportunity:decide") && (
                        <>
                          <button type="button" className="btn-gold" onClick={() => void act(r.id, "decision", { decision: "approved", note })}>
                            {locale === "ar" ? "اعتماد" : "Approve"}
                          </button>
                          <button type="button" className="btn-ghost" onClick={() => void act(r.id, "decision", { decision: "rejected", note })}>
                            {locale === "ar" ? "رفض" : "Reject"}
                          </button>
                          <button type="button" className="btn-ghost" onClick={() => void act(r.id, "decision", { decision: "deferred", note })}>
                            {locale === "ar" ? "تأجيل" : "Defer"}
                          </button>
                        </>
                      )}
                    </div>
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

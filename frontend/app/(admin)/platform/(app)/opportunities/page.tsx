"use client";

import { useCallback, useEffect, useState } from "react";
import { Column } from "@/components/ResourceTable";
import { DataStates } from "@/components/DataStates";
import { Modal } from "@/components/Modal";
import { StatusChip } from "@/components/StatusChip";
import { Toast } from "@/components/Toast";
import { api, loadError, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Opportunity = {
  id: number;
  title: string;
  company_id: number;
  description: string | null;
  country: string | null;
  attachment_file_id: number | null;
  attachment_name: string | null;
  source: string | null;
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

// Table 5 / Table 12: the country choices named in the brief.
const COUNTRIES = [
  { value: "البحرين", ar: "البحرين", en: "Bahrain" },
  { value: "السعودية", ar: "السعودية", en: "Saudi Arabia" },
  { value: "الإمارات", ar: "الإمارات", en: "UAE" },
  { value: "الكويت", ar: "الكويت", en: "Kuwait" },
  { value: "قطر", ar: "قطر", en: "Qatar" },
  { value: "عُمان", ar: "عُمان", en: "Oman" },
  { value: "الأردن", ar: "الأردن", en: "Jordan" },
];

export default function OpportunitiesPage() {
  const { locale, can } = useAuth();
  const [rows, setRows] = useState<Opportunity[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", company_id: "", description: "", country: "" });
  const [studyFile, setStudyFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  // Table 6 R7: «رفض / تأجيل — السبب * (إلزامي)» opens a window holding only
  // the mandatory reason; the decision buttons stay windowless (R6).
  const [decision, setDecision] = useState<{ id: number; verb: "rejected" | "deferred" } | null>(null);
  const [reason, setReason] = useState("");
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Opportunity[]>("/api/v1/opportunities"));
    } catch (e) {
      setError(loadError(e, locale));
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
      // Table 5: the study file is uploaded first, then linked to the draft.
      let attachment_file_id: number | null = null;
      if (studyFile) {
        const body = new FormData();
        body.append("file", studyFile);
        const stored = await api.upload<{ id: number }>("/api/v1/files", body);
        attachment_file_id = stored.id;
      }
      await api.post("/api/v1/opportunities", {
        ...form,
        company_id: Number(form.company_id),
        country: form.country || null,
        attachment_file_id,
      });
      setForm({ title: "", company_id: "", description: "", country: "" });
      setStudyFile(null);
      setFormOpen(false);
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
      // Table 5: a decision records itself only — approving never triggers
      // execution or publishing — so the toast says exactly that.
      setMessage(
        verb === "decision"
          ? locale === "ar"
            ? "سُجل القرار. لا تحويل تلقائي للتنفيذ."
            : "Decision recorded. No automatic execution."
          : locale === "ar"
            ? "تم إرسال الفرصة للمالك."
            : "Opportunity submitted to the owner.",
      );
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(err.status === 403 ? (locale === "ar" ? "لا تملك صلاحية القرار." : "You are not permitted to decide.") : locale === "ar" ? "فشل الإجراء." : "The action failed.");
    }
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">
          {locale === "ar" ? "الفرص التجارية والاستثمارية" : "Commercial and investment opportunities"}
        </h1>
        {can("opportunity:create") && (
          <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
            {locale === "ar" ? "فرصة جديدة" : "New opportunity"}
          </button>
        )}
      </header>
      <p className="muted mb-4">
        {locale === "ar"
          ? "الاعتماد لا ينشئ مشروعاً: يسجّل القرار ووقته فقط."
          : "Approval does not create a project: it records the decision and its timestamp only."}
      </p>

      {formOpen && (
        <Modal
          title={locale === "ar" ? "فرصة جديدة" : "New opportunity"}
          onClose={() => setFormOpen(false)}
        >
          <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="opp-title">{locale === "ar" ? "الموضوع" : "Topic"}</label>
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
              <label className="label" htmlFor="opp-country">{locale === "ar" ? "الدولة" : "Country"}<span aria-hidden="true"> *</span></label>
              <select id="opp-country" className="input" required value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}>
                <option value="">—</option>
                {COUNTRIES.map((c) => (<option key={c.value} value={c.value}>{locale === "ar" ? c.ar : c.en}</option>))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="label" htmlFor="opp-desc">{locale === "ar" ? "وصف مختصر" : "Short description"}</label>
              <input id="opp-desc" className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="opp-file">{locale === "ar" ? "ملف الدراسة" : "Study file"}</label>
              <input id="opp-file" type="file" className="input" onChange={(e) => setStudyFile(e.target.files?.[0] ?? null)} />
            </div>
            <div className="flex items-end justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ مسودة" : "Save draft"}</button>
            </div>
          </form>
        </Modal>
      )}


      {decision && (
        <Modal
          title={decision.verb === "rejected" ? (locale === "ar" ? "رفض الفرصة" : "Reject the opportunity") : locale === "ar" ? "تأجيل الفرصة" : "Defer the opportunity"}
          onClose={() => setDecision(null)}
        >
          <div className="grid gap-3">
            <div>
              <label className="label" htmlFor="decision-reason">
                {locale === "ar" ? "السبب" : "Reason"}
                <span aria-hidden="true"> *</span>
              </label>
              <textarea
                id="decision-reason"
                className="input min-h-20"
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              {reason.trim().length < 3 && (
                <p className="muted mt-1">{locale === "ar" ? "السبب إلزامي." : "A reason is required."}</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setDecision(null)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button
                type="button"
                className={decision.verb === "rejected" ? "btn-bad" : "btn-primary"}
                disabled={reason.trim().length < 3}
                onClick={() => {
                  const pending = decision;
                  setDecision(null);
                  void act(pending.id, "decision", { decision: pending.verb, note: reason });
                }}
              >
                {locale === "ar" ? "حفظ" : "Save"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[720px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "الموضوع" : "Topic"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الدولة" : "Country"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الملف" : "File"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "المصدر" : "Source"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "السبب" : "Reason"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="p-3">{r.title}</td>
                  <td className="p-3">{r.country ?? "—"}</td>
                  <td className="p-3">
                    {r.attachment_file_id ? (
                      <button type="button" className="btn-ghost" onClick={() => void api.download(`/api/v1/files/${r.attachment_file_id}/download`, r.attachment_name ?? `opportunity-${r.id}`)}>
                        {locale === "ar" ? "تنزيل الملف" : "Download file"}
                      </button>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="p-3">{r.source ?? "—"}</td>
                  <td className="p-3"><StatusChip value={r.status} /></td>
                  <td className="p-3">{r.decision_note ?? "—"}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      {r.status === "draft" && can("opportunity:create") && (
                        <button type="button" className="btn-ghost" onClick={() => void act(r.id, "submit")}>
                          {locale === "ar" ? "إرسال للمالك" : "Submit to owner"}
                        </button>
                      )}
                      {["submitted", "under_review"].includes(r.status) && can("opportunity:decide") && (
                        <>
                          <button type="button" className="btn-ghost" onClick={() => void act(r.id, "decision", { decision: "under_review", note })}>
                            {locale === "ar" ? "قيد المراجعة" : "Under review"}
                          </button>
                          <button type="button" className="btn-gold" onClick={() => void act(r.id, "decision", { decision: "approved", note })}>
                            {locale === "ar" ? "اعتماد" : "Approve"}
                          </button>
                          <button
                            type="button"
                            className="btn-bad"
                            onClick={() => {
                              setReason("");
                              setDecision({ id: r.id, verb: "rejected" });
                            }}
                          >
                            {locale === "ar" ? "رفض" : "Reject"}
                          </button>
                          <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => {
                              setReason("");
                              setDecision({ id: r.id, verb: "deferred" });
                            }}
                          >
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
      <Toast message={message} />
    </section>
  );
}

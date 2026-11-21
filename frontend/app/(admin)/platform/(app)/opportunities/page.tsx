"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  category: string | null;
  requested_from_group: string | null;
  investment_amount: string | null;
  expected_return: string | null;
  expected_return_pct: string | null;
  cashflow_note: string | null;
  risk_level: string | null;
  risk_note: string | null;
  recommendation: string | null;
  next_step_owner_id: number | null;
  next_step_owner_name: string | null;
  next_step_on: string | null;
  actual_return: string | null;
  actual_note: string | null;
  created_at: string;
};

type Person = { id: number; full_name_ar: string; full_name_en: string };

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

const CATEGORIES = [
  { value: "commercial", ar: "تجارية", en: "Commercial" },
  { value: "investment", ar: "استثمارية", en: "Investment" },
];

const RISKS = [
  { value: "low", ar: "منخفضة", en: "Low" },
  { value: "medium", ar: "متوسطة", en: "Medium" },
  { value: "high", ar: "مرتفعة", en: "High" },
];

const BLANK_FILE = {
  category: "",
  requested_from_group: "",
  investment_amount: "",
  expected_return: "",
  expected_return_pct: "",
  cashflow_note: "",
  risk_level: "",
  risk_note: "",
  recommendation: "",
};

export default function OpportunitiesPage() {
  const { locale, can } = useAuth();
  const ar = locale === "ar";
  const [rows, setRows] = useState<Opportunity[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [tone, setTone] = useState<"ok" | "bad">("ok");
  const [form, setForm] = useState({ title: "", company_id: "", description: "", country: "" });
  const [studyFile, setStudyFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  // Table 6 R7: «رفض / تأجيل — السبب * (إلزامي)» opens a window holding only
  // the mandatory reason; the decision buttons stay windowless (R6).
  const [decision, setDecision] = useState<{ id: number; verb: "rejected" | "deferred" } | null>(null);
  const [reason, setReason] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  // The analysis file and the realised outcome open beside the record rather
  // than in a column, so the six columns §5.1 prints stay untouched.
  const [editing, setEditing] = useState<Opportunity | null>(null);
  const [fileForm, setFileForm] = useState({ ...BLANK_FILE });
  const [outcomeForm, setOutcomeForm] = useState({ actual_return: "", actual_note: "" });
  const [followUp, setFollowUp] = useState<{ id: number } | null>(null);
  const [followForm, setFollowForm] = useState({ next_step_owner_id: "", next_step_on: "" });
  const [chosen, setChosen] = useState<number[]>([]);
  const [comparing, setComparing] = useState<Opportunity[] | null>(null);

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
    api.get<Person[]>("/api/v1/users/directory").then(setPeople).catch(() => undefined);
  }, [load]);

  function say(text: string, kind: "ok" | "bad" = "ok") {
    setMessage(text);
    setTone(kind);
  }

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
      say(ar ? "تم إنشاء الفرصة." : "Opportunity created.");
      await load();
    } catch {
      say(ar ? "تعذّر إنشاء الفرصة." : "Could not create the opportunity.", "bad");
    }
  }

  async function act(id: number, verb: "submit" | "decision", body?: unknown) {
    setMessage(null);
    try {
      await api.post(`/api/v1/opportunities/${id}/${verb}`, body);
      // Table 5: a decision records itself only — approving never triggers
      // execution or publishing — so the toast says exactly that.
      say(
        verb === "decision"
          ? ar
            ? "سُجل القرار. لا تحويل تلقائي للتنفيذ."
            : "Decision recorded. No automatic execution."
          : ar
            ? "تم إرسال الفرصة للمالك."
            : "Opportunity submitted to the owner.",
      );
      await load();
    } catch (e) {
      const err = e as { status: number };
      say(
        err.status === 403
          ? ar ? "لا تملك صلاحية القرار." : "You are not permitted to decide."
          : ar ? "فشل الإجراء." : "The action failed.",
        "bad",
      );
    }
  }

  function openFile(row: Opportunity) {
    setEditing(row);
    setFileForm({
      category: row.category ?? "",
      requested_from_group: row.requested_from_group ?? "",
      investment_amount: row.investment_amount ?? "",
      expected_return: row.expected_return ?? "",
      expected_return_pct: row.expected_return_pct ?? "",
      cashflow_note: row.cashflow_note ?? "",
      risk_level: row.risk_level ?? "",
      risk_note: row.risk_note ?? "",
      recommendation: row.recommendation ?? "",
    });
    setOutcomeForm({ actual_return: row.actual_return ?? "", actual_note: row.actual_note ?? "" });
  }

  async function saveFile(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setMessage(null);
    const body: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(fileForm)) {
      if (value !== "") body[key] = value;
    }
    try {
      await api.patch(`/api/v1/opportunities/${editing.id}`, body);
      setEditing(null);
      say(ar ? "تم حفظ ملف الفرصة." : "The opportunity file was saved.");
      await load();
    } catch (err) {
      const status = (err as { status: number }).status;
      say(
        status === 409
          ? ar ? "لا يمكن تعديل فرصة أُرسلت للمالك." : "A submitted opportunity cannot be edited."
          : ar ? "تعذّر الحفظ." : "Could not save.",
        "bad",
      );
    }
  }

  async function saveOutcome(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setMessage(null);
    const body: Record<string, unknown> = {};
    if (outcomeForm.actual_return !== "") body.actual_return = outcomeForm.actual_return;
    if (outcomeForm.actual_note !== "") body.actual_note = outcomeForm.actual_note;
    try {
      await api.patch(`/api/v1/opportunities/${editing.id}`, body);
      setEditing(null);
      say(ar ? "تم تسجيل النتيجة الفعلية." : "The realised result was recorded.");
      await load();
    } catch {
      say(ar ? "تعذّر الحفظ." : "Could not save.", "bad");
    }
  }

  async function saveFollowUp(e: React.FormEvent) {
    e.preventDefault();
    if (!followUp) return;
    setMessage(null);
    const body: Record<string, unknown> = {};
    if (followForm.next_step_owner_id) body.next_step_owner_id = Number(followForm.next_step_owner_id);
    if (followForm.next_step_on) body.next_step_on = followForm.next_step_on;
    try {
      await api.patch(`/api/v1/opportunities/${followUp.id}`, body);
      setFollowUp(null);
      say(ar ? "تم تحديد المتابعة." : "The follow-up was set.");
      await load();
    } catch {
      say(ar ? "تعذّر الحفظ." : "Could not save.", "bad");
    }
  }

  async function compare() {
    if (chosen.length === 0) return;
    setMessage(null);
    try {
      setComparing(
        await api.get<Opportunity[]>(`/api/v1/opportunities/compare?ids=${chosen.join(",")}`),
      );
    } catch {
      say(ar ? "تعذّرت المقارنة." : "Could not compare.", "bad");
    }
  }

  const companyName = useMemo(() => {
    const map = new Map(companies.map((c) => [c.id, ar ? c.name_ar : c.name_en]));
    return (id: number) => map.get(id) ?? String(id);
  }, [companies, ar]);

  const money = (value: string | null) =>
    value === null ? "—" : Number(value).toLocaleString(ar ? "ar-BH" : "en-GB");

  const label = (list: { value: string; ar: string; en: string }[], value: string | null) => {
    if (!value) return "—";
    const found = list.find((x) => x.value === value);
    return found ? (ar ? found.ar : found.en) : value;
  };

  /** The forecast against the realised figure, as a signed difference. */
  function variance(row: Opportunity) {
    if (row.actual_return === null || row.expected_return === null) return null;
    const diff = Number(row.actual_return) - Number(row.expected_return);
    return {
      diff,
      pct: Number(row.expected_return) === 0 ? null : (diff / Number(row.expected_return)) * 100,
    };
  }

  const comparisonRows: { key: string; label: string; value: (o: Opportunity) => React.ReactNode }[] = [
    { key: "company", label: ar ? "الشركة" : "Company", value: (o) => companyName(o.company_id) },
    { key: "category", label: ar ? "التصنيف" : "Classification", value: (o) => label(CATEGORIES, o.category) },
    { key: "country", label: ar ? "الدولة" : "Country", value: (o) => o.country ?? "—" },
    { key: "invest", label: ar ? "مبلغ الاستثمار" : "Investment", value: (o) => money(o.investment_amount) },
    { key: "return", label: ar ? "العائد المتوقع" : "Expected return", value: (o) => money(o.expected_return) },
    { key: "pct", label: ar ? "نسبة العائد" : "Return %", value: (o) => (o.expected_return_pct ? `${o.expected_return_pct}%` : "—") },
    { key: "risk", label: ar ? "المخاطر" : "Risk", value: (o) => label(RISKS, o.risk_level) },
    { key: "actual", label: ar ? "العائد الفعلي" : "Actual return", value: (o) => money(o.actual_return) },
    { key: "status", label: ar ? "الحالة" : "Status", value: (o) => <StatusChip value={o.status} /> },
  ];

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">
          {ar ? "الفرص التجارية والاستثمارية" : "Commercial and investment opportunities"}
        </h1>
        <div className="flex flex-wrap gap-2">
          {chosen.length > 1 && (
            <button type="button" className="btn-ghost" onClick={() => void compare()}>
              {ar ? `مقارنة (${chosen.length})` : `Compare (${chosen.length})`}
            </button>
          )}
          {can("opportunity:create") && (
            <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
              {ar ? "فرصة جديدة" : "New opportunity"}
            </button>
          )}
        </div>
      </header>
      <p className="muted mb-4">
        {ar
          ? "الاعتماد لا ينشئ مشروعاً: يسجّل القرار ووقته فقط."
          : "Approval does not create a project: it records the decision and its timestamp only."}
      </p>

      {formOpen && (
        <Modal title={ar ? "فرصة جديدة" : "New opportunity"} onClose={() => setFormOpen(false)}>
          <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="opp-title">{ar ? "الموضوع" : "Topic"}</label>
              <input id="opp-title" className="input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="opp-company">{ar ? "الشركة" : "Company"}</label>
              <select id="opp-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
                <option value="">—</option>
                {companies.map((c) => (<option key={c.id} value={c.id}>{ar ? c.name_ar : c.name_en}</option>))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="opp-country">{ar ? "الدولة" : "Country"}<span aria-hidden="true"> *</span></label>
              <select id="opp-country" className="input" required value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}>
                <option value="">—</option>
                {COUNTRIES.map((c) => (<option key={c.value} value={c.value}>{ar ? c.ar : c.en}</option>))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="label" htmlFor="opp-desc">{ar ? "وصف مختصر" : "Short description"}</label>
              <input id="opp-desc" className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="opp-file">{ar ? "ملف الدراسة" : "Study file"}</label>
              <input id="opp-file" type="file" className="input" onChange={(e) => setStudyFile(e.target.files?.[0] ?? null)} />
            </div>
            <div className="flex items-end justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>
                {ar ? "إلغاء" : "Cancel"}
              </button>
              <button type="submit" className="btn-primary">{ar ? "حفظ مسودة" : "Save draft"}</button>
            </div>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal title={ar ? "ملف الفرصة" : "Opportunity file"} onClose={() => setEditing(null)}>
          <div className="grid gap-4">
            <p className="muted">{editing.title}</p>
            <form onSubmit={saveFile} className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="file-category">{ar ? "التصنيف" : "Classification"}</label>
                <select id="file-category" className="input" value={fileForm.category} onChange={(e) => setFileForm({ ...fileForm, category: e.target.value })}>
                  <option value="">—</option>
                  {CATEGORIES.map((c) => (<option key={c.value} value={c.value}>{ar ? c.ar : c.en}</option>))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="file-risk">{ar ? "مستوى المخاطر" : "Risk level"}</label>
                <select id="file-risk" className="input" value={fileForm.risk_level} onChange={(e) => setFileForm({ ...fileForm, risk_level: e.target.value })}>
                  <option value="">—</option>
                  {RISKS.map((c) => (<option key={c.value} value={c.value}>{ar ? c.ar : c.en}</option>))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="file-invest">{ar ? "مبلغ الاستثمار" : "Investment amount"}</label>
                <input id="file-invest" type="number" step="0.01" className="input" value={fileForm.investment_amount} onChange={(e) => setFileForm({ ...fileForm, investment_amount: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="file-return">{ar ? "العائد المتوقع" : "Expected return"}</label>
                <input id="file-return" type="number" step="0.01" className="input" value={fileForm.expected_return} onChange={(e) => setFileForm({ ...fileForm, expected_return: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="file-pct">{ar ? "نسبة العائد %" : "Return %"}</label>
                <input id="file-pct" type="number" step="0.01" className="input" value={fileForm.expected_return_pct} onChange={(e) => setFileForm({ ...fileForm, expected_return_pct: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="file-ask">{ar ? "المطلوب من المجموعة" : "Requested from the group"}</label>
                <input id="file-ask" className="input" value={fileForm.requested_from_group} onChange={(e) => setFileForm({ ...fileForm, requested_from_group: e.target.value })} />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="file-cash">{ar ? "التدفقات النقدية" : "Cash flows"}</label>
                <textarea id="file-cash" className="input min-h-16" value={fileForm.cashflow_note} onChange={(e) => setFileForm({ ...fileForm, cashflow_note: e.target.value })} />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="file-risknote">{ar ? "المخاطر وكيف تُدار" : "Risk and how it is handled"}</label>
                <textarea id="file-risknote" className="input min-h-16" value={fileForm.risk_note} onChange={(e) => setFileForm({ ...fileForm, risk_note: e.target.value })} />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="file-rec">{ar ? "التوصية" : "Recommendation"}</label>
                <textarea id="file-rec" className="input min-h-16" value={fileForm.recommendation} onChange={(e) => setFileForm({ ...fileForm, recommendation: e.target.value })} />
              </div>
              <div className="flex justify-end gap-2 sm:col-span-2">
                <button type="button" className="btn-ghost" onClick={() => setEditing(null)}>
                  {ar ? "إلغاء" : "Cancel"}
                </button>
                <button type="submit" className="btn-primary">{ar ? "حفظ" : "Save"}</button>
              </div>
            </form>

            {editing.status === "approved" && (
              <form onSubmit={saveOutcome} className="grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
                <p className="muted sm:col-span-2">
                  {ar
                    ? "النتيجة الفعلية بعد الاعتماد، لمقارنتها بالتوقعات."
                    : "The realised result after approval, to compare with the forecast."}
                </p>
                <div>
                  <label className="label" htmlFor="outcome-return">{ar ? "العائد الفعلي" : "Actual return"}</label>
                  <input id="outcome-return" type="number" step="0.01" className="input" value={outcomeForm.actual_return} onChange={(e) => setOutcomeForm({ ...outcomeForm, actual_return: e.target.value })} />
                </div>
                <div>
                  <label className="label" htmlFor="outcome-note">{ar ? "ملاحظة" : "Note"}</label>
                  <input id="outcome-note" className="input" value={outcomeForm.actual_note} onChange={(e) => setOutcomeForm({ ...outcomeForm, actual_note: e.target.value })} />
                </div>
                <div className="flex justify-end sm:col-span-2">
                  <button type="submit" className="btn-gold">{ar ? "تسجيل النتيجة" : "Record the result"}</button>
                </div>
              </form>
            )}
          </div>
        </Modal>
      )}

      {followUp && (
        <Modal title={ar ? "المتابعة" : "Follow-up"} onClose={() => setFollowUp(null)}>
          <form onSubmit={saveFollowUp} className="grid gap-3">
            <div>
              <label className="label" htmlFor="follow-owner">{ar ? "المسؤول عن المتابعة" : "Follow-up owner"}</label>
              <select id="follow-owner" className="input" value={followForm.next_step_owner_id} onChange={(e) => setFollowForm({ ...followForm, next_step_owner_id: e.target.value })}>
                <option value="">—</option>
                {people.map((p) => (<option key={p.id} value={p.id}>{ar ? p.full_name_ar : p.full_name_en}</option>))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="follow-date">{ar ? "الموعد القادم" : "Next date"}</label>
              <input id="follow-date" type="date" className="input" value={followForm.next_step_on} onChange={(e) => setFollowForm({ ...followForm, next_step_on: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setFollowUp(null)}>
                {ar ? "إلغاء" : "Cancel"}
              </button>
              <button type="submit" className="btn-primary">{ar ? "حفظ" : "Save"}</button>
            </div>
          </form>
        </Modal>
      )}

      {decision && (
        <Modal
          title={decision.verb === "rejected" ? (ar ? "رفض الفرصة" : "Reject the opportunity") : ar ? "تأجيل الفرصة" : "Defer the opportunity"}
          onClose={() => setDecision(null)}
        >
          <div className="grid gap-3">
            <div>
              <label className="label" htmlFor="decision-reason">
                {ar ? "السبب" : "Reason"}
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
                <p className="muted mt-1">{ar ? "السبب إلزامي." : "A reason is required."}</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setDecision(null)}>
                {ar ? "إلغاء" : "Cancel"}
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
                {ar ? "حفظ" : "Save"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {comparing && (
        <Modal title={ar ? "مقارنة الفرص" : "Compare opportunities"} onClose={() => setComparing(null)}>
          <div className="table-scroll">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-line bg-pearl">
                  <th className="p-2 text-start">{ar ? "البند" : "Item"}</th>
                  {comparing.map((o) => (
                    <th key={o.id} className="p-2 text-start">{o.title}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.key} className="border-b border-line last:border-0">
                    <td className="p-2 font-medium">{row.label}</td>
                    {comparing.map((o) => (
                      <td key={o.id} className="p-2">{row.value(o)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Modal>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[900px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{ar ? "الموضوع" : "Topic"}</th>
                <th className="p-3 text-start">{ar ? "الدولة" : "Country"}</th>
                <th className="p-3 text-start">{ar ? "الملف" : "File"}</th>
                <th className="p-3 text-start">{ar ? "المصدر" : "Source"}</th>
                <th className="p-3 text-start">{ar ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{ar ? "السبب" : "Reason"}</th>
                <th className="p-3 text-start">{ar ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const diff = variance(r);
                return (
                  <tr key={r.id} className="border-b border-line last:border-0">
                    <td className="p-3">
                      <span>{r.title}</span>
                      <div className="muted mt-1 flex flex-wrap gap-2 text-xs">
                        {r.category && <span>{label(CATEGORIES, r.category)}</span>}
                        {r.risk_level && <span>{ar ? "المخاطر: " : "Risk: "}{label(RISKS, r.risk_level)}</span>}
                        {r.next_step_owner_name && (
                          <span>
                            {ar ? "المتابعة: " : "Follow-up: "}
                            {r.next_step_owner_name}
                            {r.next_step_on ? ` · ${r.next_step_on}` : ""}
                          </span>
                        )}
                        {diff && (
                          <span className={diff.diff < 0 ? "text-bad" : "text-ok"}>
                            {ar ? "الفرق عن التوقع: " : "vs forecast: "}
                            {money(String(diff.diff))}
                            {diff.pct === null ? "" : ` (${diff.pct.toFixed(1)}%)`}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-3">{r.country ?? "—"}</td>
                    <td className="p-3">
                      {r.attachment_file_id ? (
                        <button type="button" className="btn-ghost" onClick={() => void api.download(`/api/v1/files/${r.attachment_file_id}/download`, r.attachment_name ?? `opportunity-${r.id}`)}>
                          {ar ? "تنزيل الملف" : "Download file"}
                        </button>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3">{r.source ?? "—"}</td>
                    <td className="p-3"><StatusChip value={r.status} /></td>
                    <td className="p-3">{r.decision_note ?? "—"}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          type="checkbox"
                          aria-label={ar ? `اختيار ${r.title} للمقارنة` : `Select ${r.title} for comparison`}
                          checked={chosen.includes(r.id)}
                          onChange={(e) =>
                            setChosen((current) =>
                              e.target.checked ? [...current, r.id] : current.filter((id) => id !== r.id),
                            )
                          }
                        />
                        <button type="button" className="btn-ghost" onClick={() => openFile(r)}>
                          {ar ? "الملف" : "File"}
                        </button>
                        {["approved", "rejected", "deferred"].includes(r.status) && can("opportunity:create") && (
                          <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => {
                              setFollowForm({
                                next_step_owner_id: r.next_step_owner_id ? String(r.next_step_owner_id) : "",
                                next_step_on: r.next_step_on ?? "",
                              });
                              setFollowUp({ id: r.id });
                            }}
                          >
                            {ar ? "المتابعة" : "Follow-up"}
                          </button>
                        )}
                        {r.status === "draft" && can("opportunity:create") && (
                          <button type="button" className="btn-ghost" onClick={() => void act(r.id, "submit")}>
                            {ar ? "إرسال للمالك" : "Submit to owner"}
                          </button>
                        )}
                        {["submitted", "under_review"].includes(r.status) && can("opportunity:decide") && (
                          <>
                            <button type="button" className="btn-ghost" onClick={() => void act(r.id, "decision", { decision: "under_review", note })}>
                              {ar ? "قيد المراجعة" : "Under review"}
                            </button>
                            <button type="button" className="btn-gold" onClick={() => void act(r.id, "decision", { decision: "approved", note })}>
                              {ar ? "اعتماد" : "Approve"}
                            </button>
                            <button
                              type="button"
                              className="btn-bad"
                              onClick={() => {
                                setReason("");
                                setDecision({ id: r.id, verb: "rejected" });
                              }}
                            >
                              {ar ? "رفض" : "Reject"}
                            </button>
                            <button
                              type="button"
                              className="btn-ghost"
                              onClick={() => {
                                setReason("");
                                setDecision({ id: r.id, verb: "deferred" });
                              }}
                            >
                              {ar ? "تأجيل" : "Defer"}
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </DataStates>
      <Toast message={message} tone={tone} />
    </section>
  );
}

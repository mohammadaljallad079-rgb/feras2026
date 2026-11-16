"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { StatusChip } from "@/components/StatusChip";
import { DataStates } from "@/components/DataStates";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Entry = {
  id: number;
  kind: string;
  company_id: number;
  reference: string;
  description: string;
  amount: string;
  currency: string;
  entry_date: string;
  status: string;
  party: string | null;
  tax_amount: string | null;
  direction: string | null;
  document_file_id: number | null;
  created_at: string;
};

const KIND_TABS = [
  { key: "expense", ar: "المصاريف", en: "Expenses" },
  { key: "invoice", ar: "الفواتير", en: "Invoices" },
  { key: "commission", ar: "العمولات", en: "Commissions" },
];

export default function AccountingPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  // The accountant dashboard links here with ?kind=expense|invoice|commission.
  const initialKind = searchParams.get("kind") ?? "expense";
  const [tab, setTab] = useState(initialKind);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({
    kind: initialKind,
    company_id: "",
    reference: "",
    description: "",
    amount: "",
    currency: "BHD",
    entry_date: new Date().toISOString().slice(0, 10),
    party: "",
    tax_amount: "",
    direction: "incoming",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEntries(await api.get<Entry[]>("/api/v1/accounting"));
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

  useEffect(() => {
    setTab(initialKind);
    setForm((f) => ({ ...f, kind: initialKind }));
  }, [initialKind]);

  // The AI assistant's source record links here as ?entry=<id>; switch to that
  // entry's kind and scroll it into view so the link lands on the record.
  const deepEntry = searchParams.get("entry");
  useEffect(() => {
    if (!deepEntry || entries.length === 0) return;
    const row = entries.find((e) => e.id === Number(deepEntry));
    if (row) setTab(row.kind);
    document.getElementById(`accounting-entry-${deepEntry}`)?.scrollIntoView({ block: "start" });
  }, [deepEntry, entries]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/accounting", {
        ...form,
        company_id: Number(form.company_id),
        tax_amount: form.tax_amount || null,
        party: form.party || null,
        direction: form.kind === "commission" ? form.direction : null,
      });
      setForm((f) => ({ ...f, reference: "", description: "", amount: "", party: "", tax_amount: "" }));
      setMessage(locale === "ar" ? "تم تسجيل القيد." : "Entry recorded.");
      setTab(form.kind);
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(
        err.status === 403
          ? locale === "ar"
            ? "لا تملك صلاحية إدخال قيود محاسبية."
            : "You are not permitted to record accounting entries."
          : locale === "ar"
            ? "تعذّر حفظ القيد."
            : "Could not save the entry.",
      );
    }
  }

  const companyName = (id: number) =>
    companies.find((c) => c.id === id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? id;

  const rows = entries.filter((e) => e.kind === tab);

  // Column sets are reproduced verbatim from PDF page 9 for each section.
  const columns: Record<string, { ar: string; en: string; render: (r: Entry) => React.ReactNode }[]> = {
    expense: [
      { ar: "البيان", en: "Statement", render: (r) => r.description },
      { ar: "المبلغ", en: "Amount", render: (r) => <span dir="ltr">{`${r.amount} ${r.currency}`}</span> },
      { ar: "الجهة", en: "Party", render: (r) => r.party ?? "—" },
      { ar: "السداد", en: "Settlement", render: (r) => <StatusChip value={r.status} /> },
    ],
    invoice: [
      { ar: "العميل", en: "Client", render: (r) => r.party ?? "—" },
      {
        ar: "الإجمالي قبل الضريبة",
        en: "Net before tax",
        render: (r) => <span dir="ltr">{`${r.amount} ${r.currency}`}</span>,
      },
      {
        ar: "الضريبة",
        en: "Tax",
        render: (r) => <span dir="ltr">{r.tax_amount ? `${r.tax_amount} ${r.currency}` : "—"}</span>,
      },
      {
        ar: "الإجمالي",
        en: "Total",
        render: (r) => (
          <span dir="ltr">
            {`${(Number(r.amount) + Number(r.tax_amount ?? 0)).toFixed(2)} ${r.currency}`}
          </span>
        ),
      },
    ],
    commission: [
      { ar: "الطرف", en: "Party", render: (r) => r.party ?? "—" },
      { ar: "السبب", en: "Reason", render: (r) => r.description },
      { ar: "المبلغ", en: "Amount", render: (r) => <span dir="ltr">{`${r.amount} ${r.currency}`}</span> },
      {
        ar: "الاتجاه",
        en: "Direction",
        render: (r) =>
          r.direction === "incoming" ? (locale === "ar" ? "وارد" : "Incoming") : locale === "ar" ? "صادر" : "Outgoing",
      },
      { ar: "الحالة", en: "Status", render: (r) => <StatusChip value={r.status} /> },
    ],
  };

  return (
    <section>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-title">{locale === "ar" ? "محاسبة القابضة" : "Holding accounting"}</h1>
          <p className="muted">
            {locale === "ar"
              ? "ثلاث عمليات فقط: مصروف، إيراد/فاتورة، عمولة. لا دفع ولا تحويل بنكي."
              : "Three operations only: expense, income/invoice and commission. No payments or bank transfers."}
          </p>
        </div>
        {/* The backend exports every entry the caller may see; the button is
            offered to anyone who can view accounting at all. */}
        {can("accounting:view") && (
          <button
            type="button"
            className="btn-ghost"
            onClick={() => void api.download("/api/v1/accounting/export.xlsx", "accounting.xlsx")}
          >
            {locale === "ar" ? "تصدير Excel" : "Export Excel"}
          </button>
        )}
      </header>

      {message && (
        <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">
          {message}
        </p>
      )}

      {can("accounting:manage") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="kind">{locale === "ar" ? "النوع" : "Kind"}</label>
            <select id="kind" className="input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="expense">{locale === "ar" ? "مصروف" : "Expense"}</option>
              <option value="invoice">{locale === "ar" ? "فاتورة" : "Invoice"}</option>
              <option value="commission">{locale === "ar" ? "عمولة" : "Commission"}</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="ac-company">{locale === "ar" ? "الشركة" : "Company"}</label>
            <select id="ac-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">—</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="reference">{locale === "ar" ? "المرجع" : "Reference"}</label>
            <input id="reference" className="input" dir="ltr" required value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="description">
              {form.kind === "commission" ? (locale === "ar" ? "السبب" : "Reason") : locale === "ar" ? "البيان" : "Statement"}
            </label>
            <input id="description" className="input" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="party">
              {form.kind === "invoice" ? (locale === "ar" ? "العميل" : "Client") : locale === "ar" ? "الجهة" : "Party"}
            </label>
            <input id="party" className="input" value={form.party} onChange={(e) => setForm({ ...form, party: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="amount">{locale === "ar" ? "المبلغ" : "Amount"}</label>
            <input id="amount" className="input" dir="ltr" inputMode="decimal" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          {form.kind === "invoice" && (
            <div>
              <label className="label" htmlFor="tax_amount">{locale === "ar" ? "الضريبة" : "Tax"}</label>
              <input id="tax_amount" className="input" dir="ltr" inputMode="decimal" value={form.tax_amount} onChange={(e) => setForm({ ...form, tax_amount: e.target.value })} />
            </div>
          )}
          {form.kind === "commission" && (
            <div>
              <label className="label" htmlFor="direction">{locale === "ar" ? "الاتجاه" : "Direction"}</label>
              <select id="direction" className="input" value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })}>
                <option value="incoming">{locale === "ar" ? "وارد" : "Incoming"}</option>
                <option value="outgoing">{locale === "ar" ? "صادر" : "Outgoing"}</option>
              </select>
            </div>
          )}
          <div>
            <label className="label" htmlFor="ac-currency">{locale === "ar" ? "العملة" : "Currency"}</label>
            <input id="ac-currency" className="input" dir="ltr" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="entry_date">{locale === "ar" ? "التاريخ" : "Date"}</label>
            <input id="entry_date" type="date" className="input" dir="ltr" value={form.entry_date} onChange={(e) => setForm({ ...form, entry_date: e.target.value })} />
          </div>
          <div className="flex items-end">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إضافة قيد" : "Add entry"}</button>
          </div>
        </form>
      )}

      <div className="mb-4 flex flex-wrap gap-2" role="tablist">
        {KIND_TABS.map((k) => (
          <button
            key={k.key}
            type="button"
            role="tab"
            aria-selected={tab === k.key}
            className={tab === k.key ? "btn-primary" : "btn-ghost"}
            onClick={() => setTab(k.key)}
          >
            {locale === "ar" ? k.ar : k.en}
          </button>
        ))}
      </div>

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[640px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                {columns[tab].map((c) => (
                  <th key={c.en} className="p-3 text-start section-title">
                    {locale === "ar" ? c.ar : c.en}
                  </th>
                ))}
                <th className="p-3 text-start section-title">{locale === "ar" ? "الشركة" : "Company"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} id={`accounting-entry-${r.id}`} className="border-b border-line last:border-0">
                  {columns[tab].map((c) => (
                    <td key={c.en} className="p-3">
                      {c.render(r)}
                    </td>
                  ))}
                  <td className="p-3">{companyName(r.company_id)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>
    </section>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { StatusChip } from "@/components/StatusChip";
import { DataStates } from "@/components/DataStates";
import { Modal } from "@/components/Modal";
import { Toast } from "@/components/Toast";
import { api, loadError, Company } from "@/lib/api";
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
  payment_status: string | null;
  tax_registration_no: string | null;
  service_item: string | null;
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
  // Table 5, «مصروف جديد»: an expense may carry one optional attachment. The
  // file is uploaded first so the entry can reference the stored file id.
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  // §5.3 «ثلاثة أزرار (مصروف جديد، إيراد/فاتورة جديدة، عمولة جديدة)» — each
  // button opens the same entry window with its kind already chosen.
  const [entryOpen, setEntryOpen] = useState(false);
  const openEntry = (kind: string) => {
    setForm((f) => ({ ...f, kind }));
    setEntryOpen(true);
  };
  const [form, setForm] = useState({
    kind: initialKind,
    company_id: "",
    reference: "",
    description: "",
    amount: "",
    currency: "BHD",
    entry_date: new Date().toISOString().slice(0, 10),
    party: "",
    tax_percent: "",
    direction: "incoming",
    payment_status: "unpaid",
    tax_registration_no: "",
    service_item: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEntries(await api.get<Entry[]>("/api/v1/accounting"));
    } catch (e) {
      setError(loadError(e, locale));
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    // §5.3: these entries belong to «محاسبة القابضة», so the company is the
    // Holding itself and the form does not ask for it.
    api
      .get<Company[]>("/api/v1/companies?include_holding=true")
      .then((rows) => {
        setCompanies(rows);
        const holding = rows.find((c) => c.is_holding);
        if (holding) setForm((f) => ({ ...f, company_id: String(holding.id) }));
      })
      .catch(() => undefined);
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
    if (!form.company_id) {
      setMessage(
        locale === "ar"
          ? "سجل القابضة غير متاح بعد؛ أعد تحميل الشاشة."
          : "The Holding record is not available yet; reload the screen.",
      );
      return;
    }
    setBusy(true);
    try {
      // An optional expense attachment is uploaded before the entry is saved.
      let document_file_id: number | null = null;
      if (form.kind === "expense" && documentFile) {
        const fd = new FormData();
        fd.append("file", documentFile);
        if (form.company_id) fd.append("company_id", form.company_id);
        const stored = await api.upload<{ id: number }>("/api/v1/files", fd);
        document_file_id = stored.id;
      }
      // Table 5, «إيراد / فاتورة جديدة»: «الضريبة % عند انطباقها» — the tax is
      // entered as a rate and the total is computed by the platform.
      const tax_amount =
        form.kind === "invoice" && form.tax_percent
          ? (Number(form.amount) * Number(form.tax_percent)) / 100
          : null;
      const { tax_percent: _taxPercent, ...payload } = form;
      await api.post("/api/v1/accounting", {
        ...payload,
        // Table 5 lists no reference field; the platform assigns one so every
        // entry stays searchable in the tables and the Excel export.
        reference: `${form.kind.toUpperCase()}-${Date.now()}`,
        company_id: Number(form.company_id),
        tax_amount,
        party: form.party || null,
        tax_registration_no: form.kind === "invoice" ? form.tax_registration_no || null : null,
        service_item: form.kind === "invoice" ? form.service_item || null : null,
        direction: form.kind === "commission" ? form.direction : null,
        payment_status: form.kind === "invoice" ? null : form.payment_status,
        document_file_id,
      });
      setForm((f) => ({ ...f, reference: "", description: "", amount: "", party: "", tax_percent: "", tax_registration_no: "", service_item: "" }));
      setDocumentFile(null);
      setEntryOpen(false);
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
    } finally {
      setBusy(false);
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
      // Table 5: the invoice carries the client's tax registration number
      // (manual entry only) and the service item being invoiced.
      { ar: "رقم التسجيل الضريبي", en: "Tax registration no.", render: (r) => <span dir="ltr">{r.tax_registration_no ?? "—"}</span> },
      { ar: "بند الخدمة", en: "Service item", render: (r) => r.service_item ?? "—" },
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
          r.direction === "incoming"
            ? locale === "ar" ? "مستحقة للقابضة" : "Due to holding"
            : locale === "ar" ? "مستحقة على القابضة" : "Due from holding",
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
        <div className="flex flex-wrap gap-2">
          {/* The backend exports every entry the caller may see; the button is
              offered to anyone who can view accounting at all. */}
          {can("accounting:view") && (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => void api.download("/api/v1/accounting/export.xlsx", "accounting.xlsx")}
            >
              {locale === "ar" ? "تنزيل Excel" : "Download Excel"}
            </button>
          )}
          {can("accounting:manage") && (
            <>
              <button type="button" className="btn-primary" onClick={() => openEntry("expense")}>
                {locale === "ar" ? "مصروف جديد" : "New expense"}
              </button>
              <button type="button" className="btn-primary" onClick={() => openEntry("invoice")}>
                {locale === "ar" ? "إيراد/فاتورة جديدة" : "New income/invoice"}
              </button>
              <button type="button" className="btn-primary" onClick={() => openEntry("commission")}>
                {locale === "ar" ? "عمولة جديدة" : "New commission"}
              </button>
            </>
          )}
        </div>
      </header>

      {entryOpen && can("accounting:manage") && (
        <Modal
          title={
            form.kind === "invoice"
              ? locale === "ar" ? "إيراد/فاتورة جديدة" : "New income/invoice"
              : form.kind === "commission"
                ? locale === "ar" ? "عمولة جديدة" : "New commission"
                : locale === "ar" ? "مصروف جديد" : "New expense"
          }
          onClose={() => setEntryOpen(false)}
          wide
        >
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-3">
            <p className="muted">
              {locale === "ar"
                ? `القيد على محاسبة القابضة · ${KIND_TABS.find((k) => k.key === form.kind)?.ar ?? ""}`
                : `Recorded on the Holding's books · ${KIND_TABS.find((k) => k.key === form.kind)?.en ?? ""}`}
            </p>
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="description">
              {form.kind === "commission" ? (locale === "ar" ? "السبب" : "Reason") : locale === "ar" ? "البيان" : "Statement"}
            </label>
            <input id="description" className="input" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="party">
              {form.kind === "invoice"
                ? locale === "ar" ? "العميل" : "Client"
                : form.kind === "expense"
                  ? locale === "ar" ? "الجهة المستفيدة" : "Beneficiary"
                  : locale === "ar" ? "الطرف المقابل" : "Counterparty"}
            </label>
            <input id="party" className="input" value={form.party} onChange={(e) => setForm({ ...form, party: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="amount">
              {form.kind === "invoice"
                ? locale === "ar" ? "المجموع قبل الضريبة" : "Net before tax"
                : locale === "ar" ? "المبلغ" : "Amount"}
            <span aria-hidden="true"> *</span></label>
            <input id="amount" className="input" dir="ltr" inputMode="decimal" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          {form.kind === "invoice" && (
            <div>
              <label className="label" htmlFor="tax-reg">
                {locale === "ar" ? "رقم التسجيل الضريبي (يدويًا فقط)" : "Tax registration number (manual only)"}
              </label>
              <input id="tax-reg" className="input" dir="ltr" value={form.tax_registration_no} onChange={(e) => setForm({ ...form, tax_registration_no: e.target.value })} />
            </div>
          )}
          {form.kind === "invoice" && (
            <div>
              <label className="label" htmlFor="service-item">{locale === "ar" ? "بند الخدمة" : "Service item"}</label>
              <input id="service-item" className="input" value={form.service_item} onChange={(e) => setForm({ ...form, service_item: e.target.value })} />
            </div>
          )}
          {form.kind === "invoice" && (
            <div>
              <label className="label" htmlFor="tax_percent">{locale === "ar" ? "الضريبة % (عند انطباقها)" : "Tax % (when applicable)"}</label>
              <input id="tax_percent" className="input" dir="ltr" inputMode="decimal" value={form.tax_percent} onChange={(e) => setForm({ ...form, tax_percent: e.target.value })} />
              <p className="muted mt-1" dir="ltr">
                {`${(
                  Number(form.amount || 0) +
                  (Number(form.amount || 0) * Number(form.tax_percent || 0)) / 100
                ).toFixed(2)} ${form.currency}`}
              </p>
            </div>
          )}
          {form.kind === "commission" && (
            <div>
              <label className="label" htmlFor="direction">{locale === "ar" ? "الاتجاه" : "Direction"}<span aria-hidden="true"> *</span></label>
              <select id="direction" className="input" required value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })}>
                <option value="incoming">{locale === "ar" ? "مستحقة للقابضة" : "Due to holding"}</option>
                <option value="outgoing">{locale === "ar" ? "مستحقة على القابضة" : "Due from holding"}</option>
              </select>
            </div>
          )}
          {/* Table 5: an expense is «مسدد / غير مسدد»; a commission is
              «مستحقة / مدفوعة / مستلمة». */}
          {form.kind === "expense" && (
            <div>
              <label className="label" htmlFor="pay-status">{locale === "ar" ? "حالة السداد" : "Settlement"}</label>
              <select id="pay-status" className="input" value={form.payment_status} onChange={(e) => setForm({ ...form, payment_status: e.target.value })}>
                <option value="paid">{locale === "ar" ? "مسدد" : "Paid"}</option>
                <option value="unpaid">{locale === "ar" ? "غير مسدد" : "Unpaid"}</option>
              </select>
            </div>
          )}
          {form.kind === "commission" && (
            <div>
              <label className="label" htmlFor="comm-status">{locale === "ar" ? "الحالة" : "Status"}</label>
              <select id="comm-status" className="input" value={form.payment_status} onChange={(e) => setForm({ ...form, payment_status: e.target.value })}>
                <option value="due">{locale === "ar" ? "مستحقة" : "Due"}</option>
                <option value="paid">{locale === "ar" ? "مدفوعة" : "Paid"}</option>
                <option value="received">{locale === "ar" ? "مستلمة" : "Received"}</option>
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
          {form.kind === "expense" && (
            <div className="sm:col-span-2">
              <label className="label" htmlFor="expense-doc">
                {locale === "ar" ? "مرفق اختياري" : "Optional attachment"}
              </label>
              <input
                id="expense-doc"
                type="file"
                className="input"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx"
                onChange={(e) => setDocumentFile(e.target.files?.[0] ?? null)}
              />
              {documentFile && <p className="muted mt-1" dir="ltr">{documentFile.name}</p>}
            </div>
          )}
          <div className="flex items-end justify-end gap-2 sm:col-span-3">
            <button type="button" className="btn-ghost" onClick={() => setEntryOpen(false)}>
              {locale === "ar" ? "إلغاء" : "Cancel"}
            </button>
            <button type="submit" className="btn-primary" disabled={busy}>
              {form.kind === "invoice"
                ? locale === "ar" ? "حفظ وإصدار" : "Save and issue"
                : locale === "ar" ? "إضافة قيد" : "Add entry"}
            </button>
          </div>
        </form>
        </Modal>
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
      <Toast message={message} />
    </section>
  );
}

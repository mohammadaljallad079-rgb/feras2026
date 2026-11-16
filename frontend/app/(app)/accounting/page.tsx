"use client";

import { useEffect, useState } from "react";
import { ResourceTable, Column } from "@/components/ResourceTable";
import { StatusChip } from "@/components/StatusChip";
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
  document_file_id: number | null;
  created_at: string;
};

export default function AccountingPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [reloadKey, setReloadKey] = useState(0);
  const [form, setForm] = useState({
    kind: "expense",
    company_id: "",
    reference: "",
    description: "",
    amount: "",
    currency: "SAR",
    entry_date: new Date().toISOString().slice(0, 10),
  });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/accounting", { ...form, company_id: Number(form.company_id) });
      setForm((f) => ({ ...f, reference: "", description: "", amount: "" }));
      setMessage(locale === "ar" ? "تم تسجيل القيد." : "Entry recorded.");
      setReloadKey((k) => k + 1);
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

  const columns: Column<Entry>[] = [
    { key: "kind", headerAr: "النوع", headerEn: "Kind", render: (r) => <StatusChip value={r.kind} /> },
    { key: "reference", headerAr: "المرجع", headerEn: "Reference", render: (r) => <span dir="ltr">{r.reference}</span> },
    {
      key: "company",
      headerAr: "الشركة",
      headerEn: "Company",
      render: (r) => companies.find((c) => c.id === r.company_id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? r.company_id,
    },
    { key: "description", headerAr: "الوصف", headerEn: "Description", render: (r) => r.description },
    { key: "amount", headerAr: "المبلغ", headerEn: "Amount", numeric: true, render: (r) => `${r.amount} ${r.currency}` },
    { key: "entry_date", headerAr: "التاريخ", headerEn: "Date", numeric: true, render: (r) => <span dir="ltr">{r.entry_date}</span> },
    { key: "status", headerAr: "الحالة", headerEn: "Status", render: (r) => <StatusChip value={r.status} /> },
  ];

  return (
    <>
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
            <label className="label" htmlFor="description">{locale === "ar" ? "الوصف" : "Description"}</label>
            <input id="description" className="input" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="amount">{locale === "ar" ? "المبلغ" : "Amount"}</label>
            <input id="amount" className="input" dir="ltr" inputMode="decimal" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
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
      <ResourceTable<Entry>
        key={reloadKey}
        titleAr="محاسبة المجموعة"
        titleEn="Holding accounting"
        endpoint="/api/v1/accounting"
        columns={columns}
        permission="accounting:view"
      />
    </>
  );
}

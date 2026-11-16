"use client";

import { useEffect, useState } from "react";
import { ResourceTable, Column } from "@/components/ResourceTable";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Employee = {
  id: number;
  name_ar: string;
  name_en: string;
  job_title: string;
  company_id: number;
  contact_email: string | null;
  contact_phone: string | null;
  salary: string | null;
  currency: string;
  contract_type: string | null;
  status: string;
  hired_on: string | null;
  created_at: string;
};

export default function HrPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState({ name_ar: "", name_en: "", job_title: "", company_id: "", contact_email: "", contact_phone: "", salary: "", currency: "SAR", contract_type: "", hired_on: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/employees", {
        ...form,
        company_id: Number(form.company_id),
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        salary: form.salary || null,
        contract_type: form.contract_type || null,
        hired_on: form.hired_on || null,
      });
      setForm({ name_ar: "", name_en: "", job_title: "", company_id: "", contact_email: "", contact_phone: "", salary: "", currency: "SAR", contract_type: "", hired_on: "" });
      setMessage(locale === "ar" ? "تمت إضافة الموظف." : "Employee added.");
      setReloadKey((k) => k + 1);
    } catch {
      setMessage(locale === "ar" ? "تعذّر الحفظ." : "Could not save.");
    }
  }

  const columns: Column<Employee>[] = [
    { key: "name", headerAr: "الاسم", headerEn: "Name", render: (r) => (locale === "ar" ? r.name_ar : r.name_en) },
    { key: "job_title", headerAr: "المسمى الوظيفي", headerEn: "Job title", render: (r) => r.job_title },
    {
      key: "company",
      headerAr: "الشركة",
      headerEn: "Company",
      render: (r) => companies.find((c) => c.id === r.company_id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? r.company_id,
    },
    { key: "contact", headerAr: "بيانات التواصل", headerEn: "Contact", render: (r) => <span dir="ltr">{r.contact_email ?? r.contact_phone ?? "—"}</span> },
    // Salary is confidential HR data; it is only rendered when the viewer holds
    // hr:view_salary, which the backend also enforces on the record itself.
    { key: "salary", headerAr: "الراتب", headerEn: "Salary", numeric: true, render: (r) => (can("hr:view_salary") ? <span dir="ltr">{r.salary ? `${r.salary} ${r.currency}` : "—"}</span> : <span className="chip-bad">{locale === "ar" ? "مقيد" : "Restricted"}</span>) },
    { key: "contract", headerAr: "العقد", headerEn: "Contract", render: (r) => r.contract_type ?? "—" },
    { key: "status", headerAr: "حالة التوظيف", headerEn: "Employment status", render: (r) => <StatusChip value={r.status} /> },
  ];

  return (
    <>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}
      {can("hr:manage") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="emp-name-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
            <input id="emp-name-ar" className="input" dir="rtl" required value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-name-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
            <input id="emp-name-en" className="input" dir="ltr" required value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-job">{locale === "ar" ? "المسمى الوظيفي" : "Job title"}</label>
            <input id="emp-job" className="input" required value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-company">{locale === "ar" ? "الشركة" : "Company"}</label>
            <select id="emp-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">—</option>
              {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="emp-email">{locale === "ar" ? "البريد الإلكتروني" : "Email"}</label>
            <input id="emp-email" type="email" className="input" dir="ltr" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-phone">{locale === "ar" ? "الهاتف" : "Phone"}</label>
            <input id="emp-phone" className="input" dir="ltr" value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-salary">{locale === "ar" ? "الراتب" : "Salary"}</label>
            <input id="emp-salary" className="input" dir="ltr" inputMode="decimal" value={form.salary} onChange={(e) => setForm({ ...form, salary: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-contract">{locale === "ar" ? "نوع العقد" : "Contract type"}</label>
            <input id="emp-contract" className="input" value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-hired">{locale === "ar" ? "تاريخ التعيين" : "Hired on"}</label>
            <input id="emp-hired" type="date" className="input" dir="ltr" value={form.hired_on} onChange={(e) => setForm({ ...form, hired_on: e.target.value })} />
          </div>
          <div className="flex items-end">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إضافة موظف" : "Add employee"}</button>
          </div>
        </form>
      )}
      <ResourceTable<Employee>
        key={reloadKey}
        titleAr="الموظفون والموارد البشرية"
        titleEn="Employees and HR"
        endpoint="/api/v1/employees"
        columns={columns}
        permission="hr:view"
      />
    </>
  );
}

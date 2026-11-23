"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusChip } from "@/components/StatusChip";
import { DataStates } from "@/components/DataStates";
import { Modal } from "@/components/Modal";
import { Toast } from "@/components/Toast";
import { api, loadErrorState, Company } from "@/lib/api";
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
  contract_summary: string | null;
  official_documents_file_id: number | null;
  official_documents_name: string | null;
  employment_contract_file_id: number | null;
  employment_contract_name: string | null;
  status: string;
  hired_on: string | null;
  created_at: string;
};

type EmployeeEvent = {
  id: number;
  employee_id: number;
  kind: string;
  detail: string;
  effective_on: string | null;
  attachment_file_id: number | null;
  created_at: string;
};

export default function HrPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [rows, setRows] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);
  const [events, setEvents] = useState<EmployeeEvent[]>([]);
  const [eventForm, setEventForm] = useState({ kind: "leave", detail: "", effective_on: "" });
  const [eventFile, setEventFile] = useState<File | null>(null);
  // Table 6 R11 «إضافة إجازة / إنذار / عهدة»: نوع السجل، التاريخ، التفاصيل، المرفق.
  const [eventOpen, setEventOpen] = useState(false);
  const [form, setForm] = useState({ name_ar: "", name_en: "", job_title: "", company_id: "", contact_email: "", contact_phone: "", salary: "", currency: "SAR", contract_type: "", contract_summary: "", hired_on: "" });
  // Table 5, «إضافة موظف»: the official documents and the employment contract.
  const [officialDocs, setOfficialDocs] = useState<File | null>(null);
  const [contractFile, setContractFile] = useState<File | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.get<Employee[]>("/api/v1/employees"));
    } catch (e) {
      setError(loadErrorState(e, locale));
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    // §5.1: Employees & HR shows separate tables for each company *and for the
    // Holding*, so the Holding's own record is requested alongside the
    // subsidiaries. A scoped manager never receives it (company isolation), so
    // only an unscoped reader — the owner, the accountant, the developer — sees
    // the Holding table.
    api.get<Company[]>("/api/v1/companies?include_holding=true").then(setCompanies).catch(() => undefined);
  }, [load]);

  async function openEvents(id: number) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    setEvents(await api.get<EmployeeEvent[]>(`/api/v1/employees/${id}/events`).catch(() => []));
  }

  async function addEvent(id: number) {
    if (!eventForm.detail) return;
    let attachment_file_id: number | null = null;
    if (eventFile) {
      // HR attachments are confidential: the file is stored with the flag so a
      // reader without hr:view_confidential sees «مرفق مقيد» instead.
      const body = new FormData();
      body.append("file", eventFile);
      body.append("is_confidential", "true");
      const stored = await api.upload<{ id: number }>("/api/v1/files", body);
      attachment_file_id = stored.id;
    }
    await api.post(`/api/v1/employees/${id}/events`, {
      ...eventForm,
      effective_on: eventForm.effective_on || null,
      attachment_file_id,
    });
    setEventForm({ kind: "leave", detail: "", effective_on: "" });
    setEventFile(null);
    setEventOpen(false);
    setMessage(locale === "ar" ? "تمت إضافة السجل." : "Record added.");
    setEvents(await api.get<EmployeeEvent[]>(`/api/v1/employees/${id}/events`).catch(() => []));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      // Table 5, «إضافة موظف»: the two documents are uploaded first and linked
      // to the employee record.
      let official_documents_file_id: number | null = null;
      let employment_contract_file_id: number | null = null;
      if (officialDocs) {
        const body = new FormData();
        body.append("file", officialDocs);
        body.append("company_id", form.company_id);
        official_documents_file_id = (await api.upload<{ id: number }>("/api/v1/files", body)).id;
      }
      if (contractFile) {
        const body = new FormData();
        body.append("file", contractFile);
        body.append("company_id", form.company_id);
        employment_contract_file_id = (await api.upload<{ id: number }>("/api/v1/files", body)).id;
      }
      await api.post("/api/v1/employees", {
        ...form,
        company_id: Number(form.company_id),
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        salary: form.salary || null,
        contract_type: form.contract_type || null,
        contract_summary: form.contract_summary || null,
        hired_on: form.hired_on || null,
        official_documents_file_id,
        employment_contract_file_id,
      });
      setForm({ name_ar: "", name_en: "", job_title: "", company_id: "", contact_email: "", contact_phone: "", salary: "", currency: "SAR", contract_type: "", contract_summary: "", hired_on: "" });
      setOfficialDocs(null);
      setContractFile(null);
      setFormOpen(false);
      setMessage(locale === "ar" ? "تمت إضافة الموظف." : "Employee added.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر الحفظ." : "Could not save.");
    }
  }

  // PDF page 14: employee files are grouped per company.
  const grouped = companies
    .map((c) => ({ company: c, staff: rows.filter((r) => r.company_id === c.id) }))
    .filter((g) => g.staff.length > 0);

  const canSeeConfidential = can("hr:view_confidential");

  return (
    <section>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-title">{locale === "ar" ? "الموظفون والموارد البشرية" : "Employees and HR"}</h1>
          <p className="muted">
            {locale === "ar"
              ? "تُعرض ملفات الموظفين لكل شركة. مرفقات الإجازات تظهر «مرفق مقيد» لمن لا يملك صلاحية الوصول."
              : "Employee files are shown per company. Leave attachments read «مرفق مقيد» for anyone without the permission."}
          </p>
        </div>
        {can("hr:manage") && (
          <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
            {locale === "ar" ? "إضافة موظف" : "Add employee"}
          </button>
        )}
      </header>

      {formOpen && can("hr:manage") && (
        <Modal
          title={locale === "ar" ? "إضافة موظف" : "Add employee"}
          onClose={() => setFormOpen(false)}
          wide
        >
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="emp-name-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
            <input id="emp-name-ar" className="input" dir="rtl" required value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-name-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
            <input id="emp-name-en" className="input" dir="ltr" required value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-job">{locale === "ar" ? "المنصب" : "Position"}</label>
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
            <label className="label" htmlFor="emp-phone">{locale === "ar" ? "رقم التواصل" : "Contact number"}</label>
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
          {/* Table 5, «إضافة موظف»: ملخص عقد العمل، المستندات الرسمية، عقد العمل. */}
          <div className="sm:col-span-3">
            <label className="label" htmlFor="emp-contract-summary">{locale === "ar" ? "ملخص عقد العمل" : "Contract summary"}</label>
            <textarea id="emp-contract-summary" className="input min-h-20" value={form.contract_summary} onChange={(e) => setForm({ ...form, contract_summary: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="emp-official-docs">{locale === "ar" ? "المستندات الرسمية" : "Official documents"}</label>
            <input id="emp-official-docs" type="file" className="input" onChange={(e) => setOfficialDocs(e.target.files?.[0] ?? null)} />
          </div>
          <div>
            <label className="label" htmlFor="emp-contract-file">{locale === "ar" ? "عقد العمل" : "Employment contract"}</label>
            <input id="emp-contract-file" type="file" className="input" onChange={(e) => setContractFile(e.target.files?.[0] ?? null)} />
          </div>
          <div>
            <label className="label" htmlFor="emp-hired">{locale === "ar" ? "تاريخ التعيين" : "Hired on"}</label>
            <input id="emp-hired" type="date" className="input" dir="ltr" value={form.hired_on} onChange={(e) => setForm({ ...form, hired_on: e.target.value })} />
          </div>
          <div className="actions sm:col-span-3">
            <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>
              {locale === "ar" ? "إلغاء" : "Cancel"}
            </button>
            <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ" : "Save"}</button>
          </div>
        </form>
        </Modal>
      )}

      <DataStates loading={loading} error={error} empty={grouped.length === 0}>
        <div className="space-y-6">
          {grouped.map(({ company, staff }) => (
            <article key={company.id} className="card table-scroll">
              <h2 className="section-title mb-3">{locale === "ar" ? company.name_ar : company.name_en}</h2>
              <table className="w-full min-w-[760px] border-collapse">
                <thead>
                  <tr className="border-b border-line">
                    {[
                      { ar: "الاسم", en: "Name" },
                      { ar: "المنصب", en: "Job title" },
                      { ar: "التواصل", en: "Contact" },
                      { ar: "الراتب", en: "Salary" },
                      { ar: "العقد", en: "Contract" },
                      { ar: "المستندات", en: "Documents" },
                      { ar: "الحالة", en: "Status" },
                      { ar: "السجلات", en: "Records" },
                    ].map((c) => (
                      <th key={c.en} className="p-2 text-start text-secondary">
                        {locale === "ar" ? c.ar : c.en}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {staff.map((r) => (
                    <tr key={r.id} className="border-b border-line last:border-0 align-top">
                      <td className="p-2">{locale === "ar" ? r.name_ar : r.name_en}</td>
                      <td className="p-2">{r.job_title}</td>
                      <td className="p-2" dir="ltr">{r.contact_email ?? r.contact_phone ?? "—"}</td>
                      {/* Salary is confidential; the backend refuses the value too. */}
                      <td className="p-2" dir="ltr">
                        {can("hr:view_salary") ? (r.salary ? `${r.salary} ${r.currency}` : "—") : <span className="chip-bad">{locale === "ar" ? "مقيد" : "Restricted"}</span>}
                      </td>
                      <td className="p-2">{r.contract_type ?? "—"}</td>
                      {/* Table 5: the official documents and the employment contract. */}
                      <td className="p-2">
                        <div className="flex flex-wrap gap-2">
                          {r.official_documents_file_id ? (
                            <button type="button" className="btn-ghost" onClick={() => void api.download(`/api/v1/files/${r.official_documents_file_id}/download`, r.official_documents_name ?? `official-documents-${r.id}`)}>
                              {locale === "ar" ? "المستندات" : "Documents"}
                            </button>
                          ) : (
                            <span className="muted">—</span>
                          )}
                          {r.employment_contract_file_id ? (
                            <button type="button" className="btn-ghost" onClick={() => void api.download(`/api/v1/files/${r.employment_contract_file_id}/download`, r.employment_contract_name ?? `employment-contract-${r.id}`)}>
                              {locale === "ar" ? "العقد" : "Contract"}
                            </button>
                          ) : null}
                        </div>
                      </td>
                      <td className="p-2"><StatusChip value={r.status} /></td>
                      <td className="p-2">
                        <button type="button" className="btn-ghost" onClick={() => void openEvents(r.id)} aria-expanded={openId === r.id}>
                          {locale === "ar" ? "السجل" : "History"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {openId !== null && staff.some((s) => s.id === openId) && (
                <div className="mt-3 border-t border-line pt-3">
                  <h3 className="section-title mb-2">{locale === "ar" ? "سجل الإجازات والحركات" : "Leave and movement records"}</h3>
                  <ul className="space-y-2">
                    {events.length === 0 && <li className="muted">{locale === "ar" ? "لا سجلات." : "No records."}</li>}
                    {events.map((ev) => (
                      <li key={ev.id} className="rounded-control bg-pearl p-3">
                        <p className="text-secondary">
                          <StatusChip value={ev.kind} /> <span dir="ltr">{ev.effective_on ?? ""}</span>
                        </p>
                        <p>{ev.detail}</p>
                        {ev.attachment_file_id &&
                          (canSeeConfidential ? (
                            <button
                              type="button"
                              className="btn-ghost mt-2"
                              onClick={() => void api.download(`/api/v1/files/${ev.attachment_file_id}/download`, `attachment-${ev.id}`)}
                            >
                              {locale === "ar" ? "تنزيل المرفق" : "Download attachment"}
                            </button>
                          ) : (
                            <span className="chip-warn mt-2 inline-block">{locale === "ar" ? "مرفق مقيد" : "Restricted attachment"}</span>
                          ))}
                      </li>
                    ))}
                  </ul>
                  {can("hr:manage") && (
                    <button type="button" className="btn-primary mt-3" onClick={() => setEventOpen(true)}>
                      {locale === "ar" ? "إضافة إجازة / إنذار / عهدة" : "Add leave / warning / custody"}
                    </button>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      {eventOpen && can("hr:manage") && openId !== null && (
        <Modal
          title={locale === "ar" ? "إضافة إجازة / إنذار / عهدة" : "Add leave / warning / custody"}
          onClose={() => setEventOpen(false)}
        >
          <div className="grid gap-3">
            <div>
              <label className="label" htmlFor="ev-kind">{locale === "ar" ? "نوع السجل" : "Record type"}</label>
              <select id="ev-kind" className="input" value={eventForm.kind} onChange={(e) => setEventForm({ ...eventForm, kind: e.target.value })}>
                <option value="annual_leave">{locale === "ar" ? "إجازة سنوية" : "Annual leave"}</option>
                <option value="sick_leave">{locale === "ar" ? "إجازة مرضية" : "Sick leave"}</option>
                <option value="warning">{locale === "ar" ? "إنذار" : "Warning"}</option>
                <option value="custody">{locale === "ar" ? "عهدة" : "Custody"}</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="ev-date">{locale === "ar" ? "التاريخ" : "Date"}</label>
              <input id="ev-date" type="date" className="input" dir="ltr" value={eventForm.effective_on} onChange={(e) => setEventForm({ ...eventForm, effective_on: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ev-detail">{locale === "ar" ? "التفاصيل" : "Details"}</label>
              <textarea id="ev-detail" className="input min-h-20" value={eventForm.detail} onChange={(e) => setEventForm({ ...eventForm, detail: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ev-file">{locale === "ar" ? "المرفق" : "Attachment"}</label>
              <input id="ev-file" type="file" className="input" onChange={(e) => setEventFile(e.target.files?.[0] ?? null)} />
            </div>
            <div className="actions">
              <button type="button" className="btn-ghost" onClick={() => setEventOpen(false)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button type="button" className="btn-primary" onClick={() => void addEvent(openId)}>
                {locale === "ar" ? "حفظ" : "Save"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      </DataStates>
      <Toast message={message} />
    </section>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { ResourceTable, Column } from "@/components/ResourceTable";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Person = { id: number; full_name_ar: string; full_name_en: string };

type Lead = {
  id: number;
  name: string;
  contact_email: string | null;
  contact_phone: string | null;
  requested_service: string | null;
  source: string | null;
  company_id: number;
  follow_up_at: string | null;
  status: string;
  notes: string | null;
  assigned_to_id: number | null;
  created_at: string;
};

export default function LeadsPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [form, setForm] = useState({ name: "", contact_email: "", contact_phone: "", requested_service: "", source: "", company_id: "", follow_up_at: "", notes: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  // PDF p.11: three narrowing controls above the table.
  const [companyFilter, setCompanyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  const [rows, setRows] = useState<Lead[]>([]);

  useEffect(() => {
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
    api.get<Person[]>("/api/v1/users").then(setPeople).catch(() => undefined);
  }, []);

  useEffect(() => {
    api.get<Lead[]>("/api/v1/leads").then(setRows).catch(() => undefined);
  }, [reloadKey]);

  const assignedName = useCallback(
    (id: number | null) => {
      if (!id) return "—";
      const p = people.find((x) => x.id === id);
      return p ? (locale === "ar" ? p.full_name_ar : p.full_name_en) : `#${id}`;
    },
    [people, locale],
  );

  async function advanceStatus(id: number, status: string) {
    await api.patch(`/api/v1/leads/${id}`, { status }).catch(() => undefined);
    setReloadKey((k) => k + 1);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/leads", {
        ...form,
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        follow_up_at: form.follow_up_at || null,
        notes: form.notes || null,
        company_id: Number(form.company_id),
      });
      setForm({ name: "", contact_email: "", contact_phone: "", requested_service: "", source: "", company_id: "", follow_up_at: "", notes: "" });
      setMessage(locale === "ar" ? "تم إنشاء العميل المحتمل." : "Lead created.");
      setReloadKey((k) => k + 1);
    } catch {
      setMessage(locale === "ar" ? "تعذّر الحفظ. تأكد من اختيار شركة مسجّلة." : "Could not save. Make sure the company is registered.");
    }
  }

  const columns: Column<Lead>[] = [
    { key: "name", headerAr: "الاسم", headerEn: "Name", render: (r) => r.name },
    { key: "contact", headerAr: "بيانات التواصل", headerEn: "Contact", render: (r) => <span dir="ltr">{r.contact_email ?? r.contact_phone ?? "—"}</span> },
    { key: "service", headerAr: "الخدمة المطلوبة", headerEn: "Requested service", render: (r) => r.requested_service ?? "—" },
    { key: "source", headerAr: "المصدر", headerEn: "Source", render: (r) => r.source ?? "—" },
    {
      key: "company",
      headerAr: "الشركة",
      headerEn: "Company",
      render: (r) => companies.find((c) => c.id === r.company_id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? r.company_id,
    },
    { key: "follow_up", headerAr: "المتابعة", headerEn: "Follow-up", numeric: true, render: (r) => <span dir="ltr">{r.follow_up_at ?? "—"}</span> },
    { key: "status", headerAr: "الحالة", headerEn: "Status", render: (r) => <StatusChip value={r.status} /> },
    { key: "notes", headerAr: "الملاحظة", headerEn: "Notes", render: (r) => r.notes ?? "—" },
    { key: "assigned", headerAr: "المسؤول", headerEn: "Assigned to", render: (r) => assignedName(r.assigned_to_id) },
  ];

  return (
    <>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}
      {can("lead:create") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="lead-name">{locale === "ar" ? "الاسم" : "Name"}</label>
            <input id="lead-name" className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="lead-email">{locale === "ar" ? "البريد الإلكتروني" : "Email"}</label>
            <input id="lead-email" type="email" className="input" dir="ltr" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="lead-phone">{locale === "ar" ? "الهاتف" : "Phone"}</label>
            <input id="lead-phone" className="input" dir="ltr" value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="lead-service">{locale === "ar" ? "الخدمة المطلوبة" : "Requested service"}</label>
            <input id="lead-service" className="input" value={form.requested_service} onChange={(e) => setForm({ ...form, requested_service: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="lead-source">{locale === "ar" ? "المصدر" : "Source"}</label>
            <input id="lead-source" className="input" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="lead-company">{locale === "ar" ? "الشركة" : "Company"}</label>
            <select id="lead-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">—</option>
              {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="lead-follow">{locale === "ar" ? "تاريخ المتابعة" : "Follow-up date"}</label>
            <input id="lead-follow" type="date" className="input" dir="ltr" value={form.follow_up_at} onChange={(e) => setForm({ ...form, follow_up_at: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="lead-notes">{locale === "ar" ? "ملاحظات" : "Notes"}</label>
            <input id="lead-notes" className="input" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="flex items-end">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إضافة" : "Add"}</button>
          </div>
        </form>
      )}
      <ResourceTable<Lead>
        key={reloadKey}
        titleAr="العملاء المحتملون"
        titleEn="Leads"
        endpoint="/api/v1/leads"
        columns={columns}
        permission="lead:view"
        filters={
          <>
            <div>
              <label className="label" htmlFor="filter-company">{locale === "ar" ? "الشركة" : "Company"}</label>
              <select id="filter-company" className="input" value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)}>
                <option value="">{locale === "ar" ? "كل الشركات" : "All companies"}</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="filter-status">{locale === "ar" ? "الحالة" : "Status"}</label>
              <select id="filter-status" className="input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">{locale === "ar" ? "كل الحالات" : "All statuses"}</option>
                {["new", "contacted", "qualified", "won", "lost"].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="filter-source">{locale === "ar" ? "المصدر" : "Source"}</label>
              <select id="filter-source" className="input" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
                <option value="">{locale === "ar" ? "كل المصادر" : "All sources"}</option>
                {[...new Set(rows.map((r) => r.source).filter((s): s is string => Boolean(s)))].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </>
        }
        filter={(r) =>
          (!companyFilter || String(r.company_id) === companyFilter) &&
          (!statusFilter || r.status === statusFilter) &&
          (!sourceFilter || r.source === sourceFilter)
        }
        actions={(row) => (
          <div className="flex flex-wrap gap-2">
            {["new", "contacted", "qualified", "won", "lost"]
              .filter((s) => s !== row.status)
              .slice(0, 2)
              .map((s) => (
                <button key={s} type="button" className="btn-ghost" onClick={() => void advanceStatus(row.id, s)}>
                  {s}
                </button>
              ))}
          </div>
        )}
      />
    </>
  );
}

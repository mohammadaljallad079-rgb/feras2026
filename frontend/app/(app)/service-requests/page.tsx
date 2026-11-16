"use client";

import { useEffect, useState } from "react";
import { ResourceTable, Column } from "@/components/ResourceTable";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type ServiceRequest = {
  id: number;
  subject: string;
  body: string | null;
  company_id: number;
  created_by_id: number;
  recipient_id: number;
  priority: string;
  deadline: string | null;
  status: string;
  created_at: string;
};

export default function ServiceRequestsPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState({ subject: "", body: "", company_id: "", recipient_id: "", priority: "normal", deadline: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/service-requests", {
        ...form,
        company_id: Number(form.company_id),
        recipient_id: Number(form.recipient_id),
        deadline: form.deadline || null,
      });
      setForm({ subject: "", body: "", company_id: "", recipient_id: "", priority: "normal", deadline: "" });
      setMessage(locale === "ar" ? "تم إنشاء الطلب." : "Request created.");
      setReloadKey((k) => k + 1);
    } catch {
      setMessage(locale === "ar" ? "تعذّر إنشاء الطلب." : "Could not create the request.");
    }
  }

  const columns: Column<ServiceRequest>[] = [
    { key: "subject", headerAr: "الموضوع", headerEn: "Subject", render: (r) => r.subject },
    {
      key: "company",
      headerAr: "الشركة",
      headerEn: "Company",
      render: (r) => companies.find((c) => c.id === r.company_id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? r.company_id,
    },
    { key: "recipient", headerAr: "المستلم", headerEn: "Recipient", numeric: true, render: (r) => <span dir="ltr">#{r.recipient_id}</span> },
    { key: "priority", headerAr: "الأولوية", headerEn: "Priority", render: (r) => <StatusChip value={r.priority} /> },
    { key: "deadline", headerAr: "الموعد النهائي", headerEn: "Deadline", numeric: true, render: (r) => <span dir="ltr">{r.deadline ?? "—"}</span> },
    { key: "status", headerAr: "الحالة", headerEn: "Status", render: (r) => <StatusChip value={r.status} /> },
  ];

  return (
    <>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}
      {can("service:create") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="sr-subject">{locale === "ar" ? "الموضوع" : "Subject"}</label>
            <input id="sr-subject" className="input" required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="sr-company">{locale === "ar" ? "الشركة" : "Company"}</label>
            <select id="sr-company" className="input" required value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">—</option>
              {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="sr-recipient">{locale === "ar" ? "معرّف المستلم" : "Recipient id"}</label>
            <input id="sr-recipient" className="input" dir="ltr" required value={form.recipient_id} onChange={(e) => setForm({ ...form, recipient_id: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="sr-priority">{locale === "ar" ? "الأولوية" : "Priority"}</label>
            <select id="sr-priority" className="input" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option value="low">{locale === "ar" ? "منخفضة" : "Low"}</option>
              <option value="normal">{locale === "ar" ? "عادية" : "Normal"}</option>
              <option value="high">{locale === "ar" ? "عالية" : "High"}</option>
              <option value="urgent">{locale === "ar" ? "عاجلة" : "Urgent"}</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="sr-deadline">{locale === "ar" ? "الموعد النهائي" : "Deadline"}</label>
            <input id="sr-deadline" type="date" className="input" dir="ltr" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="sr-body">{locale === "ar" ? "التفاصيل" : "Details"}</label>
            <textarea id="sr-body" className="input min-h-20" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div>
            <button type="submit" className="btn-primary">{locale === "ar" ? "إنشاء طلب" : "Create request"}</button>
          </div>
        </form>
      )}
      <ResourceTable<ServiceRequest>
        key={reloadKey}
        titleAr="طلبات الخدمة"
        titleEn="Service requests"
        endpoint="/api/v1/service-requests"
        columns={columns}
        permission="service:view"
      />
    </>
  );
}

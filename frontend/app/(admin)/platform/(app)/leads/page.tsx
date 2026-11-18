"use client";

import { useSearchParams } from "next/navigation";
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
  contact_method: string | null;
  company_id: number;
  follow_up_at: string | null;
  status: string;
  notes: string | null;
  assigned_to_id: number | null;
  created_at: string;
};

const LEAD_STATUSES = ["new", "contacted", "following_up", "qualified", "not_suitable", "closed"];

export default function LeadsPage() {
  const { locale, can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [form, setForm] = useState({ name: "", contact_method: "", contact_email: "", contact_phone: "", requested_service: "", source: "", company_id: "", follow_up_at: "", notes: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  // §5.1: the leads table narrows by company, status, source and follow-up.
  const [companyFilter, setCompanyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [followUpFilter, setFollowUpFilter] = useState("");

  const [rows, setRows] = useState<Lead[]>([]);

  // Table 6: «تحديث» — the row action opens a modal with the status and a note.
  const [updateFor, setUpdateFor] = useState<Lead | null>(null);
  const [updateStatus, setUpdateStatus] = useState("new");
  const [updateNote, setUpdateNote] = useState("");

  // Word §5.5: the marketer's dashboard action «إرسال شكوى للمالك» arrives as
  // ?complaint=1 and opens the complaint form. The complaint is addressed to the
  // owner alone; it is not a lead.
  const searchParams = useSearchParams();
  const [complaintOpen, setComplaintOpen] = useState(false);
  const [complaint, setComplaint] = useState("");
  useEffect(() => {
    if (searchParams.get("complaint") === "1") setComplaintOpen(true);
  }, [searchParams]);

  async function sendComplaint(e: React.FormEvent) {
    e.preventDefault();
    if (!complaint.trim()) return;
    try {
      await api.post("/api/v1/service-requests/complaint", { body: complaint });
      setMessage(locale === "ar" ? "أُرسلت الشكوى إلى المالك." : "The complaint was sent to the owner.");
      setComplaint("");
      setComplaintOpen(false);
    } catch {
      setMessage(locale === "ar" ? "تعذّر إرسال الشكوى." : "The complaint could not be sent.");
    }
  }

  useEffect(() => {
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
    api.get<Person[]>("/api/v1/users/directory").then(setPeople).catch(() => undefined);
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

  // Table 6: «تحديث» records a status and a note in the lead's own record.
  async function saveUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!updateFor) return;
    await api
      .patch(`/api/v1/leads/${updateFor.id}`, {
        status: updateStatus,
        notes: updateNote || null,
      })
      .catch(() => undefined);
    setMessage(locale === "ar" ? "تم تحديث العميل المحتمل." : "Lead updated.");
    setUpdateFor(null);
    setReloadKey((k) => k + 1);
  }

  // PDF p.11 / Table 5: the owner and the business developer may reassign a
  // lead to a colleague. The assignee is chosen from the people directory.
  async function assignTo(id: number, assignedTo: string) {
    await api.patch(`/api/v1/leads/${id}`, { assigned_to_id: assignedTo ? Number(assignedTo) : null }).catch(() => undefined);
    setReloadKey((k) => k + 1);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/leads", {
        ...form,
        contact_method: form.contact_method || null,
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        follow_up_at: form.follow_up_at || null,
        notes: form.notes || null,
        company_id: Number(form.company_id),
      });
      setForm({ name: "", contact_method: "", contact_email: "", contact_phone: "", requested_service: "", source: "", company_id: "", follow_up_at: "", notes: "" });
      setMessage(locale === "ar" ? "تم إنشاء العميل المحتمل." : "Lead created.");
      setReloadKey((k) => k + 1);
    } catch {
      setMessage(locale === "ar" ? "تعذّر الحفظ. تأكد من اختيار شركة مسجّلة." : "Could not save. Make sure the company is registered.");
    }
  }

  const columns: Column<Lead>[] = [
    { key: "name", headerAr: "الاسم", headerEn: "Name", render: (r) => r.name },
    { key: "contact", headerAr: "بيانات التواصل", headerEn: "Contact", render: (r) => <span dir="ltr">{r.contact_email ?? r.contact_phone ?? "—"}</span> },
    {
      key: "contact_method",
      headerAr: "وسيلة التواصل",
      headerEn: "Contact method",
      render: (r) =>
        r.contact_method
          ? {
              email: locale === "ar" ? "بريد إلكتروني" : "Email",
              phone: locale === "ar" ? "هاتف" : "Phone",
              whatsapp: locale === "ar" ? "واتساب" : "WhatsApp",
              other: locale === "ar" ? "أخرى" : "Other",
            }[r.contact_method] ?? r.contact_method
          : "—",
    },
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

  // The follow-up filter compares dates as plain ISO strings (YYYY-MM-DD), so
  // today's date is enough to split "due" from "scheduled".
  const today = new Date().toISOString().slice(0, 10);

  return (
    <>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}
      {can("service:create") && (
        <div className="mb-4">
          <button type="button" className="btn-ghost" onClick={() => setComplaintOpen((v) => !v)}>
            {locale === "ar" ? "إرسال شكوى للمالك" : "Send a complaint to the owner"}
          </button>
        </div>
      )}
      {complaintOpen && can("service:create") && (
        <form onSubmit={sendComplaint} className="card mb-4 space-y-3">
          <label className="label" htmlFor="complaint-body">
            {locale === "ar" ? "نص الشكوى *" : "Complaint text *"}
          </label>
          <textarea
            id="complaint-body"
            className="input"
            required
            rows={4}
            value={complaint}
            onChange={(e) => setComplaint(e.target.value)}
          />
          <div className="flex gap-2">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إرسال" : "Send"}</button>
            <button type="button" className="btn-ghost" onClick={() => setComplaintOpen(false)}>
              {locale === "ar" ? "إلغاء" : "Cancel"}
            </button>
          </div>
        </form>
      )}
      {can("lead:manage") && (
        <form onSubmit={submit} className="card mb-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="lead-name">{locale === "ar" ? "الاسم" : "Name"}</label>
            <input id="lead-name" className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="lead-contact-method">{locale === "ar" ? "وسيلة التواصل" : "Contact method"}</label>
            <select id="lead-contact-method" className="input" value={form.contact_method} onChange={(e) => setForm({ ...form, contact_method: e.target.value })}>
              <option value="">{locale === "ar" ? "— بلا تحديد —" : "— Not specified —"}</option>
              <option value="email">{locale === "ar" ? "بريد إلكتروني" : "Email"}</option>
              <option value="phone">{locale === "ar" ? "هاتف" : "Phone"}</option>
              <option value="whatsapp">{locale === "ar" ? "واتساب" : "WhatsApp"}</option>
              <option value="other">{locale === "ar" ? "أخرى" : "Other"}</option>
            </select>
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
            <label className="label" htmlFor="lead-company">{locale === "ar" ? "الشركة المستلمة" : "Receiving company"}<span aria-hidden="true"> *</span></label>
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
            <label className="label" htmlFor="lead-notes">{locale === "ar" ? "ملاحظة مختصرة" : "Brief note"}</label>
            <input id="lead-notes" className="input" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="flex items-end">
            {/* Table 5: the save action is «حفظ وتحويل» — it converts the lead to
                the receiving company's manager. */}
            <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ وتحويل" : "Save and convert"}</button>
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
                {LEAD_STATUSES.map((s) => (
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
            {/* §5.1: the fourth narrowing control is «المتابعة». A lead with no
                follow-up date and one whose date has passed are different
                states, so the filter offers both plus a specific date. */}
            <div>
              <label className="label" htmlFor="filter-follow">{locale === "ar" ? "المتابعة" : "Follow-up"}</label>
              <select id="filter-follow" className="input" value={followUpFilter} onChange={(e) => setFollowUpFilter(e.target.value)}>
                <option value="">{locale === "ar" ? "الكل" : "All"}</option>
                <option value="due">{locale === "ar" ? "حان موعدها" : "Due now"}</option>
                <option value="scheduled">{locale === "ar" ? "مجدولة" : "Scheduled"}</option>
                <option value="none">{locale === "ar" ? "بلا موعد" : "No date"}</option>
                {[...new Set(rows.map((r) => r.follow_up_at).filter((s): s is string => Boolean(s)))].sort().map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </>
        }
        filter={(r) => {
          if (companyFilter && String(r.company_id) !== companyFilter) return false;
          if (statusFilter && r.status !== statusFilter) return false;
          if (sourceFilter && r.source !== sourceFilter) return false;
          if (followUpFilter === "none" && r.follow_up_at) return false;
          if (followUpFilter === "scheduled" && (!r.follow_up_at || r.follow_up_at < today)) return false;
          if (followUpFilter === "due" && (!r.follow_up_at || r.follow_up_at > today)) return false;
          if (followUpFilter && !["none", "scheduled", "due"].includes(followUpFilter) && r.follow_up_at !== followUpFilter) return false;
          return true;
        }}
        actions={(row) => (
          <div className="flex flex-wrap items-center gap-2">
            {can("lead:manage") && (
              <>
                {/* Table 6: «تحديث» opens a modal with the status and a note. */}
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setUpdateFor(row);
                    setUpdateStatus(row.status);
                    setUpdateNote(row.notes ?? "");
                  }}
                >
                  {locale === "ar" ? "تحديث" : "Update"}
                </button>
                <select
                  className="input w-auto"
                  aria-label={locale === "ar" ? "تغيير الحالة" : "Change status"}
                  value={row.status}
                  onChange={(e) => void advanceStatus(row.id, e.target.value)}
                >
                  {LEAD_STATUSES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <select
                  className="input w-auto"
                  aria-label={locale === "ar" ? "إسناد إلى" : "Assign to"}
                  value={row.assigned_to_id ?? ""}
                  onChange={(e) => void assignTo(row.id, e.target.value)}
                >
                  <option value="">{locale === "ar" ? "— بلا مسؤول —" : "— Unassigned —"}</option>
                  {people.map((p) => (
                    <option key={p.id} value={p.id}>{locale === "ar" ? p.full_name_ar : p.full_name_en}</option>
                  ))}
                </select>
              </>
            )}
          </div>
        )}
      />

      {/* Table 6: «تحديث» — the lead's own status and note, saved in its record. */}
      {updateFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <form onSubmit={saveUpdate} className="card w-full max-w-md space-y-4">
            <h2 className="section-title">{locale === "ar" ? "تحديث العميل المحتمل" : "Update the lead"}</h2>
            <p className="muted">{updateFor.name}</p>
            <div>
              <label className="label" htmlFor="lead-update-status">{locale === "ar" ? "الحالة" : "Status"}</label>
              <select
                id="lead-update-status"
                className="input"
                value={updateStatus}
                onChange={(e) => setUpdateStatus(e.target.value)}
              >
                {LEAD_STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="lead-update-note">{locale === "ar" ? "ملاحظة" : "Note"}</label>
              <textarea
                id="lead-update-note"
                className="input min-h-20"
                value={updateNote}
                onChange={(e) => setUpdateNote(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-ghost" onClick={() => setUpdateFor(null)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ" : "Save"}</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

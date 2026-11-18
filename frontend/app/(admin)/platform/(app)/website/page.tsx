"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";
import { AuthImage } from "@/components/AuthImage";
import { api, loadError, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Submission = {
  id: number;
  kind: string;
  name: string;
  email: string;
  phone: string | null;
  message: string | null;
  service_type: string | null;
  country: string | null;
  subject: string | null;
  expertise: string | null;
  company_id: number | null;
  attachment_file_id: number | null;
  attachment_name: string | null;
  status: string;
  converted_type: string | null;
  converted_id: number | null;
  created_at: string;
};

// §6.5: the inbox shows a kind chip per record.
const KIND_LABELS: Record<string, { ar: string; en: string }> = {
  service_request: { ar: "طلب خدمة", en: "Service request" },
  opportunity: { ar: "فرصة", en: "Opportunity" },
  job_application: { ar: "طلب انضمام", en: "Job application" },
  contact: { ar: "تواصل", en: "Contact" },
};

// §6.5: the four internal service types used to route a converted request.
const SERVICE_TYPES = [
  { value: "accounting", ar: "محاسبة", en: "Accounting" },
  { value: "design", ar: "تصميم", en: "Design" },
  { value: "study", ar: "دراسة أو مساعدة", en: "Study or help" },
  { value: "marketing", ar: "تسويق واستشارة تسويقية", en: "Marketing and consulting" },
];

export default function WebsitePage() {
  const { locale, can } = useAuth();
  const [rows, setRows] = useState<Submission[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState<Company | null>(null);
  const [profile, setProfile] = useState({ activity_ar: "", activity_en: "", website_url: "" });
  // §6.5: the details modal and the per-kind "take action" modal.
  const [details, setDetails] = useState<Submission | null>(null);
  const [routing, setRouting] = useState<Submission | null>(null);
  const [routeForm, setRouteForm] = useState({ company_id: "", service_type: "study" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Submission[]>("/api/v1/website/submissions"));
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

  // §6.5 / Table 7: each kind has its own toast, because the effect differs —
  // an opportunity becomes a draft for internal review, a join request goes for
  // human review only (no user is created).
  const CONVERT_TOAST: Record<string, { ar: string; en: string }> = {
    service_request: { ar: "تم توجيه طلب الخدمة إلى الشركة والمختص.", en: "The service request was routed to the company and specialist." },
    opportunity: { ar: "تم توجيه الفرصة للمراجعة مع المرفق.", en: "Opportunity routed for review with attachment." },
    job_application: { ar: "أُرسل الطلب للمراجعة البشرية.", en: "Application sent for human review." },
    lead: { ar: "تم التحويل إلى سجل داخلي.", en: "Converted to an internal record." },
  };

  async function convert(id: number, target: string, extra: Record<string, unknown> = {}) {
    setMessage(null);
    try {
      await api.post(`/api/v1/website/submissions/${id}/convert`, { target, ...extra });
      const toast = CONVERT_TOAST[target] ?? CONVERT_TOAST.lead;
      setMessage(locale === "ar" ? toast.ar : toast.en);
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(
        err.status === 409
          ? locale === "ar"
            ? "تم تحويل هذا الطلب مسبقاً."
            : "This submission was already converted."
          : locale === "ar"
            ? "فشل التحويل."
            : "Conversion failed.",
      );
    }
  }

  // §6.5: «مراجعة واتخاذ إجراء» — the effect depends on the submission kind.
  function takeAction(r: Submission) {
    if (r.kind === "service_request") {
      setRouteForm({ company_id: r.company_id ? String(r.company_id) : "", service_type: "study" });
      setRouting(r);
      return;
    }
    if (r.kind === "opportunity") {
      void convert(r.id, "opportunity");
      return;
    }
    if (r.kind === "job_application") {
      void convert(r.id, "job_application");
      return;
    }
    void convert(r.id, "lead");
  }

  async function routeSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!routing) return;
    setRouting(null);
    await convert(routing.id, "service_request", {
      company_id: routeForm.company_id ? Number(routeForm.company_id) : null,
      service_type: routeForm.service_type,
    });
  }

  async function reject(id: number) {
    setMessage(null);
    try {
      await api.post(`/api/v1/website/submissions/${id}/reject`);
      setMessage(locale === "ar" ? "تم رفض الطلب." : "Submission rejected.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر رفض الطلب." : "Could not reject the submission.");
    }
  }

  async function toggleVisibility(companyId: number, next: boolean) {
    setMessage(null);
    try {
      await api.patch(`/api/v1/website/companies/${companyId}/visibility`, { public_visible: next });
      setMessage(locale === "ar" ? "تم تحديث الظهور العام." : "Public visibility updated.");
      setCompanies(await api.get<Company[]>("/api/v1/companies"));
    } catch {
      setMessage(locale === "ar" ? "تعذّر تحديث الظهور." : "Could not update visibility.");
    }
  }

  // Table 7: edit the public activity text and the optional live-site link.
  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setMessage(null);
    try {
      await api.patch(`/api/v1/website/companies/${editing.id}/profile`, {
        public_activity_ar: profile.activity_ar || null,
        public_activity_en: profile.activity_en || null,
        website_url: profile.website_url || null,
      });
      setMessage(locale === "ar" ? "تم حفظ البيانات العامة." : "Public profile saved.");
      setEditing(null);
      setCompanies(await api.get<Company[]>("/api/v1/companies"));
    } catch {
      setMessage(locale === "ar" ? "تعذّر حفظ البيانات العامة." : "Could not save the public profile.");
    }
  }

  // Table 7: «تعديل الشعار» — reuse the file endpoint and the company logo field.
  async function uploadLogo(companyId: number, file: File) {
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("company_id", String(companyId));
      const stored = await api.upload<{ id: number }>("/api/v1/files", form);
      await api.patch(`/api/v1/companies/${companyId}`, { logo_file_id: stored.id });
      setMessage(locale === "ar" ? "تم رفع الشعار." : "Logo uploaded.");
      setCompanies(await api.get<Company[]>("/api/v1/companies"));
    } catch {
      setMessage(locale === "ar" ? "تعذّر رفع الشعار. تأكد من أن الملف صورة." : "The logo upload failed. Make sure the file is an image.");
    }
  }

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{locale === "ar" ? "إدارة الموقع" : "Website management"}</h1>
        <p className="muted">
          {locale === "ar"
            ? "نماذج الموقع العام محفوظة في المنصة. تصميم الموقع العام نفسه غير محدد في المرجع، لذا فهو مؤقت."
            : "Public form submissions are stored in the platform. The public site's own design is not specified by the reference, so it is provisional."}
        </p>
        {can("site:manage") && (
          <a className="btn-ghost mt-3 inline-flex" href="/platform/website/content">
            {locale === "ar" ? "تحرير محتوى الموقع" : "Edit website content"}
          </a>
        )}
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      <div className="card mb-4">
        <h2 className="section-title mb-1">{locale === "ar" ? "ملخص البيانات" : "Data summary"}</h2>
        <p className="muted">
          {locale === "ar"
            ? `وارد النماذج: ${rows.length} — خدمات: ${rows.filter((r) => r.kind === "service_request").length} — فرص: ${rows.filter((r) => r.kind === "opportunity").length} — سير ذاتية: ${rows.filter((r) => r.kind === "job_application").length} — بانتظار التحويل: ${rows.filter((r) => r.status === "new").length}`
            : `Submissions: ${rows.length} — services: ${rows.filter((r) => r.kind === "service_request").length} — opportunities: ${rows.filter((r) => r.kind === "opportunity").length} — CVs: ${rows.filter((r) => r.kind === "job_application").length} — awaiting conversion: ${rows.filter((r) => r.status === "new").length}`}
        </p>
      </div>

      <h2 className="section-title mb-3">{locale === "ar" ? "وارد النماذج (خدمة، فرصة، سيرة ذاتية)" : "Form inbox (service, opportunity, CV)"}</h2>
      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "النوع" : "Kind"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "ملخص البيانات" : "Data summary"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "المرفق" : "Attachment"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="p-3">
                    <span className="chip-neutral">{locale === "ar" ? KIND_LABELS[r.kind]?.ar ?? r.kind : KIND_LABELS[r.kind]?.en ?? r.kind}</span>
                  </td>
                  <td className="p-3">
                    <p>{r.name}</p>
                    <p className="muted" dir="ltr">{r.email}{r.phone ? ` · ${r.phone}` : ""}</p>
                    {r.message && <p className="muted max-w-xs truncate">{r.message}</p>}
                  </td>
                  <td className="p-3">
                    {r.attachment_file_id
                      ? <span className="chip-ok" dir="ltr">{r.attachment_name ?? `#${r.attachment_file_id}`}</span>
                      : <span className="muted">—</span>}
                  </td>
                  <td className="p-3"><StatusChip value={r.status} /></td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      {/* §6.5: «التفاصيل والمرفق» — a modal with every field sent. */}
                      <button type="button" className="btn-ghost" onClick={() => setDetails(r)}>
                        {locale === "ar" ? "التفاصيل والمرفق" : "Details and attachment"}
                      </button>
                      {r.status === "new" && can("website:manage") && (
                        <button type="button" className="btn-primary" onClick={() => takeAction(r)}>
                          {locale === "ar" ? "مراجعة واتخاذ إجراء" : "Review and take action"}
                        </button>
                      )}
                      {r.status === "converted" && (
                        <span className="muted" dir="ltr">{r.converted_type}{r.converted_id ? ` #${r.converted_id}` : ""}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>

      {can("website:manage") && (
        <>
          <h2 className="section-title mb-3 mt-6">{locale === "ar" ? "الشركات المعروضة في الموقع" : "Companies shown on the website"}</h2>
          <div className="card table-scroll p-0">
            <table className="w-full min-w-[680px] border-collapse">
              <thead>
                <tr className="border-b border-line bg-pearl">
                  <th className="p-3 text-start">{locale === "ar" ? "الشركة" : "Company"}</th>
                  <th className="p-3 text-start">{locale === "ar" ? "الشعار" : "Logo"}</th>
                  <th className="p-3 text-start">{locale === "ar" ? "النشاط" : "Activity"}</th>
                  <th className="p-3 text-start">{locale === "ar" ? "الدولة" : "Country"}</th>
                  <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                  <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.id} className="border-b border-line last:border-0">
                    <td className="p-3">{locale === "ar" ? c.name_ar : c.name_en}</td>
                    <td className="p-3">
                      {c.logo_url ? (
                        <AuthImage path={c.logo_url} alt="" className="h-8 w-8 rounded object-contain" />
                      ) : (
                        <span className="chip-warn">{locale === "ar" ? "بلا شعار" : "No logo"}</span>
                      )}
                    </td>
                    <td className="p-3">
                      {locale === "ar"
                        ? (c.public_activity_ar ?? <span className="chip-warn">{locale === "ar" ? "غير مضاف" : "Not added"}</span>)
                        : (c.public_activity_en ?? <span className="chip-warn">Not added</span>)}
                    </td>
                    <td className="p-3">{c.country ?? "—"}</td>
                    <td className="p-3"><StatusChip value={c.status} /></td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="btn-ghost" onClick={() => void toggleVisibility(c.id, !c.public_visible)}>
                          {c.public_visible ? (locale === "ar" ? "إخفاء" : "Hide") : locale === "ar" ? "إظهار" : "Show"}
                        </button>
                        {/* Table 7: «تعديل النشاط» — the public activity text and link. */}
                        <button type="button" className="btn-ghost" onClick={() => { setProfile({ activity_ar: c.public_activity_ar ?? "", activity_en: c.public_activity_en ?? "", website_url: c.website_url ?? "" }); setEditing(c); }}>
                          {locale === "ar" ? "تعديل النشاط" : "Edit activity"}
                        </button>
                        {/* Table 7: «تعديل الشعار» — upload a logo image. */}
                        <label className="btn-ghost cursor-pointer">
                          {locale === "ar" ? "تعديل الشعار" : "Edit logo"}
                          <input
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) void uploadLogo(c.id, file);
                            }}
                          />
                        </label>
                        <a className="btn-ghost" href={`/platform/companies/${c.id}`}>{locale === "ar" ? "تعديل" : "Edit"}</a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* §6.5: «التفاصيل والمرفق» — a modal with every field sent, plus a
          "take action" button that appears for a new record only. */}
      {details && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <div className="card w-full max-w-lg space-y-3">
            <h2 className="section-title">{locale === "ar" ? "التفاصيل والمرفق" : "Details and attachment"}</h2>
            <dl className="grid gap-2 sm:grid-cols-2">
              {([
                ["kind", locale === "ar" ? "النوع" : "Kind", locale === "ar" ? KIND_LABELS[details.kind]?.ar ?? details.kind : KIND_LABELS[details.kind]?.en ?? details.kind],
                ["name", locale === "ar" ? "الاسم" : "Name", details.name],
                ["email", locale === "ar" ? "البريد" : "Email", details.email],
                ["phone", locale === "ar" ? "الهاتف" : "Phone", details.phone ?? "—"],
                ["service_type", locale === "ar" ? "نوع الخدمة" : "Service type", details.service_type ?? "—"],
                ["country", locale === "ar" ? "الدولة" : "Country", details.country ?? "—"],
                ["subject", locale === "ar" ? "الموضوع" : "Subject", details.subject ?? "—"],
                ["expertise", locale === "ar" ? "مجال الخبرة" : "Expertise", details.expertise ?? "—"],
                ["attachment", locale === "ar" ? "المرفق" : "Attachment", details.attachment_name ?? (details.attachment_file_id ? `#${details.attachment_file_id}` : "—")],
              ] as const).map(([k, label, value]) => (
                <div key={k}>
                  <dt className="muted">{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            {details.message && <p className="rounded-control bg-pearl p-3">{details.message}</p>}
            <div className="flex flex-wrap gap-2">
              {details.status === "new" && can("website:manage") && (
                <button type="button" className="btn-primary" onClick={() => { const r = details; setDetails(null); takeAction(r); }}>
                  {locale === "ar" ? "اتخاذ إجراء" : "Take action"}
                </button>
              )}
              {details.status === "new" && can("website:manage") && (
                <button type="button" className="btn-ghost" onClick={() => { const r = details; setDetails(null); void reject(r.id); }}>
                  {locale === "ar" ? "رفض" : "Reject"}
                </button>
              )}
              <button type="button" className="btn-ghost" onClick={() => setDetails(null)}>
                {locale === "ar" ? "إغلاق" : "Close"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* §6.5: «توجيه طلب الخدمة» — the receiving company and the service type. */}
      {routing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <form onSubmit={routeSubmit} className="card w-full max-w-lg space-y-4">
            <h2 className="section-title">{locale === "ar" ? "توجيه طلب الخدمة" : "Route the service request"}</h2>
            <div>
              <label className="label" htmlFor="rt-company">{locale === "ar" ? "الشركة المستلمة" : "Receiving company"}</label>
              <select id="rt-company" className="input" required value={routeForm.company_id} onChange={(e) => setRouteForm({ ...routeForm, company_id: e.target.value })}>
                <option value="">—</option>
                {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="rt-service">{locale === "ar" ? "نوع الخدمة" : "Service type"}</label>
              <select id="rt-service" className="input" value={routeForm.service_type} onChange={(e) => setRouteForm({ ...routeForm, service_type: e.target.value })}>
                {SERVICE_TYPES.map((s) => (<option key={s.value} value={s.value}>{locale === "ar" ? s.ar : s.en}</option>))}
              </select>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">{locale === "ar" ? "تحويل" : "Convert"}</button>
              <button type="button" className="btn-ghost" onClick={() => setRouting(null)}>{locale === "ar" ? "إلغاء" : "Cancel"}</button>
            </div>
          </form>
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <form onSubmit={saveProfile} className="card w-full max-w-lg space-y-4">
            <h2 className="section-title">{locale === "ar" ? "البيانات العامة للشركة" : "Company public profile"}</h2>
            <div>
              <label className="label" htmlFor="pa-ar">{locale === "ar" ? "النشاط بالعربية" : "Activity (Arabic)"}</label>
              <input id="pa-ar" className="input" dir="rtl" value={profile.activity_ar} onChange={(e) => setProfile({ ...profile, activity_ar: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="pa-en">{locale === "ar" ? "النشاط بالإنجليزية" : "Activity (English)"}</label>
              <input id="pa-en" className="input" dir="ltr" value={profile.activity_en} onChange={(e) => setProfile({ ...profile, activity_en: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="pa-url">{locale === "ar" ? "رابط الموقع المباشر (اختياري)" : "Live site link (optional)"}</label>
              <input id="pa-url" className="input" dir="ltr" value={profile.website_url} onChange={(e) => setProfile({ ...profile, website_url: e.target.value })} />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ" : "Save"}</button>
              <button type="button" className="btn-ghost" onClick={() => setEditing(null)}>{locale === "ar" ? "إلغاء" : "Cancel"}</button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

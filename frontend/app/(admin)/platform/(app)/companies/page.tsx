"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, loadError, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthImage } from "@/components/AuthImage";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";
import { CompanyWizard } from "@/components/CompanyWizard";

export default function CompaniesPage() {
  const { locale, can } = useAuth();
  const router = useRouter();
  const [rows, setRows] = useState<Company[]>([]);
  const [closedOnly, setClosedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  // §6.2 / design p.7: «إضافة شركة» opens the four-step wizard over this screen.
  const [wizardOpen, setWizardOpen] = useState(false);
  // §6.3: the logo modal and the close-confirmation modal.
  const [logoFor, setLogoFor] = useState<Company | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [closeFor, setCloseFor] = useState<Company | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = closedOnly ? "?status=closed" : "";
      setRows(await api.get<Company[]>(`/api/v1/companies${query}`));
    } catch (e) {
      setError(loadError(e, locale));
    } finally {
      setLoading(false);
    }
  }, [closedOnly, locale]);

  useEffect(() => {
    void load();
  }, [load]);

  async function action(id: number, verb: string) {
    setBusyId(id);
    try {
      await api.post(`/api/v1/companies/${id}/${verb}`);
      await load();
    } catch {
      // The backend rejects unauthorized transitions; the reload reflects reality.
    } finally {
      setBusyId(null);
    }
  }

  // §6.3: «تغيير شعار الشركة» — choose an image file, then cancel or save.
  async function saveLogo(e: React.FormEvent) {
    e.preventDefault();
    if (!logoFor || !logoFile) return;
    try {
      const body = new FormData();
      body.append("file", logoFile);
      body.append("company_id", String(logoFor.id));
      const stored = await api.upload<{ id: number }>("/api/v1/files", body);
      await api.patch(`/api/v1/companies/${logoFor.id}`, { logo_file_id: stored.id });
      setMessage(locale === "ar" ? "تم حفظ الشعار." : "Logo saved.");
      setLogoFor(null);
      setLogoFile(null);
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر رفع الشعار. تأكد من أن الملف صورة." : "The logo upload failed. Make sure the file is an image.");
    }
  }

  async function confirmClose() {
    if (!closeFor) return;
    await action(closeFor.id, "close");
    setCloseFor(null);
  }

  const nameOf = (c: Company) => (locale === "ar" ? c.name_ar : c.name_en);
  const managerOf = (c: Company) => (locale === "ar" ? c.manager_name_ar : c.manager_name_en) ?? "—";

  return (
    <section>
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="page-title">{locale === "ar" ? "الشركات" : "Companies"}</h1>
          <p className="muted">
            {locale === "ar"
              ? "الشركات النشطة والمسودات. يعيّن المالك مديرًا من المستخدمين ذوي دور مدير الشركة."
              : "Active companies and drafts. The owner assigns a manager from users holding the company-manager role."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-ghost" onClick={() => void load()}>
            {locale === "ar" ? "تحديث القائمة" : "Refresh listing"}
          </button>
          <button
            type="button"
            className={closedOnly ? "btn-gold" : "btn-ghost"}
            aria-pressed={closedOnly}
            onClick={() => setClosedOnly((v) => !v)}
          >
            {closedOnly
              ? (locale === "ar" ? "عرض الشركات النشطة" : "Show active companies")
              : (locale === "ar" ? "عرض الشركات المغلقة فقط" : "Show closed companies only")}
          </button>
          {can("company:manage") && (
            <button type="button" className="btn-primary" onClick={() => setWizardOpen(true)}>
              {locale === "ar" ? "إضافة شركة" : "Add company"}
            </button>
          )}
        </div>
      </header>

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[900px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                {[
                  { ar: "الشعار", en: "Logo" },
                  { ar: "الكود", en: "Code" },
                  { ar: "الشركة", en: "Company" },
                  { ar: "الدولة والقطاع", en: "Country and sector" },
                  { ar: "البريد والهاتف", en: "Email and phone" },
                  { ar: "المدير", en: "Manager" },
                  { ar: "الملكية", en: "Ownership" },
                  { ar: "الحالة", en: "Status" },
                  { ar: "الإجراءات", en: "Actions" },
                ].map((c) => (
                  <th key={c.en} className="p-3 text-start section-title">
                    {locale === "ar" ? c.ar : c.en}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0">
                  <td className="p-3">
                    {c.logo_url ? (
                      <AuthImage path={c.logo_url} alt={nameOf(c)} className="h-8 w-8 rounded object-contain" />
                    ) : (
                      <span className="muted">{locale === "ar" ? "بلا شعار" : "No logo"}</span>
                    )}
                  </td>
                  <td className="p-3" dir="ltr">{c.code}</td>
                  <td className="p-3">{nameOf(c)}</td>
                  <td className="p-3">
                    {c.country} — {c.sector}
                  </td>
                  <td className="p-3" dir="ltr">
                    {c.contact_email ?? "—"}
                    {c.contact_phone ? ` · ${c.contact_phone}` : ""}
                  </td>
                  <td className="p-3">{managerOf(c)}</td>
                  <td className="p-3 tabular-nums" dir="ltr">
                    {Number(c.ownership_percent) === 0
                      ? locale === "ar" ? "إدارة فقط (0%)" : "Managed only (0%)"
                      : `${c.ownership_percent}%`}
                  </td>
                  <td className="p-3">
                    <StatusChip value={c.status} />
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button type="button" className="btn-ghost" onClick={() => router.push(`/platform/companies/${c.id}`)}>
                        {locale === "ar" ? "عرض التفاصيل" : "View details"}
                      </button>
                      {/* §6.3: «الشعار» — a change-logo modal. */}
                      {can("company:manage") && c.status !== "closed" && (
                        <button type="button" className="btn-ghost" onClick={() => { setLogoFile(null); setLogoFor(c); }}>
                          {locale === "ar" ? "الشعار" : "Logo"}
                        </button>
                      )}
                      {c.status === "draft" && can("company:manage") && (
                        <button
                          type="button"
                          className="btn-gold"
                          disabled={busyId === c.id}
                          onClick={() => void action(c.id, "activate")}
                        >
                          {locale === "ar" ? "تفعيل" : "Activate"}
                        </button>
                      )}
                      {c.status === "active" && can("company:manage") && (
                        <button
                          type="button"
                          className="btn-bad"
                          disabled={busyId === c.id}
                          onClick={() => setCloseFor(c)}
                        >
                          {locale === "ar" ? "إغلاق" : "Close"}
                        </button>
                      )}
                      {c.status === "closed" && (
                        <>
                          {/* Table 4: a closed company's previous reports stay in the archive. */}
                          <button type="button" className="btn-ghost" onClick={() => router.push(`/platform/reports?company=${c.id}`)}>
                            {locale === "ar" ? "التقارير المؤرشفة" : "Archived reports"}
                          </button>
                          {can("company:manage") && (
                            <button
                              type="button"
                              className="btn-gold"
                              disabled={busyId === c.id}
                              onClick={() => void action(c.id, "reactivate")}
                            >
                              {locale === "ar" ? "إعادة تفعيل" : "Reactivate"}
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>

      {wizardOpen && (
        <CompanyWizard
          onClose={() => setWizardOpen(false)}
          onSaved={() => {
            setWizardOpen(false);
            setMessage(locale === "ar" ? "أُضيفت الشركة." : "The company was added.");
            void load();
          }}
        />
      )}

      {message && <p role="status" className="mt-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      {/* §6.3: «تغيير شعار الشركة» — choose an image, cancel or save. */}
      {logoFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <form onSubmit={saveLogo} className="card w-full max-w-md space-y-4">
            <h2 className="section-title">{locale === "ar" ? "تغيير شعار الشركة" : "Change the company logo"}</h2>
            <p className="muted">{nameOf(logoFor)}</p>
            <input type="file" accept="image/*" className="input" onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)} />
            <div className="flex gap-2">
              <button type="submit" className="btn-primary" disabled={!logoFile}>{locale === "ar" ? "حفظ" : "Save"}</button>
              <button type="button" className="btn-ghost" onClick={() => { setLogoFor(null); setLogoFile(null); }}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* §6.3: «إغلاق الشركة؟» — a confirmation before the company is archived. */}
      {closeFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <div className="card w-full max-w-md space-y-4">
            <h2 className="section-title">{locale === "ar" ? "إغلاق الشركة؟" : "Close the company?"}</h2>
            <p className="muted">
              {locale === "ar"
                ? "تختفي من القوائم والتقارير والتنبيهات، ويبقى سجلها في الأرشيف، دون تصفية قانونية أو محاسبية."
                : "It disappears from the lists, reports and alerts, while its record stays in the archive — with no legal or accounting liquidation."}
            </p>
            <p>{nameOf(closeFor)}</p>
            <div className="flex gap-2">
              <button type="button" className="btn-ghost" onClick={() => setCloseFor(null)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button type="button" className="btn-bad" onClick={() => void confirmClose()}>
                {locale === "ar" ? "تأكيد الإغلاق" : "Confirm close"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

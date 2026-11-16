"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthImage } from "@/components/AuthImage";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

export default function CompaniesPage() {
  const { locale, can } = useAuth();
  const router = useRouter();
  const [rows, setRows] = useState<Company[]>([]);
  const [closedOnly, setClosedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = closedOnly ? "?status=closed" : "";
      setRows(await api.get<Company[]>(`/api/v1/companies${query}`));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
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
            {locale === "ar" ? "الشركات المغلقة فقط" : "Closed companies only"}
          </button>
          {can("company:manage") && (
            <Link className="btn-primary" href="/companies/new">
              {locale === "ar" ? "إضافة شركة" : "Add company"}
            </Link>
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
                      <button type="button" className="btn-ghost" onClick={() => router.push(`/companies/${c.id}`)}>
                        {locale === "ar" ? "عرض التفاصيل" : "View details"}
                      </button>
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
                          className="btn-ghost"
                          disabled={busyId === c.id}
                          onClick={() => void action(c.id, "close")}
                        >
                          {locale === "ar" ? "إغلاق" : "Close"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>
    </section>
  );
}

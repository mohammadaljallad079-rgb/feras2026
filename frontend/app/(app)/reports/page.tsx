"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ResourceTable, Column } from "@/components/ResourceTable";
import { StatusChip } from "@/components/StatusChip";
import { api, Company, MonthlyReport, ReportingPeriod } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ReportsPage() {
  const { locale, can } = useAuth();
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [periods, setPeriods] = useState<ReportingPeriod[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [periodId, setPeriodId] = useState("");
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
    api.get<ReportingPeriod[]>("/api/v1/periods").then(setPeriods).catch(() => undefined);
  }, []);

  async function createReport() {
    if (!companyId || !periodId) return;
    setCreating(true);
    setMessage(null);
    try {
      const created = await api.post<MonthlyReport>("/api/v1/reports", {
        company_id: Number(companyId),
        period_id: Number(periodId),
      });
      router.push(`/reports/${created.id}`);
    } catch (e) {
      const err = e as { status: number };
      setMessage(
        err.status === 409
          ? locale === "ar"
            ? "الفترة مغلقة أو يوجد تقرير قائم بالفعل."
            : "The period is closed or a report already exists."
          : locale === "ar"
            ? "تعذّر إنشاء التقرير."
            : "Could not create the report.",
      );
    } finally {
      setCreating(false);
    }
  }

  const columns: Column<MonthlyReport>[] = [
    { key: "id", headerAr: "الرقم", headerEn: "ID", numeric: true, render: (r) => r.id },
    {
      key: "company",
      headerAr: "الشركة",
      headerEn: "Company",
      render: (r) => companies.find((c) => c.id === r.company_id)?.[locale === "ar" ? "name_ar" : "name_en"] ?? r.company_id,
    },
    {
      key: "period",
      headerAr: "الفترة",
      headerEn: "Period",
      render: (r) => periods.find((p) => p.id === r.period_id)?.[locale === "ar" ? "label_ar" : "label_en"] ?? r.period_id,
    },
    { key: "currency", headerAr: "العملة", headerEn: "Currency", render: (r) => <span dir="ltr">{r.currency}</span> },
    { key: "status", headerAr: "الحالة", headerEn: "Status", render: (r) => <StatusChip value={r.status} /> },
    {
      key: "submitted",
      headerAr: "تاريخ الإرسال",
      headerEn: "Submitted",
      numeric: true,
      render: (r) => <span dir="ltr">{r.submitted_at ? r.submitted_at.slice(0, 10) : "—"}</span>,
    },
  ];

  return (
    <>
      <p className="muted mb-4">{locale === "ar" ? "تُعرض المبالغ بعملة كل شركة؛ لا تُجمع عملات مختلفة في إجمالي واحد." : "Amounts are shown per company currency; different currencies are never summed into one total."}</p>
      {message && (
        <p role="alert" className="mb-4 rounded-control border border-warn bg-warnbg p-3 text-warn">
          {message}
        </p>
      )}
      {can("report:create") && (
        <div className="card mb-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="label" htmlFor="company">{locale === "ar" ? "الشركة" : "Company"}</label>
            <select id="company" className="input w-auto" value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
              <option value="">—</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {locale === "ar" ? c.name_ar : c.name_en}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="period">{locale === "ar" ? "فترة التقرير" : "Reporting period"}</label>
            <select id="period" className="input w-auto" value={periodId} onChange={(e) => setPeriodId(e.target.value)}>
              <option value="">—</option>
              {periods.map((p) => (
                <option key={p.id} value={p.id}>
                  {locale === "ar" ? p.label_ar : p.label_en}
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="btn-primary" onClick={() => void createReport()} disabled={creating || !companyId || !periodId}>
            {locale === "ar" ? "فتح فترة التقرير" : "Open reporting period"}
          </button>
        </div>
      )}
      <ResourceTable<MonthlyReport>
        titleAr="التقارير الشهرية"
        titleEn="Monthly reports"
        endpoint="/api/v1/reports"
        columns={columns}
        permission="report:view_own"
        actions={(row) => (
          <button type="button" className="btn-ghost" onClick={() => router.push(`/reports/${row.id}`)}>
            {locale === "ar" ? "فتح التقرير" : "Open report"}
          </button>
        )}
      />
    </>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ResourceTable, Column } from "@/components/ResourceTable";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function CompaniesPage() {
  const { locale, can } = useAuth();
  const router = useRouter();
  const [busyId, setBusyId] = useState<number | null>(null);

  async function action(id: number, verb: string, reload: () => void) {
    setBusyId(id);
    try {
      await api.post(`/api/v1/companies/${id}/${verb}`);
      reload();
    } catch {
      // The backend rejects unauthorized transitions; surface it via reload.
    } finally {
      setBusyId(null);
    }
  }

  const columns: Column<Company>[] = [
    { key: "code", headerAr: "رمز الشركة", headerEn: "Company code", render: (r) => <span dir="ltr">{r.code}</span> },
    {
      key: "name",
      headerAr: "الاسم",
      headerEn: "Name",
      render: (r) => (locale === "ar" ? r.name_ar : r.name_en),
    },
    { key: "country", headerAr: "الدولة", headerEn: "Country", render: (r) => r.country },
    { key: "sector", headerAr: "القطاع", headerEn: "Sector", render: (r) => r.sector },
    {
      key: "ownership",
      headerAr: "نسبة الملكية",
      headerEn: "Ownership",
      numeric: true,
      render: (r) => `${r.ownership_percent}%`,
    },
    { key: "currency", headerAr: "العملة", headerEn: "Currency", render: (r) => <span dir="ltr">{r.currency}</span> },
    { key: "status", headerAr: "الحالة", headerEn: "Status", render: (r) => <StatusChip value={r.status} /> },
  ];

  return (
    <ResourceTable<Company>
      titleAr="إدارة الشركات"
      titleEn="Companies management"
      endpoint="/api/v1/companies"
      columns={columns}
      permission="company:view"
      createHref="/companies/new"
      createLabelAr="شركة جديدة"
      createLabelEn="New company"
      actions={(row, reload) => (
        <>
          <button type="button" className="btn-ghost" onClick={() => router.push(`/companies/${row.id}`)}>
            {locale === "ar" ? "عرض التفاصيل" : "View details"}
          </button>
          {row.status === "draft" && can("company:activate") && (
            <button type="button" className="btn-gold" disabled={busyId === row.id} onClick={() => void action(row.id, "activate", reload)}>
              {locale === "ar" ? "تفعيل" : "Activate"}
            </button>
          )}
          {row.status === "active" && can("company:close") && (
            <button type="button" className="btn-ghost" disabled={busyId === row.id} onClick={() => void action(row.id, "close", reload)}>
              {locale === "ar" ? "إغلاق" : "Close"}
            </button>
          )}
        </>
      )}
    />
  );
}

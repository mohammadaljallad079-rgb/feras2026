"use client";

import { useEffect, useState } from "react";
import { api, Dashboard } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

export default function DashboardPage() {
  const { locale, me } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Dashboard>("/api/v1/dashboard")
      .then(setData)
      .catch(() => setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data."))
      .finally(() => setLoading(false));
  }, [locale]);

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{data ? (locale === "ar" ? data.title_ar : data.title_en) : "…"}</h1>
        <p className="muted">
          {me?.full_name_ar} — {me?.roles.join(" · ")}
        </p>
      </header>
      <DataStates loading={loading} error={error} empty={!data}>
        {data && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.cards.map((card) => (
                <article key={card.key} className="card">
                  <p className="muted">{locale === "ar" ? card.label_ar : card.label_en}</p>
                  <p className="mt-1 text-page font-semibold tabular-nums" dir="ltr">
                    {card.value}
                  </p>
                  {(card.hint_ar || card.hint_en) && (
                    <p className="mt-1 muted">{locale === "ar" ? card.hint_ar : card.hint_en}</p>
                  )}
                </article>
              ))}
            </div>

            {data.sections.length > 0 && (
              <div className="mt-6 space-y-4">
                {data.sections.map((section, i) => (
                  <article key={i} className="card table-scroll">
                    <h2 className="section-title mb-3">
                      {locale === "ar"
                        ? String((section.title_ar as string) ?? "")
                        : String((section.title_en as string) ?? "")}
                    </h2>
                    {Array.isArray(section.rows) && (
                      <table className="w-full min-w-[560px] border-collapse">
                        <thead>
                          <tr className="border-b border-line">
                            {(section.columns as { ar: string; en: string }[] | undefined)?.map((c) => (
                              <th key={c.en} className="p-2 text-start text-secondary">
                                {locale === "ar" ? c.ar : c.en}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {(section.rows as Record<string, unknown>[]).map((row, ri) => (
                            <tr key={ri} className="border-b border-line last:border-0">
                              {Object.entries(row).map(([k, v]) => (
                                <td key={k} className="p-2">
                                  {k === "status" ? <StatusChip value={String(v)} /> : String(v ?? "—")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </DataStates>
    </section>
  );
}

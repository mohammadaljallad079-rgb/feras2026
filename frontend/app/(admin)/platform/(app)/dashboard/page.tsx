"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, loadErrorState, Dashboard } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

type Section = {
  key?: string;
  title_ar: string;
  title_en: string;
  columns?: { ar: string; en: string }[];
  rows?: (string | number)[][];
};

export default function DashboardPage() {
  const { locale, me } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<{ label: string; due: string | null } | null>(null);

  useEffect(() => {
    api
      .get<Dashboard>("/api/v1/dashboard")
      .then(setData)
      .catch((e) => setError(loadErrorState(e, locale)))
      .finally(() => setLoading(false));
    api
      .get<{ period: { label: string; due: string | null } | null }>("/api/v1/dashboard/period")
      .then((r) => setPeriod(r.period))
      .catch(() => setPeriod(null));
  }, [locale]);

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{data ? (locale === "ar" ? data.title_ar : data.title_en) : "…"}</h1>
        {/* §5.1: the dashboard's own line names the working period and its
            deadline: «الفترة الحالية 2026-10 · الاستحقاق 2026-11-05». */}
        {period && (
          <p className="muted" dir={locale === "ar" ? "rtl" : "ltr"}>
            {locale === "ar"
              ? `الفترة الحالية ${period.label}${period.due ? ` · الاستحقاق ${period.due}` : ""}`
              : `Current period ${period.label}${period.due ? ` · due ${period.due}` : ""}`}
          </p>
        )}
        <p className="muted">
          {locale === "ar" ? me?.full_name_ar : me?.full_name_en || me?.full_name_ar} — {me?.roles.join(" · ")}
        </p>
      </header>
      <DataStates loading={loading} error={error} empty={!data}>
        {data && (
          <>
            {/* PDF p.22 / §7.5: the banner names the period, company and deadline
                and is coloured by the §2 alert tones — amber approaching, red late. */}
            {(data.banner_ar || data.banner_en) && (
              <p
                role="alert"
                className={`mb-4 rounded-control border p-3 ${
                  data.banner_tone === "bad"
                    ? "border-bad bg-badbg text-bad"
                    : data.banner_tone === "warn"
                      ? "border-warn bg-warnbg text-warn"
                      : "border-line bg-pearl"
                }`}
              >
                {locale === "ar" ? data.banner_ar : data.banner_en}
              </p>
            )}
            {/* PDF pp.22-24: the actions that start the monthly work. The
                manager's isolation probe is pulled out into its own «اختبار
                العزل» section below, as §5.2 describes it. */}
            {data.actions.some((a) => a.group !== "isolation") && (
              <div className="mb-4 flex flex-wrap gap-2">
                {data.actions
                  .filter((a) => a.group !== "isolation")
                  .map((a) => (
                    <Link key={a.href + a.label_en} href={a.href} className="btn-primary">
                      {locale === "ar" ? a.label_ar : a.label_en}
                    </Link>
                  ))}
              </div>
            )}
            {/* §5.2: «اختبار العزل» — a direct link to another company's report,
                which the server refuses and records in the audit log. */}
            {data.actions.some((a) => a.group === "isolation") && (
              <article className="card mb-4">
                <h2 className="section-title mb-2">{locale === "ar" ? "اختبار العزل" : "Isolation test"}</h2>
                <div className="flex flex-wrap gap-2">
                  {data.actions
                    .filter((a) => a.group === "isolation")
                    .map((a) => (
                      <Link key={a.href + a.label_en} href={a.href} className="btn-ghost">
                        {locale === "ar" ? a.label_ar : a.label_en}
                      </Link>
                    ))}
                </div>
              </article>
            )}
            {/* PDF p.5: each KPI is a link into the screen that owns the number. */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {data.cards.map((card) => {
                const inner = (
                  <>
                    <p className="muted">{locale === "ar" ? card.label_ar : card.label_en}</p>
                    <p className="mt-1 text-page font-semibold tabular-nums" dir="ltr">
                      {card.value}
                    </p>
                    {(card.hint_ar || card.hint_en) && (
                      <p className="mt-1 muted">{locale === "ar" ? card.hint_ar : card.hint_en}</p>
                    )}
                  </>
                );
                return card.href ? (
                  <Link key={card.key} href={card.href} className="card transition hover:border-gold">
                    {inner}
                  </Link>
                ) : (
                  <article key={card.key} className="card">
                    {inner}
                  </article>
                );
              })}
            </div>

            {data.sections.length > 0 && (
              <div className="mt-6 space-y-4">
                {data.sections.map((raw, i) => {
                  const section = raw as unknown as Section;
                  const columns = section.columns ?? [];
                  const rows = section.rows ?? [];
                  return (
                    <article key={section.key ?? i} className="card table-scroll">
                      <h2 className="section-title mb-3">
                        {locale === "ar" ? section.title_ar : section.title_en}
                      </h2>
                      {columns.length > 0 ? (
                        <table className="w-full min-w-[560px] border-collapse">
                          <thead>
                            <tr className="border-b border-line">
                              {columns.map((c) => (
                                <th key={c.en} className="p-2 text-start text-secondary">
                                  {locale === "ar" ? c.ar : c.en}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {rows.map((row, ri) => (
                              <tr key={ri} className="border-b border-line last:border-0">
                                {row.map((cell, ci) => (
                                  <td key={ci} className="p-2">
                                    {columns[ci]?.en === "Status" ? <StatusChip value={String(cell)} /> : String(cell ?? "—")}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <p className="muted">{locale === "ar" ? "لا سجلات" : "No records"}</p>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </>
        )}
      </DataStates>
    </section>
  );
}

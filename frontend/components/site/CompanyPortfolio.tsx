"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Locale, PublicCompany } from "@/lib/site";
import { logoUrl, pick } from "@/lib/site";

// §9 Table 11: the portfolio filters are the four sectors plus "all".
const FILTERS: { value: string; ar: string; en: string }[] = [
  { value: "", ar: "كل الشركات", en: "All companies" },
  { value: "تقنية", ar: "تقنية", en: "Technology" },
  { value: "صناعي", ar: "صناعي", en: "Industrial" },
  { value: "تجاري", ar: "تجاري", en: "Commercial" },
  { value: "خدمي", ar: "خدمي", en: "Services" },
];

// §9: the card and the preview modal both carry the company logo when one is
// published; otherwise the initials stand in. A broken image falls back too.
function CompanyMark({ company, size }: { company: PublicCompany; size: "sm" | "lg" }) {
  const [failed, setFailed] = useState(false);
  const src = logoUrl(company.logo_url);
  const box = size === "lg" ? "h-14 w-14" : "h-13 w-13";
  if (src && !failed) {
    return (
      <span className={`flex ${box} shrink-0 items-center justify-center overflow-hidden rounded-lg border border-brand-line bg-white p-1.5`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={company.name_en}
          className="h-full w-full object-contain"
          onError={() => setFailed(true)}
        />
      </span>
    );
  }
  return (
    <span className={`flex ${box} items-center justify-center rounded-lg bg-brand-deep p-3 text-[18px] font-bold text-white`}>
      {company.name_en.slice(0, 2).toUpperCase()}
    </span>
  );
}

/**
 * §9: the group-companies section. A filter narrows by sector, the card shows
 * the company's public data, clicking the name expands it, and «معاينة الشركة»
 * opens the public preview modal. Only public fields are ever rendered.
 */
export function CompanyPortfolio({
  companies,
  locale,
  showHeading = true,
}: {
  companies: PublicCompany[];
  locale: Locale;
  showHeading?: boolean;
}) {
  const ar = locale === "ar";
  const [sector, setSector] = useState("");
  const [preview, setPreview] = useState<PublicCompany | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const rows = useMemo(
    () => (sector ? companies.filter((c) => c.sector === sector) : companies),
    [companies, sector],
  );

  return (
    <div>
      {showHeading && (
        <>
          <span className="site-eyebrow">{ar ? "شركات المجموعة" : "Group companies"}</span>
          <h2 id="h-companies" className="site-h2">{ar ? "محفظة الشركات" : "Our portfolio"}</h2>
          <p className="site-lead">
            {ar
              ? "شركات متخصصة تعمل في قطاعات وأسواق مختلفة ضمن محفظة واحدة."
              : "Specialised companies operating across different sectors and markets within one portfolio."}
          </p>
        </>
      )}

      <ul className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label={ar ? "تصفية القطاع" : "Sector filter"}>
        {FILTERS.map((f) => (
          <li key={f.value}>
            <button
              type="button"
              role="tab"
              aria-selected={sector === f.value}
              onClick={() => setSector(f.value)}
              className={`rounded-full border px-4 py-1.5 text-[13.5px] font-semibold transition ${
                sector === f.value
                  ? "border-brand-deep bg-brand-deep text-white"
                  : "border-brand-line bg-white text-brand-slate hover:border-brand-deep"
              }`}
            >
              {ar ? f.ar : f.en}
            </button>
          </li>
        ))}
      </ul>

      {rows.length === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed border-brand-line bg-white p-9 text-center text-brand-slate">
          {ar ? "لا توجد شركات معروضة حالياً." : "No companies are shown at the moment."}
        </p>
      ) : (
        <ul className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((c, i) => {
            const name = ar ? c.name_ar : c.name_en;
            const activity = pick(locale, c.activity_ar, c.activity_en);
            const open = expanded === c.code;
            return (
              <li key={c.code} className="site-card">
                <div className="flex items-start justify-between gap-3">
                  <CompanyMark company={c} size="sm" />
                  <span className="tabular-nums text-[13px] font-bold text-brand-sand" dir="ltr">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setExpanded(open ? null : c.code)}
                  aria-expanded={open}
                  className="mt-5 w-fit text-start text-[18px] font-bold text-brand-ink"
                >
                  {name}
                </button>
                <p className="mt-1.5 text-[13.5px] text-brand-slate">{c.sector} · {c.country}</p>

                {open && (
                  <div className="mt-3 border-t border-brand-line pt-3 text-[13.5px] text-brand-slate">
                    <p>{activity || (ar ? "لم يُضف نشاط عام بعد." : "No public activity has been added yet.")}</p>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => setPreview(c)}
                  className="mt-5 block w-fit border-b-[1.5px] border-brand-sand pb-1 text-[14px] font-semibold text-brand-deep"
                >
                  {ar ? "معاينة الشركة" : "Company preview"} →
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <Link href={`/${locale}/companies`} className="site-btn site-btn-primary mt-8">
        {ar ? "كل الشركات" : "All companies"}
      </Link>

      {/* §9: the public preview modal — public fields only, never internal data. */}
      {preview && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={ar ? "معاينة الشركة" : "Company preview"}
          onClick={() => setPreview(null)}
        >
          <div className="w-full max-w-lg rounded-xl bg-white p-7 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start gap-4">
              <CompanyMark company={preview} size="lg" />
              <div>
                <h3 className="text-[19px] font-bold text-brand-ink">{ar ? preview.name_ar : preview.name_en}</h3>
                <p className="text-[13.5px] text-brand-slate">{preview.sector} · {preview.country}</p>
              </div>
            </div>

            <p className="mt-5 text-[14.5px] text-brand-ink">
              {pick(locale, preview.activity_ar, preview.activity_en) ||
                (ar ? "لم يُضف نشاط عام بعد." : "No public activity has been added yet.")}
            </p>

            <p className="mt-4 rounded-lg bg-brand-mist px-4 py-3 text-[13.5px] font-semibold text-brand-deep">
              {ar ? "شركة ضمن محفظة ستارت أب سفير القابضة" : "A company within the Start Up Sphere Holding portfolio"}
            </p>

            <p className="mt-4 text-[13.5px]">
              {preview.website_url ? (
                <a href={preview.website_url} className="font-semibold text-brand-deep underline" target="_blank" rel="noopener noreferrer" dir="ltr">
                  {preview.website_url}
                </a>
              ) : (
                <span className="text-brand-slate">
                  {ar ? "لا يوجد رابط موقع مستقل مضاف حاليًا" : "No standalone website link has been added yet"}
                </span>
              )}
            </p>

            <div className="mt-6 flex justify-end">
              <button type="button" onClick={() => setPreview(null)} className="site-btn site-btn-outline">
                {ar ? "إغلاق" : "Close"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

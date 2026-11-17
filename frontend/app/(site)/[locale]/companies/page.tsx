import type { Metadata } from "next";
import Link from "next/link";
import { getCompanies, type Locale } from "@/lib/site";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "شركات المجموعة" : "Group companies" };
}

export default async function CompaniesPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const companies = await getCompanies();
  const sectors = Array.from(new Set(companies.map((c) => c.sector))).sort();

  return (
    <section className="site-section">
      <div className="site-container">
        <span className="site-eyebrow">{ar ? "شركات المجموعة" : "Group companies"}</span>
        <h1 className="site-h2">{ar ? "محفظة الشركات" : "Our portfolio"}</h1>
        <p className="site-lead">
          {ar ? "تُعرض الشركات المنشورة فقط من قاعدة البيانات." : "Only companies published from the database are shown."}
        </p>

        {sectors.length > 0 && (
          <ul className="mt-6 flex flex-wrap gap-2">
            {sectors.map((s) => (
              <li key={s} className="rounded-full border border-brand-line bg-white px-4 py-1.5 text-[13.5px] font-semibold text-brand-slate">
                {s}
              </li>
            ))}
          </ul>
        )}

        {companies.length === 0 ? (
          <p className="mt-8 rounded-xl border border-dashed border-brand-line bg-white p-9 text-center text-brand-slate">
            {ar ? "لا توجد شركات منشورة حالياً." : "No published companies at the moment."}
          </p>
        ) : (
          <ul className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {companies.map((c) => (
              <li key={c.code} className="site-card">
                <span className="flex h-13 w-13 items-center justify-center rounded-lg bg-brand-deep p-3 text-[18px] font-bold text-white">
                  {c.name_en.slice(0, 2).toUpperCase()}
                </span>
                <h2 className="mt-5 text-[18px] font-bold">{ar ? c.name_ar : c.name_en}</h2>
                <p className="mt-1.5 text-[13.5px] text-brand-slate">{c.sector} · {c.country}</p>
                <span className="mt-3 inline-block rounded bg-[#f6eedd] px-2.5 py-1 text-[11.5px] font-bold uppercase tracking-wide text-[#8a6a2e]">
                  {c.sector}
                </span>
              </li>
            ))}
          </ul>
        )}

        <Link href={`/${locale}/service-request`} className="site-btn site-btn-primary mt-9">
          {ar ? "طلب خدمة" : "Request a service"}
        </Link>
      </div>
    </section>
  );
}

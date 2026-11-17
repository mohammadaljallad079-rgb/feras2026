import type { Metadata } from "next";
import Link from "next/link";
import { getSite, pick, sectionByKey, setting, type Locale } from "@/lib/site";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const ar = locale === "ar";
  return { title: ar ? "عن القابضة" : "About the holding" };
}

export default async function AboutPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const about = sectionByKey(site, "about");
  const country = setting(site, "country", locale);
  const brand = setting(site, "brand_name", locale);

  return (
    <section className="site-section">
      <div className="site-container">
        <span className="site-eyebrow">{ar ? "من نحن" : "About us"}</span>
        <h1 className="site-h2">{ar ? "عن القابضة" : "About the holding"}</h1>
        {about && <p className="site-lead">{pick(locale, about.body_ar, about.body_en)}</p>}

        <dl className="mt-10 grid gap-6 sm:grid-cols-3">
          <div className="site-card">
            <dt className="text-[13px] uppercase tracking-wider text-brand-slate">{ar ? "الشركة" : "Company"}</dt>
            <dd className="mt-2 text-[16px] font-semibold">{brand}</dd>
          </div>
          <div className="site-card">
            <dt className="text-[13px] uppercase tracking-wider text-brand-slate">{ar ? "الدولة" : "Country"}</dt>
            <dd className="mt-2 text-[16px] font-semibold">{country}</dd>
          </div>
          <div className="site-card">
            <dt className="text-[13px] uppercase tracking-wider text-brand-slate">{ar ? "النشاط" : "Activity"}</dt>
            <dd className="mt-2 text-[16px] font-semibold">
              {ar ? "إدارة وتطوير شركات المجموعة" : "Managing and developing group companies"}
            </dd>
          </div>
        </dl>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href={`/${locale}/companies`} className="site-btn site-btn-primary">
            {ar ? "شركات المجموعة" : "Group companies"}
          </Link>
          <Link href={`/${locale}/contact`} className="site-btn site-btn-outline">
            {ar ? "تواصل معنا" : "Contact us"}
          </Link>
        </div>
      </div>
    </section>
  );
}

import type { Metadata } from "next";
import { getCompanies, type Locale } from "@/lib/site";
import { CompanyPortfolio } from "@/components/site/CompanyPortfolio";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "شركات المجموعة" : "Group companies" };
}

export default async function CompaniesPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const companies = await getCompanies();

  return (
    <section className="site-section">
      <div className="site-container">
        <span className="site-eyebrow">{ar ? "شركات المجموعة" : "Group companies"}</span>
        <h1 className="site-h2">{ar ? "محفظة الشركات" : "Our portfolio"}</h1>
        <p className="site-lead">
          {ar ? "تُعرض الشركات المنشورة فقط من قاعدة البيانات." : "Only companies published from the database are shown."}
        </p>
        <div className="mt-6">
          <CompanyPortfolio companies={companies} locale={locale} showHeading={false} />
        </div>
      </div>
    </section>
  );
}

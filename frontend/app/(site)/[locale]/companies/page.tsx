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
        <span className="site-eyebrow">{ar ? "محفظة المجموعة" : "Group portfolio"}</span>
        <h1 className="site-h2">{ar ? "شركات المجموعة" : "Group companies"}</h1>
        <p className="site-lead">
          {ar
            ? "شركات متخصصة تعمل في قطاعات وأسواق مختلفة ضمن محفظة واحدة."
            : "Specialised companies operating in different sectors and markets within one portfolio."}
        </p>
        <div className="mt-6">
          <CompanyPortfolio companies={companies} locale={locale} showHeading={false} />
        </div>
      </div>
    </section>
  );
}

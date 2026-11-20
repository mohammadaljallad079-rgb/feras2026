import type { Metadata } from "next";
import { getSite, setting, type Locale } from "@/lib/site";
import { PublicForm } from "@/components/site/PublicForm";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "الفرص التجارية والاستثمارية" : "Opportunities" };
}

export default async function OpportunitiesPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const notice = setting(site, "opportunity_notice", locale);

  return (
    <section className="site-section">
      <div className="site-container grid gap-12 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <span className="site-eyebrow">{ar ? "الفرص" : "Opportunities"}</span>
          <h1 className="site-h2">{ar ? "قدّم فرصة تجارية أو استثمارية" : "Submit a commercial or investment opportunity"}</h1>
          <p className="site-lead">
            {ar
              ? "أرسل وصفًا موجزًا وحدد دولة المشروع، ويمكنك إرفاق ملف الدراسة."
              : "Send a brief description, specify the project country, and you may attach a study file."}
          </p>
          {notice && (
            <p className="mt-6 flex gap-3 rounded-lg border border-[#ede2cc] border-s-4 border-s-brand-sand bg-[#fbf7ef] p-5 text-[14px] text-[#6a5731]">
              <span aria-hidden="true">⚠</span>
              <span>
                <strong className="font-semibold">{ar ? "تنبيه: " : "Notice: "}</strong>
                {notice}
              </span>
            </p>
          )}
        </div>
        <PublicForm
          kind="opportunity"
          locale={locale}
          countries={site.opportunity_countries}
          file={{ label: "study", required: false }}
          consentHref={`/${locale}/privacy`}
        />
      </div>
    </section>
  );
}

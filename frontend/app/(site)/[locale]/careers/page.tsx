import type { Metadata } from "next";
import { getSite, pick, sectionByKey, type Locale } from "@/lib/site";
import { PublicForm } from "@/components/site/PublicForm";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "الوظائف" : "Careers" };
}

export default async function CareersPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const section = sectionByKey(site, "careers");

  return (
    <section className="site-section">
      <div className="site-container grid gap-12 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <span className="site-eyebrow">{pick(locale, section?.title_ar, section?.title_en) || (ar ? "الوظائف" : "Careers")}</span>
          <h1 className="site-h2">
            {pick(locale, section?.body_ar, section?.body_en) ||
              (ar ? "هل ترغب في الانضمام إلى فريقنا؟" : "Would you like to join our team?")}
          </h1>
          <p className="site-lead">
            {ar
              ? "أرسل سيرتك الذاتية ومجال اهتمامك. سنتواصل معك إذا توفرت فرصة مناسبة."
              : "Send your CV and area of interest. We will contact you if a suitable opportunity becomes available."}
          </p>
        </div>
        <PublicForm
          kind="job_application"
          locale={locale}
          file={{ label: "cv", required: true }}
          consentHref={`/${locale}/privacy`}
        />
      </div>
    </section>
  );
}

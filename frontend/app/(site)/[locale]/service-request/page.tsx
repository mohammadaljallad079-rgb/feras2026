import type { Metadata } from "next";
import { getSite, pick, sectionByKey, type Locale } from "@/lib/site";
import { PublicForm } from "@/components/site/PublicForm";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "طلب خدمة" : "Service request" };
}

export default async function ServiceRequestPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const section = sectionByKey(site, "service_request");

  return (
    <section className="site-section">
      <div className="site-container grid gap-12 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <span className="site-eyebrow">{ar ? "طلب خدمة" : "Service request"}</span>
          <h1 className="site-h2">
            {pick(locale, section?.title_ar, section?.title_en) || (ar ? "اطلب خدمات المجموعة" : "Request the group's services")}
          </h1>
          <p className="site-lead">
            {ar
              ? "يُحفظ الطلب في قاعدة البيانات ويصل مباشرة إلى فريق المجموعة."
              : "Your request is saved in the database and reaches the group's team directly."}
          </p>
          <ul className="mt-8 grid gap-3">
            {site.services.map((s) => (
              <li key={s.id} className="flex items-start gap-3 text-[15px]">
                <span aria-hidden="true" className="mt-2 h-2 w-2 shrink-0 rotate-45 bg-brand-sand" />
                {pick(locale, s.name_ar, s.name_en)}
              </li>
            ))}
          </ul>
        </div>
        <PublicForm
          kind="service_request"
          locale={locale}
          services={site.services.map((s) => ({ id: s.id, name_ar: s.name_ar, name_en: s.name_en }))}
          consentHref={`/${locale}/privacy`}
        />
      </div>
    </section>
  );
}

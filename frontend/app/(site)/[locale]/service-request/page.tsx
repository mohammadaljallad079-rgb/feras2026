import type { Metadata } from "next";
import { getSite, pick, type Locale } from "@/lib/site";
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

  return (
    <section className="site-section">
      <div className="site-container grid gap-12 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <span className="site-eyebrow">{ar ? "طلب خدمة" : "Service request"}</span>
          <h1 className="site-h2">{ar ? "اطلب خدمة من المجموعة" : "Request a service from the group"}</h1>
          <p className="site-lead">
            {ar
              ? "أرسل بياناتك الأساسية، وسيراجع الفريق طلبك ويوجهه للجهة المناسبة."
              : "Send your basic details; the team will review your request and route it to the right party."}
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

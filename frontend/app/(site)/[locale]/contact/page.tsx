import type { Metadata } from "next";
import { getSite, setting, type Locale } from "@/lib/site";
import { PublicForm } from "@/components/site/PublicForm";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "تواصل معنا" : "Contact us" };
}

export default async function ContactPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const email = setting(site, "contact_email", locale);
  const phone = setting(site, "contact_phone", locale);
  const country = setting(site, "country", locale);

  return (
    <section className="site-section">
      <div className="site-container grid gap-12 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <span className="site-eyebrow">{ar ? "تواصل" : "Contact"}</span>
          <h1 className="site-h2">{ar ? "تواصل معنا" : "Contact us"}</h1>
          <p className="site-lead">
            {ar ? "أرسل استفسارك وسيصل مباشرة إلى فريق المجموعة." : "Send your enquiry and it will reach the group's team directly."}
          </p>
          <dl className="mt-8 grid gap-4">
            {country && (
              <div><dt className="text-[13px] uppercase tracking-wider text-brand-slate">{ar ? "الدولة" : "Country"}</dt>
                <dd className="mt-1 text-[15px]">{country}</dd></div>
            )}
            {email && (
              <div><dt className="text-[13px] uppercase tracking-wider text-brand-slate">{ar ? "البريد الإلكتروني" : "Email"}</dt>
                <dd className="mt-1"><a className="text-brand-deep underline" href={`mailto:${email}`}>{email}</a></dd></div>
            )}
            {phone && (
              <div><dt className="text-[13px] uppercase tracking-wider text-brand-slate">{ar ? "الهاتف" : "Phone"}</dt>
                <dd className="mt-1"><a className="text-brand-deep underline" href={`tel:${phone.replace(/\s+/g, "")}`} dir="ltr">{phone}</a></dd></div>
            )}
          </dl>
        </div>
        <PublicForm kind="contact" locale={locale} consentHref={`/${locale}/privacy`} />
      </div>
    </section>
  );
}

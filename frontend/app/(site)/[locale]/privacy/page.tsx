import type { Metadata } from "next";
import { setting, getSite, pick, type Locale } from "@/lib/site";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "سياسة الخصوصية" : "Privacy policy" };
}

/**
 * Privacy policy, rendered from §13 of the approved content deck through the
 * public API. The deck marks the text as awaiting legal review, so the review
 * note is shown above the sections.
 */
export default async function PrivacyPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const email = setting(site, "contact_email", locale);
  const cr = setting(site, "commercial_register", locale);

  const intro = pick(locale, site.privacy.intro.ar, site.privacy.intro.en);
  const reviewNote = pick(locale, site.privacy.review_note.ar, site.privacy.review_note.en);
  const sections = site.privacy.sections.map((s) => ({
    h: pick(locale, s.title.ar, s.title.en),
    p: pick(locale, s.body.ar, s.body.en),
  }));


  return (
    <section className="site-section">
      <div className="site-container max-w-[820px]">
        <span className="site-eyebrow">{ar ? "قانوني" : "Legal"}</span>
        <h1 className="site-h2">{ar ? "سياسة الخصوصية" : "Privacy policy"}</h1>
        <p className="site-lead">{intro}</p>

        <dl className="mt-6 grid gap-2 rounded-lg border border-brand-line bg-brand-mist p-5 text-[14px] sm:grid-cols-2">
          <div>
            <dt className="text-brand-slate">{ar ? "مسؤول معالجة البيانات" : "Data controller"}</dt>
            <dd className="font-semibold">{ar ? "شركة ستارت أب سفير القابضة ذ.م.م" : "START UP SPHERE HOLDING CO W.L.L"}</dd>
          </div>
          {cr && (
            <div>
              <dt className="text-brand-slate">{ar ? "السجل التجاري" : "Commercial registration"}</dt>
              <dd className="font-semibold" dir="ltr">{cr}</dd>
            </div>
          )}
          {email && (
            <div>
              <dt className="text-brand-slate">{ar ? "البريد الإلكتروني" : "Email"}</dt>
              <dd className="font-semibold" dir="ltr">{email}</dd>
            </div>
          )}
        </dl>

        <p className="mt-6 rounded-lg border border-[#ede2cc] border-s-4 border-s-brand-sand bg-[#fbf7ef] p-5 text-[14px] text-[#6a5731]">
          {reviewNote}
        </p>

        <div className="mt-9 grid gap-6">
          {sections.map((s) => (
            <div key={s.h}>
              <h2 className="text-[18px] font-bold">{s.h}</h2>
              <p className="mt-2 text-[15px] text-brand-slate">{s.p}</p>
            </div>
          ))}
        </div>

        {email && (
          <p className="mt-9 text-[15px]">
            {ar ? "للتواصل: " : "Contact: "}
            <a className="text-brand-deep underline" href={`mailto:${email}`}>{email}</a>
          </p>
        )}
      </div>
    </section>
  );
}

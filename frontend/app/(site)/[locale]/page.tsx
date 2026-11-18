import Link from "next/link";
import { getCompanies, getSite, pick, sectionByKey, setting, type Locale } from "@/lib/site";
import { HeroSlider } from "@/components/site/HeroSlider";
import { CompanyPortfolio } from "@/components/site/CompanyPortfolio";

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const [site, companies] = await Promise.all([getSite(), getCompanies()]);
  const about = sectionByKey(site, "about");
  const solutions = sectionByKey(site, "solutions");
  const opportunities = sectionByKey(site, "opportunities");
  const careers = sectionByKey(site, "careers");
  const notice = setting(site, "opportunity_notice", locale);
  const l = (path: string) => `/${locale}${path}`;

  return (
    <>
      <HeroSlider locale={locale} slides={site.slides} />

      {/* About */}
      <section className="site-section bg-white" aria-labelledby="h-about">
        <div className="site-container grid items-center gap-14 lg:grid-cols-2">
          <div className="relative min-h-[380px] overflow-hidden rounded-xl bg-gradient-to-br from-brand-deep to-brand-ink">
            <div
              aria-hidden="true"
              className="absolute inset-0 opacity-40 [background:repeating-linear-gradient(135deg,rgba(255,255,255,.06)_0_2px,transparent_2px_22px),radial-gradient(420px_260px_at_70%_20%,rgba(12,143,173,.5),transparent_60%)]"
            />
            <div className="absolute bottom-6 start-6 rounded-lg bg-white/95 px-4 py-3 shadow-lg">
              <span className="block text-[11px] font-bold uppercase tracking-wider text-brand-sand">
                {ar ? "مجموعة واحدة" : "One group"}
              </span>
              <span className="text-[13px] font-semibold text-brand-deep">
                {ar ? "خبرات متكاملة ضمن رؤية موحدة" : "Integrated expertise under one vision"}
              </span>
            </div>
          </div>
          <div>
            <span className="site-eyebrow">{pick(locale, about?.title_ar, about?.title_en) || (ar ? "من نحن" : "About us")}</span>
            <h2 id="h-about" className="site-h2">
              {ar ? "نطوّر شركات المجموعة وننسّق خبراتها." : "We develop the group's companies and coordinate their expertise."}
            </h2>
            {about && (
              <p className="site-lead">{pick(locale, about.body_ar, about.body_en)}</p>
            )}
            <ul className="mt-6 grid gap-3">
              {(ar
                ? ["تطوير شركات المجموعة", "تنسيق الخبرات", "ربط العملاء بالخدمات والفرص"]
                : ["Developing the group's companies", "Coordinating expertise", "Connecting clients with services and opportunities"]
              ).map((item) => (
                <li key={item} className="flex items-start gap-3 text-[15px] text-brand-ink">
                  <span aria-hidden="true" className="mt-2 h-2 w-2 shrink-0 rotate-45 bg-brand-sand" />
                  {item}
                </li>
              ))}
            </ul>
            <Link href={l("/about")} className="site-btn site-btn-outline mt-7">
              {ar ? "المزيد عن القابضة" : "More about the holding"}
            </Link>
          </div>
        </div>
      </section>

      {/* Group companies — from the database, published ones only */}
      <section className="site-section bg-brand-mist" aria-labelledby="h-companies">
        <div className="site-container">
          <CompanyPortfolio companies={companies} locale={locale} />
        </div>
      </section>

      {/* Solutions — the six approved services */}
      <section className="site-section bg-white" aria-labelledby="h-solutions">
        <div className="site-container">
          <span className="site-eyebrow">{pick(locale, solutions?.title_ar, solutions?.title_en) || (ar ? "منظومة الحلول" : "Solutions ecosystem")}</span>
          <h2 id="h-solutions" className="site-h2">
            {ar
              ? "حلول أعمال تبدأ من احتياجك وتمتد إلى فرص النمو."
              : "Business solutions that start from your need and extend to growth."}
          </h2>
          <ul className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {site.services.map((s) => (
              <li key={s.id} className="site-card flex flex-col">
                <span aria-hidden="true" className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#eadfc8] bg-[#f4efe5] text-[20px] text-[#8a6a2e]">
                  ◆
                </span>
                <h3 className="mt-5 text-[17px] font-bold leading-snug">{pick(locale, s.name_ar, s.name_en)}</h3>
                {(s.description_ar || s.description_en) && (
                  <p className="mt-2 text-[14px] text-brand-slate">{pick(locale, s.description_ar, s.description_en)}</p>
                )}
                <Link href={`${l("/service-request")}?service=${encodeURIComponent(s.slug)}`} className="site-btn site-btn-outline mt-6 w-fit">
                  {ar ? "طلب الخدمة" : "Request service"}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Service request band */}
      <section className="bg-gradient-to-br from-brand-deep to-brand-ink py-20 text-white" aria-labelledby="h-sr">
        <div className="site-container grid items-center gap-12 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <span className="site-eyebrow">{ar ? "طلب خدمة" : "Service request"}</span>
            <h2 id="h-sr" className="site-h2 text-white">
              {ar ? "اطلب خدمات المجموعة عبر نموذج مباشر." : "Request the group's services through a direct form."}
            </h2>
            <p className="mt-4 max-w-[560px] text-[#c9dbe2]">
              {ar
                ? "يُحفظ الطلب في قاعدة البيانات ويصل مباشرة إلى فريق المجموعة."
                : "Your request is saved in the database and reaches the group's team directly."}
            </p>
            <Link href={l("/service-request")} className="site-btn site-btn-sand mt-7">
              {ar ? "ابدأ طلب الخدمة" : "Start a service request"}
            </Link>
          </div>
          <ul className="rounded-xl border border-white/15 bg-white/[0.06] p-7 text-[14.5px]">
            {(ar
              ? ["الاسم", "البريد الإلكتروني", "رقم التواصل", "نوع الخدمة", "وصف مختصر", "الموافقة على سياسة الخصوصية"]
              : ["Name", "Email", "Contact number", "Service type", "Brief description", "Privacy-policy consent"]
            ).map((row) => (
              <li key={row} className="flex justify-between border-b border-white/10 py-3 last:border-0">
                <span className="text-[#a9b6c9]">{row}</span>
                <span aria-hidden="true">—</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Opportunities */}
      <section className="site-section bg-brand-mist" aria-labelledby="h-opp">
        <div className="site-container">
          <span className="site-eyebrow">{pick(locale, opportunities?.title_ar, opportunities?.title_en) || (ar ? "الفرص" : "Opportunities")}</span>
          <h2 id="h-opp" className="site-h2">
            {ar ? "الفرص التجارية والاستثمارية" : "Business and investment opportunities"}
          </h2>
          <div className="mt-9 grid gap-6 md:grid-cols-2">
            <div className="site-card">
              <h3 className="text-[19px] font-bold">{ar ? "أرسل فرصتك إلى المجموعة" : "Send your opportunity to the group"}</h3>
              <p className="mt-3 text-[15px] text-brand-slate">
                {ar ? "شاركنا تفاصيل الفرصة التجارية أو الاستثمارية لدراستها." : "Share the details of your commercial or investment opportunity for review."}
              </p>
              <Link href={l("/opportunities")} className="site-btn site-btn-primary mt-5">
                {ar ? "أرسل فرصة" : "Submit an opportunity"}
              </Link>
            </div>
            <div className="site-card">
              <h3 className="text-[19px] font-bold">{ar ? "كيف تُدرس الفرص؟" : "How are opportunities reviewed?"}</h3>
              <p className="mt-3 text-[15px] text-brand-slate">
                {ar
                  ? "تُستقبل الفرص وتُسجّل في قاعدة البيانات ثم تُراجع من الفريق المختص."
                  : "Opportunities are received, recorded in the database, and reviewed by the relevant team."}
              </p>
            </div>
          </div>
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
      </section>

      {/* Careers */}
      <section className="site-section bg-white" aria-labelledby="h-careers">
        <div className="site-container">
          <div className="rounded-2xl border border-brand-line bg-brand-mist p-12 text-center">
            <h2 id="h-careers" className="text-[28px] font-bold">
              {pick(locale, careers?.title_ar, careers?.title_en) || (ar ? "هل ترغب في الانضمام إلى فريقنا؟" : "Would you like to join our team?")}
            </h2>
            <p className="mt-3 text-brand-slate">
              {ar ? "أرسل سيرتك الذاتية وسنراها في المجموعة." : "Send your CV and it will be reviewed within the group."}
            </p>
            <Link href={l("/careers")} className="site-btn site-btn-sand mt-6">
              {ar ? "قدّم طلب انضمام" : "Submit an application"}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

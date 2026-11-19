import type { Metadata } from "next";
import Link from "next/link";
import { getSite, pick, sectionByKey, type Locale } from "@/lib/site";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "منظومة الحلول" : "Solutions" };
}

export default async function SolutionsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const solutions = sectionByKey(site, "solutions");

  return (
    <section className="site-section">
      <div className="site-container">
        <span className="site-eyebrow">{pick(locale, solutions?.title_ar, solutions?.title_en) || (ar ? "منظومة الحلول" : "Solutions")}</span>
        <h1 className="site-h2">
          {ar ? "حلول أعمال تبدأ من احتياجك وتمتد إلى فرص النمو." : "Business solutions that start from your need and extend to growth."}
        </h1>
        {solutions && (solutions.body_ar || solutions.body_en) && (
          <p className="site-lead">{pick(locale, solutions.body_ar, solutions.body_en)}</p>
        )}

        <ul className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {site.services.map((s) => (
            <li key={s.id} className="site-card flex flex-col">
              <span aria-hidden="true" className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#eadfc8] bg-[#f4efe5] text-[20px] text-[#8a6a2e]">◆</span>
              <h2 className="mt-5 text-[17px] font-bold leading-snug">{pick(locale, s.name_ar, s.name_en)}</h2>
              {(s.description_ar || s.description_en) ? (
                <p className="mt-2 text-[14px] text-brand-slate">{pick(locale, s.description_ar, s.description_en)}</p>
              ) : (
                <p className="mt-2 text-[13px] text-brand-slate">
                  {ar ? "التفاصيل عند الطلب." : "Details available on request."}
                </p>
              )}
              <Link href={`/${locale}/service-request?service=${encodeURIComponent(s.slug)}`} className="site-btn site-btn-outline mt-6 w-fit">
                {ar ? "اطلب خدمة" : "Request a service"}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * 404 inside the site chrome for an unknown path under a valid locale.
 * The route segment exposes no params here, so the language comes from the path.
 */
export default function LocaleNotFound() {
  const ar = !usePathname()?.startsWith("/en");

  return (
    <section className="site-section">
      <div className="site-container text-center">
        <p className="text-[13px] font-bold uppercase tracking-widest text-brand-sand">404</p>
        <h1 className="mt-4 text-[28px] font-bold">
          {ar ? "الصفحة غير موجودة" : "Page not found"}
        </h1>
        <p className="mt-3 text-brand-slate">
          {ar
            ? "ربما نُقلت الصفحة أو تغيّر رابطها. عد إلى الصفحة الرئيسية."
            : "The page may have moved or its address changed. Return to the home page."}
        </p>
        <div className="mt-7 flex justify-center gap-3">
          <Link href={ar ? "/ar" : "/en"} className="site-btn site-btn-primary">
            {ar ? "الصفحة الرئيسية" : "Home page"}
          </Link>
          <Link href={ar ? "/en" : "/ar"} className="site-btn site-btn-outline" hrefLang={ar ? "en" : "ar"}>
            {ar ? "English" : "العربية"}
          </Link>
        </div>
      </div>
    </section>
  );
}

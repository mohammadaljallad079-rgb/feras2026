"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BrandMark } from "@/components/BrandMark";
import { pick, setting, type Locale, type SiteBootstrap } from "@/lib/site";

/**
 * Public-site header: brand, navigation, the two primary calls to action and a
 * language switch. Navigation and labels come from the CMS, so the menu is
 * edited in the admin rather than in code.
 */
export function SiteHeader({ locale, site }: { locale: Locale; site: SiteBootstrap }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const ar = locale === "ar";

  const nav = site.header_nav;
  const brand =
    setting(site, "brand_short", locale) ||
    (ar ? "ستارت أب سفير القابضة" : "Start Up Sphere Holding");
  // §9: the full legal name in the top strip, distinct from the short header brand.
  const legalName =
    setting(site, "brand_name", locale) ||
    (ar ? "شركة ستارت أب سفير القابضة ذ.م.م" : "START UP SPHERE HOLDING CO W.L.L");
  const country = setting(site, "country", locale);
  const isActive = (href: string) => {
    const full = `/${locale}${href === "/" ? "" : href}`;
    return pathname === full || (href !== "/" && pathname.startsWith(full));
  };
  const other: Locale = ar ? "en" : "ar";
  const swapped = pathname.replace(new RegExp(`^/${locale}`), `/${other}`);

  return (
    <header className="site-header">
      {/* §9: the top strip shows «مملكة البحرين · ستارت أب سفير القابضة ذ.م.م». */}
      {country && (
        <div className="border-b border-brand-line bg-brand-mist">
          <div className="site-container flex h-8 items-center justify-center text-[12.5px] text-brand-slate">
            <span>
              {country} · {legalName}
            </span>
          </div>
        </div>
      )}
      <div className="site-container flex h-[74px] items-center gap-6">
        <Link href={`/${locale}`} className="flex items-center gap-3 no-underline" aria-label={brand}>
          <BrandMark name={brand} size={40} tone="onCard" plate="none" />
        </Link>

        <nav
          className="ms-auto hidden items-center gap-6 nav:flex"
          aria-label={ar ? "التنقل الرئيسي" : "Main navigation"}
        >
          {nav.map((link) => (
            <Link
              key={link.id}
              href={`/${locale}${link.href === "/" ? "" : link.href}`}
              className="site-nav-link"
              aria-current={isActive(link.href) ? "page" : undefined}
            >
              {pick(locale, link.label_ar, link.label_en)}
            </Link>
          ))}
        </nav>

        <div className="ms-auto flex items-center gap-2 nav:ms-0">
          <Link
            href={swapped}
            className="site-btn site-btn-outline !px-3 !py-2 text-[13px]"
            hrefLang={other}
            aria-label={ar ? "Switch to English" : "التبديل إلى العربية"}
          >
            {ar ? "English" : "العربية"}
          </Link>
          <Link
            href={`/${locale}/service-request`}
            className="site-btn site-btn-primary hidden sm:inline-flex"
          >
            {ar ? "طلب خدمة" : "Request a service"}
          </Link>
          {/* §9: the top menu carries two buttons — request a service and
              submit an opportunity. */}
          <Link
            href={`/${locale}/opportunities`}
            className="site-btn site-btn-outline hidden lg:inline-flex"
          >
            {ar ? "تقديم فرصة" : "Submit an opportunity"}
          </Link>
          <button
            type="button"
            className="site-btn site-btn-outline !px-3 !py-2 nav:hidden"
            aria-expanded={open}
            aria-controls="site-mobile-nav"
            onClick={() => setOpen((v) => !v)}
          >
            <span className="sr-only">{ar ? "القائمة" : "Menu"}</span>
            <span aria-hidden="true">☰</span>
          </button>
        </div>
      </div>

      {open && (
        <nav
          id="site-mobile-nav"
          className="border-t border-brand-line nav:hidden"
          aria-label={ar ? "التنقل" : "Navigation"}
        >
          <div className="site-container flex flex-col py-2">
            {nav.map((link) => (
              <Link
                key={link.id}
                href={`/${locale}${link.href === "/" ? "" : link.href}`}
                className="border-b border-brand-line py-3 text-[15px] no-underline"
                onClick={() => setOpen(false)}
              >
                {pick(locale, link.label_ar, link.label_en)}
              </Link>
            ))}
            <Link
              href={`/${locale}/service-request`}
              className="site-btn site-btn-primary mt-3"
              onClick={() => setOpen(false)}
            >
              {ar ? "طلب خدمة" : "Request a service"}
            </Link>
            <Link
              href={`/${locale}/opportunities`}
              className="site-btn site-btn-outline mt-2"
              onClick={() => setOpen(false)}
            >
              {ar ? "تقديم فرصة" : "Submit an opportunity"}
            </Link>
            {country && <p className="py-3 text-[13px] text-brand-slate">{country}</p>}
          </div>
        </nav>
      )}
    </header>
  );
}

import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { pick, setting, type Locale, type SiteBootstrap } from "@/lib/site";

/** Public-site footer: brand, group links, contact details and legal line. */
export function SiteFooter({ locale, site }: { locale: Locale; site: SiteBootstrap }) {
  const ar = locale === "ar";
  const brand = setting(site, "brand_name", locale);
  const description = ar
    ? "شركة قابضة بحرينية تعمل على تطوير شركات المجموعة وربط الخبرات بفرص الأعمال والنمو."
    : "A Bahraini holding company that develops the group's companies and connects expertise with business and growth opportunities.";
  const email = setting(site, "contact_email", locale);
  const phone = setting(site, "contact_phone", locale);
  const country = setting(site, "country", locale);
  const year = new Date().getFullYear();

  return (
    <footer className="bg-brand-ink text-[#a9b7c2]">
      <div className="site-container grid gap-9 py-16 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <BrandMark name={brand} size={40} tone="onDark" plate="always" />
          {description && <p className="mt-4 max-w-[340px] text-[14px] leading-7">{description}</p>}
        </div>

        <nav aria-label={ar ? "الموقع" : "Site"}>
          <h2 className="mb-3 text-[13px] uppercase tracking-wider text-white">{ar ? "الموقع" : "Site"}</h2>
          {site.header_nav.map((link) => (
            <Link
              key={link.id}
              href={`/${locale}${link.href === "/" ? "" : link.href}`}
              className="block py-1 text-[14px] no-underline hover:text-brand-sand"
            >
              {pick(locale, link.label_ar, link.label_en)}
            </Link>
          ))}
        </nav>

        <nav aria-label={ar ? "الحلول" : "Solutions"}>
          <h2 className="mb-3 text-[13px] uppercase tracking-wider text-white">
            {ar ? "منظومة الحلول" : "Solutions"}
          </h2>
          {site.services.slice(0, 6).map((service) => (
            <Link
              key={service.id}
              href={`/${locale}/solutions`}
              className="block py-1 text-[14px] no-underline hover:text-brand-sand"
            >
              {pick(locale, service.name_ar, service.name_en)}
            </Link>
          ))}
        </nav>

        <div>
          <h2 className="mb-3 text-[13px] uppercase tracking-wider text-white">
            {ar ? "تواصل" : "Contact"}
          </h2>
          {country && <p className="py-1 text-[14px]">{country}</p>}
          {email && (
            <a href={`mailto:${email}`} className="block py-1 text-[14px] no-underline hover:text-brand-sand">
              {email}
            </a>
          )}
          {phone && (
            <a
              href={`tel:${phone.replace(/\s+/g, "")}`}
              dir="ltr"
              className="block py-1 text-[14px] no-underline hover:text-brand-sand"
            >
              {phone}
            </a>
          )}
          {site.footer_nav.map((link) => (
            <Link
              key={link.id}
              href={`/${locale}${link.href}`}
              className="block py-1 text-[14px] no-underline hover:text-brand-sand"
            >
              {pick(locale, link.label_ar, link.label_en)}
            </Link>
          ))}
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="site-container flex flex-wrap items-center justify-between gap-3 py-5 text-[13px]">
          <span>{`© ${year} ${brand}`}</span>
          {/* §9: the visitor site and the staff platform live on separate
              addresses; this is the discreet entry point to the login page. */}
          <Link
            href="/platform/login"
            className="no-underline hover:text-brand-sand"
            data-platform-link="login"
          >
            {ar ? "المنصة الداخلية" : "Staff platform"}
          </Link>
          {country && <span>{country}</span>}
        </div>
      </div>
    </footer>
  );
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import "../../globals.css";
import { dirOf, getSite, isLocale, siteOrigin, type Locale } from "@/lib/site";
import { SiteHeader } from "@/components/site/SiteHeader";
import { SiteFooter } from "@/components/site/SiteFooter";
import { OrganizationJsonLd } from "@/components/site/OrganizationJsonLd";

/**
 * Locale layout for the public website.
 *
 * This is a *nested root layout* (it renders `<html>`/`<body>`), which lets the
 * document carry the right `lang` and `dir` on the server — Arabic RTL by
 * default, English LTR — instead of correcting them on the client after
 * hydration. `notFound()` for any other first segment keeps unknown paths from
 * being treated as a locale.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const site = await getSite();
  const loc: Locale = isLocale(locale) ? locale : "ar";
  const title = loc === "ar" ? site.settings.seo_title?.ar : site.settings.seo_title?.en;
  const description =
    loc === "ar" ? site.settings.seo_description?.ar : site.settings.seo_description?.en;
  const origin = siteOrigin();
  return {
    metadataBase: new URL(origin),
    title: title ?? undefined,
    description: description ?? undefined,
    alternates: {
      canonical: `${origin}/${loc}`,
      languages: { ar: `${origin}/ar`, en: `${origin}/en` },
    },
    openGraph: {
      type: "website",
      siteName: (loc === "ar" ? site.settings.brand_name?.ar : site.settings.brand_name?.en) ?? undefined,
      title: title ?? undefined,
      description: description ?? undefined,
      locale: loc === "ar" ? "ar_BH" : "en_US",
      url: `${origin}/${loc}`,
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  // An unknown first segment is not a locale. Rendering the 404 here (rather
  // than calling notFound()) keeps a valid document shell, which a nested root
  // layout cannot get from a boundary above it.
  if (!isLocale(locale)) notFound();
  const site = await getSite();

  return (
    <html lang={locale} dir={dirOf(locale)}>
      <body className="site-root">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:z-[60] focus:m-3 focus:rounded focus:bg-brand-deep focus:px-4 focus:py-2 focus:text-white"
        >
          {locale === "ar" ? "انتقل إلى المحتوى" : "Skip to content"}
        </a>
        <SiteHeader locale={locale} site={site} />
        <main id="main">{children}</main>
        <SiteFooter locale={locale} site={site} />
        <OrganizationJsonLd locale={locale} />
      </body>
    </html>
  );
}


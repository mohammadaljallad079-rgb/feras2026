/**
 * Public-site data access and types.
 *
 * Content comes from the platform's CMS tables through the public API, so a
 * change made in the admin appears on the website without a deploy. Server
 * components fetch the backend directly; the browser posts forms through the
 * Next.js rewrite.
 */

export const LOCALES = ["ar", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "ar";

export const dirOf = (locale: Locale) => (locale === "ar" ? "rtl" : "ltr");
export const isLocale = (value: string): value is Locale =>
  (LOCALES as readonly string[]).includes(value);

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

/** Bilingual value as the API returns it. */
export type Bi = { ar: string | null; en: string | null };

export type SiteSection = {
  id: number;
  key: string;
  title_ar: string | null;
  title_en: string | null;
  body_ar: string | null;
  body_en: string | null;
  image_file_id: number | null;
  sort_order: number;
  is_visible: boolean;
  needs_review: boolean;
};

export type SiteSlide = {
  id: number;
  title_ar: string;
  title_en: string;
  body_ar: string | null;
  body_en: string | null;
  image_file_id: number | null;
  cta_primary_label_ar: string | null;
  cta_primary_label_en: string | null;
  cta_primary_href: string | null;
  cta_secondary_label_ar: string | null;
  cta_secondary_label_en: string | null;
  cta_secondary_href: string | null;
  sort_order: number;
  is_active: boolean;
};

export type SiteService = {
  id: number;
  slug: string;
  name_ar: string;
  name_en: string;
  description_ar: string | null;
  description_en: string | null;
  icon: string | null;
  sort_order: number;
  is_active: boolean;
  needs_review: boolean;
};

export type SiteNavLink = {
  id: number;
  location: string;
  label_ar: string;
  label_en: string;
  href: string;
  sort_order: number;
  is_active: boolean;
};

export type PublicCompany = {
  code: string;
  name_ar: string;
  name_en: string;
  sector: string;
  country: string;
  logo_url: string | null;
};

export type SiteBootstrap = {
  settings: Record<string, Bi>;
  sections: SiteSection[];
  slides: SiteSlide[];
  services: SiteService[];
  header_nav: SiteNavLink[];
  footer_nav: SiteNavLink[];
  opportunity_countries: Bi[];
};

/** Pick the current locale's value, falling back to the other language. */
export function pick(locale: Locale, ar?: string | null, en?: string | null): string {
  const value = locale === "ar" ? ar : en;
  return (value ?? (locale === "ar" ? en : ar) ?? "").trim();
}

export function bi(locale: Locale, value: Bi | undefined): string {
  if (!value) return "";
  return pick(locale, value.ar, value.en);
}

const EMPTY: SiteBootstrap = {
  settings: {},
  sections: [],
  slides: [],
  services: [],
  header_nav: [],
  footer_nav: [],
  opportunity_countries: [],
};

/**
 * Fetch the whole site content for one render. A backend outage yields empty
 * content rather than a crash: the layout still renders and the pages show
 * their own empty states.
 */
export async function getSite(): Promise<SiteBootstrap> {
  try {
    const res = await fetch(`${BACKEND}/api/v1/public/site`, { next: { revalidate: 30 } });
    if (!res.ok) return EMPTY;
    return (await res.json()) as SiteBootstrap;
  } catch {
    return EMPTY;
  }
}

export async function getCompanies(sector?: string): Promise<PublicCompany[]> {
  try {
    const url = new URL(`${BACKEND}/api/v1/public/companies`);
    if (sector) url.searchParams.set("sector", sector);
    const res = await fetch(url, { next: { revalidate: 30 } });
    if (!res.ok) return [];
    return (await res.json()) as PublicCompany[];
  } catch {
    return [];
  }
}

/** Absolute site origin, used for canonical URLs and structured data. */
export function siteOrigin(): string {
  return (process.env.SITE_ORIGIN || "https://sup-edu.com").replace(/\/$/, "");
}

export function sectionByKey(site: SiteBootstrap, key: string): SiteSection | undefined {
  return site.sections.find((s) => s.key === key);
}

export function setting(site: SiteBootstrap, key: string, locale: Locale): string {
  return bi(locale, site.settings[key]);
}

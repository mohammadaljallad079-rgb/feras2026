import type { MetadataRoute } from "next";
import { LOCALES, getCompanies, siteOrigin } from "@/lib/site";

const PATHS = ["", "/about", "/companies", "/solutions", "/opportunities", "/careers", "/service-request", "/contact", "/privacy"];

/**
 * Sitemap with hreflang alternates for every page in both languages. Company
 * pages are not listed individually because the public company view is a single
 * listing page fed from the database.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = siteOrigin();
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [];

  for (const path of PATHS) {
    for (const locale of LOCALES) {
      entries.push({
        url: `${origin}/${locale}${path}`,
        lastModified: now,
        changeFrequency: path === "" ? "weekly" : "monthly",
        priority: path === "" ? 1 : 0.7,
        alternates: {
          languages: {
            ar: `${origin}/ar${path}`,
            en: `${origin}/en${path}`,
          },
        },
      });
    }
  }

  // Touch the companies endpoint so the sitemap date reflects published data.
  await getCompanies();
  return entries;
}

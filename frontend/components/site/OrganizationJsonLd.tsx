import { getSite, setting, siteOrigin, type Locale } from "@/lib/site";

/**
 * Organization structured data. Only fields the CMS actually holds are
 * emitted, so the markup never asserts a value the owner has not published.
 */
export async function OrganizationJsonLd({ locale }: { locale: Locale }) {
  const site = await getSite();
  const origin = siteOrigin();
  const name = setting(site, "brand_name", locale);
  const description = setting(site, "seo_description", locale);
  const email = setting(site, "contact_email", locale);
  const phone = setting(site, "contact_phone", locale);
  const country = setting(site, "country", locale);

  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name,
    url: `${origin}/${locale}`,
    logo: `${origin}/brand/holding-logo.png`,
  };
  if (description) data.description = description;
  if (email || phone) {
    data.contactPoint = {
      "@type": "ContactPoint",
      contactType: "customer service",
      ...(email ? { email } : {}),
      ...(phone ? { telephone: phone } : {}),
      ...(country ? { areaServed: country } : {}),
    };
  }

  return (
    <script
      type="application/ld+json"
      // The payload is built from CMS values and serialised here; no user HTML
      // is interpolated.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

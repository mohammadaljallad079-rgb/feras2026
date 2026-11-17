import type { MetadataRoute } from "next";
import { siteOrigin } from "@/lib/site";

/**
 * robots.txt. The admin console (`/platform/*`) is disallowed because it is a
 * private application, and API routes are disallowed because they are not
 * content. The public site is allowed and points at the sitemap.
 */
export default function robots(): MetadataRoute.Robots {
  const origin = siteOrigin();
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/platform", "/platform/", "/api/"],
      },
    ],
    sitemap: `${origin}/sitemap.xml`,
    host: origin,
  };
}

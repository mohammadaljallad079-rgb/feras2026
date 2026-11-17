"use client";

import { useAuth } from "@/lib/auth";

/**
 * Application-wide loading state (reference page 32, item 10: «تصميم حالات
 * التحميل والخطأ العامة»). Rendered by the App Router while a route segment is
 * fetching, so a slow request shows a designed state rather than a blank page.
 */
export default function Loading() {
  const { locale } = useAuth();
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3" role="status" aria-live="polite">
      <span
        className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-gold"
        aria-hidden="true"
      />
      <p className="muted">{locale === "ar" ? "جارٍ التحميل…" : "Loading…"}</p>
    </div>
  );
}

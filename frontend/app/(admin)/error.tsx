"use client";

import { useEffect, useState } from "react";

/**
 * Application-wide error state (reference page 32, item 10: «تصميم حالات
 * التحميل والخطأ العامة»).
 *
 * The message is deliberately generic: a thrown error must never surface a
 * stack trace, a SQL statement or any protected record, matching the reference
 * security rule that an unauthorized read answers 403/404 without leaking
 * protected data.
 */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const [locale, setLocale] = useState<"ar" | "en">("ar");

  useEffect(() => {
    setLocale((document.documentElement.lang as "ar" | "en") === "en" ? "en" : "ar");
    // The digest is the only safe identifier to log; the message may carry data.
    console.error("Unhandled route error", error.digest ?? "");
  }, [error.digest]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6" role="alert">
      <div className="card w-full max-w-md border-bad bg-badbg p-6 text-center">
        <h1 className="section-title text-bad">
          {locale === "ar" ? "حدث خطأ غير متوقع" : "Something went wrong"}
        </h1>
        <p className="mt-2 text-secondary text-ink">
          {locale === "ar"
            ? "لم تكتمل العملية. أعد المحاولة، وإن تكرّر الخطأ فأبلغ مدير النظام."
            : "The operation did not complete. Try again, and if it repeats tell your administrator."}
        </p>
        <button type="button" className="btn-primary mt-4" onClick={reset}>
          {locale === "ar" ? "إعادة المحاولة" : "Try again"}
        </button>
      </div>
    </div>
  );
}

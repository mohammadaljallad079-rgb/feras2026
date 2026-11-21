import Link from "next/link";

/**
 * Global 404. Needed at the true app root because a nested root layout (the
 * public site's `[locale]` layout) cannot render a not-found boundary from an
 * ancestor. It carries its own document shell for that reason.
 */
export default function NotFound() {
  return (
    <html lang="ar" dir="rtl">
      <body className="site-root">
        <main className="site-container flex min-h-screen flex-col items-center justify-center text-center">
          <p className="text-[13px] font-bold uppercase tracking-widest text-brand-sand">404</p>
          <h1 className="mt-4 text-[28px] font-bold">الصفحة غير موجودة</h1>
          <p className="mt-3 text-brand-slate">
            ربما نُقلت الصفحة أو تغيّر رابطها. عد إلى الصفحة الرئيسية.
          </p>
          <p className="mt-2 text-brand-slate" dir="ltr">
            The page may have moved. Return to the home page.
          </p>
          <div className="mt-7 flex gap-3">
            <Link href="/ar" className="site-btn site-btn-primary">الصفحة الرئيسية</Link>
            <Link href="/en" className="site-btn site-btn-outline">Home page</Link>
          </div>
        </main>
      </body>
    </html>
  );
}

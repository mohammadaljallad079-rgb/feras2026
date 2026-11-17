import Link from "next/link";

/** 404 inside the site chrome for an unknown path under a valid locale. */
export default function LocaleNotFound() {
  return (
    <section className="site-section">
      <div className="site-container text-center">
        <p className="text-[13px] font-bold uppercase tracking-widest text-brand-sand">404</p>
        <h1 className="mt-4 text-[28px] font-bold">الصفحة غير موجودة / Page not found</h1>
        <p className="mt-3 text-brand-slate">
          الرابط الذي طلبته غير صحيح. / The address you requested is not valid.
        </p>
        <div className="mt-7 flex justify-center gap-3">
          <Link href="/ar" className="site-btn site-btn-primary">الصفحة الرئيسية</Link>
          <Link href="/en" className="site-btn site-btn-outline">Home page</Link>
        </div>
      </div>
    </section>
  );
}

"use client";

import { useAuth } from "@/lib/auth";
import { t } from "@/lib/i18n";

/** Loading / empty / error states used by every data screen. */
export function DataStates({
  loading,
  error,
  empty,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty: boolean;
  children: React.ReactNode;
}) {
  const { locale } = useAuth();
  if (loading) {
    return <p className="muted p-6">{locale === "ar" ? "جارٍ التحميل…" : "Loading…"}</p>;
  }
  if (error) {
    return (
      <p role="alert" className="card border-bad bg-badbg p-4 text-bad">
        {error}
      </p>
    );
  }
  if (empty) {
    return (
      <p className="card p-6 text-center muted">
        {locale === "ar" ? "لا توجد بيانات لعرضها." : "No data to display."}
      </p>
    );
  }
  return <>{children}</>;
}

export function PageHeader({
  titleKey,
  section,
  children,
}: {
  titleKey: string;
  section: string;
  children?: React.ReactNode;
}) {
  const { locale } = useAuth();
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <h1 className="page-title">{t(section, titleKey, locale)}</h1>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </header>
  );
}

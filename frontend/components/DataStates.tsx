"use client";

import { useAuth } from "@/lib/auth";
import { errorText, isDenied } from "@/lib/api";
import { t } from "@/lib/i18n";

/**
 * The «403» state (design p.4, §6): the title is the code itself and the body
 * explains that the refusal is enforced on the server and that the attempt was
 * written to the activity log. It is a state, not a redirect: the user stays on
 * the screen they tried to open.
 */
export function DeniedState({ detail }: { detail?: string | null }) {
  const { locale } = useAuth();
  const ar = locale === "ar";
  return (
    <section
      role="alert"
      className="card mx-auto max-w-xl space-y-3 border-bad bg-badbg p-6 text-center"
    >
      <h1 className="page-title text-bad">403</h1>
      <p className="text-base font-medium text-ink">
        {ar ? "ممنوع الوصول" : "Access forbidden"}
      </p>
      <p className="muted">
        {ar
          ? "هذا الرفض يُفرض في الخادم، لا في الواجهة وحدها. سُجّلت المحاولة في سجل النشاط."
          : "This refusal is enforced on the server, not by the interface alone. The attempt was recorded in the activity log."}
      </p>
      {detail ? <p className="text-secondary text-bad">{detail}</p> : null}
    </section>
  );
}

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
    if (isDenied(error)) {
      return <DeniedState detail={errorText(error)} />;
    }
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

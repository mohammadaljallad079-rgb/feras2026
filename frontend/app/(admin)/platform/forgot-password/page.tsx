"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { t } from "@/lib/i18n";
import { BrandMark } from "@/components/BrandMark";

type Issued = { reset_token: string | null; message: string };

export default function ForgotPasswordPage() {
  const { locale, setLocale, theme, toggleTheme } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [issued, setIssued] = useState<Issued | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      setIssued(await api.post<Issued>("/api/v1/auth/password-reset/request", { email }));
    } catch {
      // The endpoint answers the same way for a known and an unknown address, so
      // any error here is transport-level, not account enumeration.
      setIssued({ reset_token: null, message: t("passwordReset", "issued", locale) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-4 flex justify-end gap-2">
          <button type="button" className="btn-ghost" onClick={() => setLocale(locale === "ar" ? "en" : "ar")}>
            {locale === "ar" ? "English" : "العربية"}
          </button>
          <button type="button" className="btn-ghost" onClick={toggleTheme} aria-pressed={theme === "dark"}>
            {t("common", "dark", locale)}
          </button>
        </div>
        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          <div className="text-center">
            <BrandMark size={48} tone="onCard" />
            <h1 className="page-title mt-3">{t("passwordReset", "requestTitle", locale)}</h1>
            <p className="muted">{t("passwordReset", "requestHint", locale)}</p>
          </div>

          {issued && (
            <div role="status" className="rounded-control border border-line bg-pearl p-3 text-secondary">
              <p>{issued.message}</p>
              {issued.reset_token && (
                <div className="mt-3">
                  <p className="label">{t("passwordReset", "devToken", locale)}</p>
                  <p className="rounded-control border border-line bg-card p-2 break-all" dir="ltr">
                    {issued.reset_token}
                  </p>
                  <p className="muted mt-1">{t("passwordReset", "devTokenHint", locale)}</p>
                  <button
                    type="button"
                    className="btn-primary mt-3 w-full"
                    onClick={() => router.push(`/platform/reset-password?token=${encodeURIComponent(issued.reset_token!)}`)}
                  >
                    {t("passwordReset", "useToken", locale)}
                  </button>
                </div>
              )}
            </div>
          )}

          <div>
            <label className="label" htmlFor="email">
              {t("common", "email", locale)}
            </label>
            <input
              id="email"
              type="email"
              className="input"
              autoComplete="username"
              dir="ltr"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {t("passwordReset", "send", locale)}
          </button>
          <p className="text-center">
            <Link className="underline" href="/platform/login">
              {t("passwordReset", "backToLogin", locale)}
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}

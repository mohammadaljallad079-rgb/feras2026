"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { appName, t } from "@/lib/i18n";
import { BrandMark } from "@/components/BrandMark";

function ResetPasswordForm() {
  const { locale, setLocale, theme, toggleTheme } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  // A link delivered out-of-band carries the token; prefill it when present.
  useEffect(() => {
    const fromLink = searchParams.get("token");
    if (fromLink) setToken(fromLink);
  }, [searchParams]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError(t("passwordReset", "tooShort", locale));
      return;
    }
    if (password !== confirm) {
      setError(t("passwordReset", "mismatch", locale));
      return;
    }
    setBusy(true);
    try {
      await api.post("/api/v1/auth/password-reset/confirm", { token, new_password: password });
      setDone(true);
    } catch {
      setError(t("passwordReset", "invalidToken", locale));
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
            <BrandMark name={appName(locale)} size={48} tone="onCard" />
            <h1 className="page-title mt-3">{t("passwordReset", "confirmTitle", locale)}</h1>
          </div>

          {done ? (
            <div role="status" className="space-y-3">
              <p className="rounded-control border border-ok bg-okbg p-3 text-secondary text-ok">
                {t("passwordReset", "done", locale)}
              </p>
              <button type="button" className="btn-primary w-full" onClick={() => router.push("/login")}>
                {t("passwordReset", "backToLogin", locale)}
              </button>
            </div>
          ) : (
            <>
              {error && (
                <p role="alert" className="rounded-control border border-bad bg-badbg p-3 text-secondary text-bad">
                  {error}
                </p>
              )}
              <div>
                <label className="label" htmlFor="token">
                  {t("passwordReset", "token", locale)}
                </label>
                <input
                  id="token"
                  className="input"
                  dir="ltr"
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
              </div>
              <div>
                <label className="label" htmlFor="new-password">
                  {t("passwordReset", "newPassword", locale)}
                </label>
                <input
                  id="new-password"
                  type="password"
                  className="input"
                  autoComplete="new-password"
                  dir="ltr"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div>
                <label className="label" htmlFor="confirm-password">
                  {t("passwordReset", "confirmPassword", locale)}
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  className="input"
                  autoComplete="new-password"
                  dir="ltr"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </div>
              <button type="submit" className="btn-primary w-full" disabled={busy}>
                {t("passwordReset", "submit", locale)}
              </button>
              <p className="text-center">
                <Link className="underline" href="/login">
                  {t("passwordReset", "backToLogin", locale)}
                </Link>
              </p>
            </>
          )}
        </form>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}

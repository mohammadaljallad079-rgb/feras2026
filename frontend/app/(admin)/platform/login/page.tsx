"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { appName, t } from "@/lib/i18n";
import { BrandMark } from "@/components/BrandMark";

export default function LoginPage() {
  const { login, locale, setLocale, theme, toggleTheme } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/platform/dashboard");
    } catch {
      setError(t("login", "failed", locale));
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
            <h1 className="page-title mt-3">{appName(locale)}</h1>
            <p className="muted">{t("login", "title", locale)}</p>
          </div>
          {error && (
            <p role="alert" className="rounded-control border border-bad bg-badbg p-3 text-secondary text-bad">
              {error}
            </p>
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
          <div>
            <label className="label" htmlFor="password">
              {t("common", "password", locale)}
            </label>
            <input
              id="password"
              type="password"
              className="input"
              autoComplete="current-password"
              dir="ltr"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {t("common", "login", locale)}
          </button>
          <p className="text-center">
            <Link className="underline" href="/platform/forgot-password">
              {t("login", "forgot", locale)}
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}

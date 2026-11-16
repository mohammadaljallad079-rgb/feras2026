"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Locale, appName, t } from "@/lib/i18n";
import { BrandMark } from "@/components/BrandMark";
import { api } from "@/lib/api";

/** Sidebar entries, each gated by the permission the backend enforces. */
const NAV: { href: string; section: string; key: string; permission: string }[] = [
  { href: "/dashboard", section: "nav", key: "dashboard", permission: "" },
  { href: "/companies", section: "nav", key: "companies", permission: "company:view" },
  { href: "/reports", section: "nav", key: "reports", permission: "report:view_own" },
  { href: "/accounting", section: "nav", key: "accounting", permission: "accounting:view" },
  { href: "/service-requests", section: "nav", key: "serviceRequests", permission: "service:view" },
  { href: "/leads", section: "nav", key: "leads", permission: "lead:view" },
  { href: "/opportunities", section: "nav", key: "opportunities", permission: "opportunity:view" },
  { href: "/directives", section: "nav", key: "directives", permission: "directive:view" },
  { href: "/hr", section: "nav", key: "hr", permission: "hr:view" },
  { href: "/website", section: "nav", key: "website", permission: "website:view" },
  { href: "/advisor", section: "nav", key: "advisor", permission: "advisor:view" },
  { href: "/assistant", section: "nav", key: "assistant", permission: "ai:use" },
  { href: "/form-builder", section: "nav", key: "formBuilder", permission: "form:manage" },
  { href: "/users", section: "nav", key: "users", permission: "user:view" },
  { href: "/audit", section: "nav", key: "audit", permission: "audit:view" },
];

type Period = { label: string; due: string | null };

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, locale, setLocale, theme, toggleTheme, logout, can, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [period, setPeriod] = useState<Period | null>(null);

  useEffect(() => {
    api
      .get<{ period: Period | null }>("/api/v1/dashboard/period")
      .then((r) => setPeriod(r.period))
      .catch(() => setPeriod(null));
  }, []);

  if (loading) {
    return <div className="p-6 muted">{locale === "ar" ? "جارٍ التحميل…" : "Loading…"}</div>;
  }
  if (!me) {
    if (typeof window !== "undefined") router.replace("/login");
    return null;
  }

  const visible = NAV.filter((item) => !item.permission || can(item.permission));

  return (
    <div className="flex min-h-screen">
      {/* Sidebar sits on the right in Arabic (RTL) and the left in English (LTR). */}
      <aside
        className={`${menuOpen ? "block" : "hidden"} nav:block w-sidebar shrink-0 bg-side p-4`}
        aria-label={t("common", "menu", locale)}
      >
        <div className="mb-6">
          <BrandMark name={appName(locale)} />
          <p className="mt-2 text-secondary text-sidefg opacity-80">{me.roles.join(" · ")}</p>
          {period && (
            <p className="mt-1 text-secondary text-sidefg opacity-70" dir="ltr">
              {locale === "ar" ? `الفترة الحالية: ${period.label}` : `Current period: ${period.label}`}
              {period.due ? (locale === "ar" ? ` — الاستحقاق ${period.due}` : ` — due ${period.due}`) : ""}
            </p>
          )}
        </div>
        <nav className="space-y-1">
          {visible.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item text-sidefg ${active ? "nav-item-active" : ""}`}
                onClick={() => setMenuOpen(false)}
              >
                {t(item.section, item.key, locale)}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-card px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn-ghost nav:hidden"
              onClick={() => setMenuOpen((v) => !v)}
              aria-expanded={menuOpen}
            >
              {t("common", "menu", locale)}
            </button>
            <span className="section-title">
              {locale === "ar" ? me.full_name_ar : me.full_name_en || me.full_name_ar}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <label className="muted" htmlFor="locale-select">
              {t("common", "language", locale)}
            </label>
            <select
              id="locale-select"
              className="input w-auto"
              value={locale}
              onChange={(e) => setLocale(e.target.value as Locale)}
            >
              <option value="ar">العربية</option>
              <option value="en">English</option>
            </select>
            <button type="button" className="btn-ghost" onClick={toggleTheme} aria-pressed={theme === "dark"}>
              {t("common", "dark", locale)}
            </button>
            <button type="button" className="btn-primary" onClick={() => void logout().then(() => router.push("/login"))}>
              {t("common", "logout", locale)}
            </button>
          </div>
        </header>
        <main className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}

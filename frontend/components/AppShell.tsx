"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Locale, appName, t } from "@/lib/i18n";
import { BrandMark } from "@/components/BrandMark";
import { NavIcon, NavIconName } from "@/components/NavIcon";
import { api } from "@/lib/api";

/** Sidebar entries, each gated by the permission(s) the backend enforces.
 *
 * The tab set is Table 1 of the owner's brief. An entry with several
 * permissions is shown when the user holds any of them (the reports tab, for
 * instance, is read by a manager through `report:view_own` and by the
 * accountant and business developer through `report:view_all`). The owner
 * reaches the Companies tab because it is the only role holding
 * `company:manage`.
 */
const NAV: { href: string; section: string; key: string; permissions: string[]; icon: NavIconName }[] = [
  { href: "/platform/dashboard", section: "nav", key: "dashboard", permissions: [], icon: "dashboard" },
  { href: "/platform/companies", section: "nav", key: "companies", permissions: ["company:manage"], icon: "companies" },
  { href: "/platform/reports", section: "nav", key: "reports", permissions: ["report:view_own", "report:view_all"], icon: "reports" },
  { href: "/platform/accounting", section: "nav", key: "accounting", permissions: ["accounting:view"], icon: "accounting" },
  { href: "/platform/service-requests", section: "nav", key: "serviceRequests", permissions: ["service:view"], icon: "serviceRequests" },
  { href: "/platform/leads", section: "nav", key: "leads", permissions: ["lead:view"], icon: "leads" },
  { href: "/platform/opportunities", section: "nav", key: "opportunities", permissions: ["opportunity:view"], icon: "opportunities" },
  { href: "/platform/directives", section: "nav", key: "directives", permissions: ["directive:view"], icon: "directives" },
  { href: "/platform/hr", section: "nav", key: "hr", permissions: ["hr:view"], icon: "hr" },
  { href: "/platform/website", section: "nav", key: "website", permissions: ["website:view"], icon: "website" },
  { href: "/platform/advisor", section: "nav", key: "advisor", permissions: ["advisor:view"], icon: "advisor" },
  { href: "/platform/assistant", section: "nav", key: "assistant", permissions: ["ai:use"], icon: "assistant" },
  { href: "/platform/form-builder", section: "nav", key: "formBuilder", permissions: ["form:manage"], icon: "formBuilder" },
  { href: "/platform/users", section: "nav", key: "users", permissions: ["user:view"], icon: "users" },
  { href: "/platform/audit", section: "nav", key: "audit", permissions: ["audit:view"], icon: "audit" },
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
    if (typeof window !== "undefined") router.replace("/platform/login");
    return null;
  }

  const visible = NAV.filter((item) => item.permissions.length === 0 || item.permissions.some((p) => can(p)));

  return (
    <div className="flex min-h-screen">
      {/* Sidebar sits on the right in Arabic (RTL) and the left in English (LTR). */}
      <aside
        className={`${menuOpen ? "block" : "hidden"} nav:block w-sidebar shrink-0 bg-side p-4`}
        aria-label={t("common", "menu", locale)}
      >
        <div className="mb-6">
          <BrandMark name={appName(locale)} layout="stack" />
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
                <NavIcon name={item.icon} />
                <span>{t(item.section, item.key, locale)}</span>
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
            <button type="button" className="btn-primary" onClick={() => void logout().then(() => router.push("/platform/login"))}>
              {t("common", "logout", locale)}
            </button>
          </div>
        </header>
        <main className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}

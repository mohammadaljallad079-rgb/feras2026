"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearTokens, getAccessToken, Me, setTokens } from "@/lib/api";
import { Locale } from "@/lib/i18n";

type Theme = "light" | "dark";

type AuthState = {
  me: Me | null;
  loading: boolean;
  locale: Locale;
  theme: Theme;
  setLocale: (l: Locale) => void;
  toggleTheme: () => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (permission: string) => boolean;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [locale, setLocaleState] = useState<Locale>("ar");
  const [theme, setTheme] = useState<Theme>("light");

  const applyTheme = useCallback((next: Theme) => {
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    window.localStorage.setItem("safir.theme", next);
  }, []);

  useEffect(() => {
    const storedTheme = (window.localStorage.getItem("safir.theme") as Theme) || "light";
    applyTheme(storedTheme);
    const storedLocale = (window.localStorage.getItem("safir.locale") as Locale) || "ar";
    setLocaleState(storedLocale);
    document.documentElement.lang = storedLocale;
    document.documentElement.dir = storedLocale === "ar" ? "rtl" : "ltr";
  }, [applyTheme]);

  const refreshMe = useCallback(async () => {
    if (!getAccessToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      setMe(await api.get<Me>("/api/v1/auth/me"));
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await api.post<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", {
        email,
        password,
      });
      setTokens(tokens.access_token, tokens.refresh_token);
      const profile = await api.get<Me>("/api/v1/auth/me");
      setMe(profile);
      const nextLocale = (profile.locale as Locale) || "ar";
      setLocaleState(nextLocale);
      window.localStorage.setItem("safir.locale", nextLocale);
      document.documentElement.lang = nextLocale;
      document.documentElement.dir = nextLocale === "ar" ? "rtl" : "ltr";
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/api/v1/auth/logout", { refresh_token: window.sessionStorage.getItem("safir.refresh") });
    } catch {
      // A failed logout must still clear the local session.
    }
    clearTokens();
    setMe(null);
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem("safir.locale", next);
    document.documentElement.lang = next;
    document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
  }, []);

  const can = useCallback(
    (permission: string) => {
      if (!me) return false;
      // Hiding a control is a UX convenience only; the backend re-checks.
      return me.permissions.includes(permission);
    },
    [me],
  );

  const value = useMemo<AuthState>(
    () => ({
      me,
      loading,
      locale,
      theme,
      setLocale,
      toggleTheme: () => applyTheme(theme === "light" ? "dark" : "light"),
      login,
      logout,
      can,
      refreshMe,
    }),
    [me, loading, locale, theme, setLocale, applyTheme, login, logout, can, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

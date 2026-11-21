"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

/**
 * §9: the platform lives at `sup-edu.com/platform` and requires a login. The
 * bare path is the address a visitor types or a bookmark points at, so it hands
 * them to the dashboard when a session exists and to the login form otherwise.
 * The guard runs on the client because the session lives in browser storage.
 */
export default function PlatformEntry() {
  const { me, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(me ? "/platform/dashboard" : "/platform/login");
  }, [loading, me, router]);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <p className="muted" role="status">
        …
      </p>
    </main>
  );
}

"use client";

import { InviteUserForm } from "@/components/InviteUserForm";
import { useAuth } from "@/lib/auth";

/**
 * The invite screen stays reachable by URL for deep links, but §2/§6.4 present
 * every add form as a window; the users screen opens the same form in a modal.
 */
export default function NewUserPage() {
  const { locale } = useAuth();
  return (
    <section className="mx-auto max-w-2xl">
      <h1 className="page-title mb-6">{locale === "ar" ? "مستخدم جديد" : "New user"}</h1>
      <div className="card">
        <InviteUserForm />
      </div>
    </section>
  );
}

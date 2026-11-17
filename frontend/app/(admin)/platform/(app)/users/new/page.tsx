"use client";

import { useEffect, useState } from "react";
import { api, Company, Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type InviteResult = { user: { id: number; email: string }; setup_token: string; setup_url: string };

export default function NewUserPage() {
  const { locale } = useAuth();
  const [roles, setRoles] = useState<Role[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState({ email: "", full_name_ar: "", full_name_en: "", locale: "ar", role_slugs: [] as string[], company_ids: [] as number[] });
  const [result, setResult] = useState<InviteResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Role[]>("/api/v1/roles").then(setRoles).catch(() => undefined);
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    try {
      setResult(await api.post<InviteResult>("/api/v1/users", form));
    } catch (e) {
      const err = e as { status: number };
      setError(
        err.status === 403
          ? locale === "ar"
            ? "لا تملك صلاحية دعوة المستخدمين."
            : "You are not permitted to invite users."
          : locale === "ar"
            ? "تعذّر إنشاء المستخدم."
            : "Could not create the user.",
      );
    }
  }

  function toggle<T>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
  }

  return (
    <section className="mx-auto max-w-2xl">
      <h1 className="page-title mb-6">{locale === "ar" ? "مستخدم جديد" : "New user"}</h1>
      {error && <p role="alert" className="mb-4 rounded-control border border-bad bg-badbg p-3 text-bad">{error}</p>}
      <form onSubmit={submit} className="card space-y-4">
        <div>
          <label className="label" htmlFor="nu-email">{locale === "ar" ? "البريد الإلكتروني" : "Email"}</label>
          <input id="nu-email" type="email" className="input" dir="ltr" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="nu-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
            <input id="nu-ar" className="input" dir="rtl" required value={form.full_name_ar} onChange={(e) => setForm({ ...form, full_name_ar: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="nu-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
            <input id="nu-en" className="input" dir="ltr" required value={form.full_name_en} onChange={(e) => setForm({ ...form, full_name_en: e.target.value })} />
          </div>
        </div>
        <fieldset>
          <legend className="label">{locale === "ar" ? "الأدوار" : "Roles"}</legend>
          <div className="flex flex-wrap gap-3">
            {roles.map((r) => (
              <label key={r.id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.role_slugs.includes(r.slug)}
                  onChange={() => setForm({ ...form, role_slugs: toggle(form.role_slugs, r.slug) })}
                />
                <span>{locale === "ar" ? r.name_ar : r.name_en}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="label">{locale === "ar" ? "نطاق الشركات" : "Company scope"}</legend>
          <p className="muted mb-2">
            {locale === "ar" ? "اتركه فارغاً للأدوار التي ترى كل الشركات." : "Leave empty for roles that see all companies."}
          </p>
          <div className="flex flex-wrap gap-3">
            {companies.map((c) => (
              <label key={c.id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.company_ids.includes(c.id)}
                  onChange={() => setForm({ ...form, company_ids: toggle(form.company_ids, c.id) })}
                />
                <span>{locale === "ar" ? c.name_ar : c.name_en}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <button type="submit" className="btn-primary">{locale === "ar" ? "إنشاء المستخدم" : "Create user"}</button>
      </form>

      {result && (
        <div className="card mt-4">
          <h2 className="section-title mb-2">{locale === "ar" ? "رابط إعداد كلمة المرور" : "Password setup link"}</h2>
          <p className="muted mb-2">
            {locale === "ar"
              ? "لا تُرسل كلمات المرور بنص واضح. شارك هذا الرابط لمرة واحدة مع المستخدم."
              : "Passwords are never emailed in plain text. Share this single-use link with the user."}
          </p>
          <code className="block break-all rounded-control bg-pearl p-3" dir="ltr">{result.setup_url}</code>
        </div>
      )}
    </section>
  );
}

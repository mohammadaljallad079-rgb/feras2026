"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { api, Role, UserOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function UsersPage() {
  const { locale, can } = useAuth();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [newRole, setNewRole] = useState({ slug: "", name_ar: "", name_en: "", permissions: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await api.get<UserOut[]>("/api/v1/users"));
      setRoles(await api.get<Role[]>("/api/v1/roles").catch(() => []));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleActive(user: UserOut) {
    setMessage(null);
    try {
      await api.patch(`/api/v1/users/${user.id}`, { is_active: !user.is_active });
      await load();
    } catch {
      setMessage(locale === "ar" ? "فشل التحديث." : "The update failed.");
    }
  }

  async function createRole(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/roles", {
        slug: newRole.slug,
        name_ar: newRole.name_ar,
        name_en: newRole.name_en,
        permissions: newRole.permissions.split(",").map((p) => p.trim()).filter(Boolean),
      });
      setNewRole({ slug: "", name_ar: "", name_en: "", permissions: "" });
      setMessage(locale === "ar" ? "تم إنشاء الدور المخصص." : "Custom role created.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر إنشاء الدور." : "Could not create the role.");
    }
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{locale === "ar" ? "المستخدمون والصلاحيات" : "Users and roles"}</h1>
        {can("user:manage") && (
          <a className="btn-primary" href="/users/new">{locale === "ar" ? "دعوة مستخدم" : "Invite user"}</a>
        )}
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      <DataStates loading={loading} error={error} empty={users.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "البريد الإلكتروني" : "Email"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الاسم" : "Name"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الأدوار" : "Roles"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "نطاق الشركات" : "Company scope"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-line last:border-0">
                  <td className="p-3" dir="ltr">{u.email}</td>
                  <td className="p-3">{locale === "ar" ? u.full_name_ar : u.full_name_en}</td>
                  <td className="p-3">{u.roles.join(", ")}</td>
                  <td className="p-3" dir="ltr">{u.company_ids.length ? u.company_ids.join(", ") : locale === "ar" ? "كل الشركات" : "All companies"}</td>
                  <td className="p-3">
                    <span className={u.is_active ? "chip-ok" : "chip-bad"}>{u.is_active ? (locale === "ar" ? "نشط" : "Active") : locale === "ar" ? "غير نشط" : "Inactive"}</span>
                  </td>
                  <td className="p-3">
                    {can("user:manage") && (
                      <button type="button" className="btn-ghost" onClick={() => void toggleActive(u)}>
                        {u.is_active ? (locale === "ar" ? "تعطيل" : "Deactivate") : locale === "ar" ? "تفعيل" : "Activate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>

      <h2 className="section-title mb-3 mt-6">{locale === "ar" ? "الأدوار" : "Roles"}</h2>
      <div className="card table-scroll p-0">
        <table className="w-full min-w-[560px] border-collapse">
          <thead>
            <tr className="border-b border-line bg-pearl">
              <th className="p-3 text-start">{locale === "ar" ? "الدور" : "Role"}</th>
              <th className="p-3 text-start">{locale === "ar" ? "الصلاحيات" : "Permissions"}</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0">
                <td className="p-3">{locale === "ar" ? r.name_ar : r.name_en}{r.is_system && <span className="chip-neutral ms-2">{locale === "ar" ? "نظامي" : "System"}</span>}</td>
                <td className="p-3 muted" dir="ltr">{r.permission_codes.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {can("role:manage") && (
        <form onSubmit={createRole} className="card mt-6 grid gap-3 sm:grid-cols-2">
          <h2 className="section-title sm:col-span-2">{locale === "ar" ? "دور مخصص جديد" : "New custom role"}</h2>
          <div>
            <label className="label" htmlFor="role-slug">{locale === "ar" ? "المعرّف" : "Slug"}</label>
            <input id="role-slug" className="input" dir="ltr" required value={newRole.slug} onChange={(e) => setNewRole({ ...newRole, slug: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="role-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
            <input id="role-ar" className="input" dir="rtl" required value={newRole.name_ar} onChange={(e) => setNewRole({ ...newRole, name_ar: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="role-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
            <input id="role-en" className="input" dir="ltr" required value={newRole.name_en} onChange={(e) => setNewRole({ ...newRole, name_en: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="role-perms">{locale === "ar" ? "الصلاحيات (مفصولة بفواصل)" : "Permissions (comma separated)"}</label>
            <input id="role-perms" className="input" dir="ltr" value={newRole.permissions} onChange={(e) => setNewRole({ ...newRole, permissions: e.target.value })} />
          </div>
          <div className="flex items-end">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إنشاء الدور" : "Create role"}</button>
          </div>
        </form>
      )}
    </section>
  );
}

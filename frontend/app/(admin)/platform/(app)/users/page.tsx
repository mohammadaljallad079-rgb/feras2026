"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { InviteUserForm } from "@/components/InviteUserForm";
import { Modal } from "@/components/Modal";
import { Toast } from "@/components/Toast";
import { api, loadErrorState, Role, UserOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Table 5, «دور مخصص»: the dialog picks modules (the platform tabs) and, under
// each, the actions the backend can enforce. A module never offers a code the
// catalog does not define, so a granted role is always enforceable.
type Action = { key: string; ar: string; en: string; code: string };

// Table 5 R18 names the action vocabulary explicitly: «الإجراءات (عرض، إضافة،
// تعديل، حذف، اعتماد، تنزيل)». Each module offers the subset of those six verbs
// the backend can enforce, and each verb maps to exactly one permission code.
const VERBS: Record<string, { ar: string; en: string }> = {
  view: { ar: "عرض", en: "View" },
  add: { ar: "إضافة", en: "Add" },
  edit: { ar: "تعديل", en: "Edit" },
  delete: { ar: "حذف", en: "Delete" },
  approve: { ar: "اعتماد", en: "Approve" },
  download: { ar: "تنزيل", en: "Download" },
};

const MODULE_ACTIONS: { key: string; ar: string; en: string; actions: Action[] }[] = [
  { key: "companies", ar: "الشركات", en: "Companies", actions: [
    { key: "view", ...VERBS.view, code: "company:view" },
    { key: "edit", ...VERBS.edit, code: "company:manage" },
  ] },
  { key: "reports", ar: "التقارير الشهرية", en: "Monthly reports", actions: [
    { key: "view", ...VERBS.view, code: "report:view_all" },
    { key: "add", ...VERBS.add, code: "report:submit" },
    { key: "approve", ...VERBS.approve, code: "report:review" },
    { key: "download", ...VERBS.download, code: "report:export" },
  ] },
  { key: "accounting", ar: "محاسبة القابضة", en: "Holding accounting", actions: [
    { key: "view", ...VERBS.view, code: "accounting:view" },
    { key: "edit", ...VERBS.edit, code: "accounting:manage" },
  ] },
  { key: "service", ar: "طلبات الخدمات", en: "Service requests", actions: [
    { key: "view", ...VERBS.view, code: "service:view" },
    { key: "add", ...VERBS.add, code: "service:create" },
    { key: "edit", ...VERBS.edit, code: "service:reply" },
  ] },
  { key: "leads", ar: "العملاء المحتملون", en: "Leads", actions: [
    { key: "view", ...VERBS.view, code: "lead:view" },
    { key: "edit", ...VERBS.edit, code: "lead:manage" },
  ] },
  { key: "opportunities", ar: "الفرص", en: "Opportunities", actions: [
    { key: "view", ...VERBS.view, code: "opportunity:view" },
    { key: "add", ...VERBS.add, code: "opportunity:create" },
    { key: "approve", ...VERBS.approve, code: "opportunity:decide" },
  ] },
  { key: "directives", ar: "التوجيهات", en: "Directives", actions: [
    { key: "view", ...VERBS.view, code: "directive:view" },
    { key: "add", ...VERBS.add, code: "directive:create" },
    { key: "edit", ...VERBS.edit, code: "directive:update" },
  ] },
  { key: "hr", ar: "الموظفون والموارد البشرية", en: "Employees & HR", actions: [
    { key: "view", ...VERBS.view, code: "hr:view" },
    { key: "edit", ...VERBS.edit, code: "hr:manage" },
  ] },
  { key: "website", ar: "إدارة الموقع", en: "Website management", actions: [
    { key: "view", ...VERBS.view, code: "website:view" },
    { key: "edit", ...VERBS.edit, code: "website:manage" },
    { key: "delete", ...VERBS.delete, code: "site:manage" },
  ] },
  { key: "advisor", ar: "المستشار الخارجي", en: "External advisor", actions: [
    { key: "view", ...VERBS.view, code: "advisor:view" },
    { key: "add", ...VERBS.add, code: "advisor:submit" },
  ] },
  { key: "assistant", ar: "المساعد الذكي", en: "AI assistant", actions: [
    { key: "view", ...VERBS.view, code: "ai:use" },
  ] },
  { key: "formBuilder", ar: "منشئ النماذج", en: "Form builder", actions: [
    { key: "add", ...VERBS.add, code: "form:manage" },
    { key: "edit", ...VERBS.edit, code: "form:manage" },
  ] },
  { key: "users", ar: "المستخدمون والأدوار", en: "Users and roles", actions: [
    { key: "view", ...VERBS.view, code: "user:view" },
    { key: "edit", ...VERBS.edit, code: "user:manage" },
  ] },
  { key: "audit", ar: "سجل النشاط", en: "Activity log", actions: [
    { key: "view", ...VERBS.view, code: "audit:view" },
  ] },
];

// Grants the six verbs do not express — narrower rights the specification gives
// by name (own-company reports, forwarding, confidential HR attachments, the
// salary column, assigning submissions, configuring the key, managing roles).
const EXTRA_GRANTS: Action[] = [
  { key: "report_own", ar: "تقارير شركته", en: "Own company reports", code: "report:view_own" },
  { key: "report_forward", ar: "إرسال التقرير للإدارة", en: "Forward a report", code: "report:forward" },
  { key: "report_period", ar: "فتح فترة", en: "Open a period", code: "report:period_manage" },
  { key: "service_assign", ar: "إسناد الطلبات", en: "Assign requests", code: "service:assign" },
  { key: "inbox", ar: "وارد الموقع", en: "Website inbox", code: "site:submissions" },
  { key: "site_assign", ar: "إسناد الوارد", en: "Assign submissions", code: "site:assign" },
  { key: "confidential", ar: "مرفقات مقيدة", en: "Confidential attachments", code: "hr:view_confidential" },
  { key: "salary", ar: "الراتب", en: "Salary", code: "hr:view_salary" },
  { key: "ai_key", ar: "إعداد مفتاح المساعد", en: "Configure the assistant key", code: "ai:configure" },
  { key: "roles", ar: "إدارة الأدوار", en: "Manage roles", code: "role:manage" },
];

export default function UsersPage() {
  const { locale, can } = useAuth();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  // §Table 5: «دور مخصص» opens a modal with name, description, modules and
  // actions; the chosen permission codes are derived from the checkboxes.
  const [roleOpen, setRoleOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [newRole, setNewRole] = useState({ slug: "", name_ar: "", name_en: "", description: "" });
  const [picked, setPicked] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await api.get<UserOut[]>("/api/v1/users"));
      setRoles(await api.get<Role[]>("/api/v1/roles").catch(() => []));
    } catch (e) {
      setError(loadErrorState(e, locale));
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
        description: newRole.description || null,
        permissions: picked,
      });
      setNewRole({ slug: "", name_ar: "", name_en: "", description: "" });
      setPicked([]);
      setRoleOpen(false);
      setMessage(locale === "ar" ? "تم إنشاء الدور المخصص." : "Custom role created.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر إنشاء الدور." : "Could not create the role.");
    }
  }

  function togglePermission(code: string) {
    setPicked((list) => (list.includes(code) ? list.filter((c) => c !== code) : [...list, code]));
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{locale === "ar" ? "المستخدمون والصلاحيات" : "Users and roles"}</h1>
        <div className="flex flex-wrap gap-2">
          {can("user:manage") && (
            <button type="button" className="btn-primary" onClick={() => setInviteOpen(true)}>
              {locale === "ar" ? "مستخدم جديد" : "New user"}
            </button>
          )}
          {can("role:manage") && (
            <button type="button" className="btn-gold" onClick={() => setRoleOpen(true)}>
              {locale === "ar" ? "دور مخصص" : "Custom role"}
            </button>
          )}
        </div>
      </header>

      {inviteOpen && can("user:manage") && (
        <Modal
          title={locale === "ar" ? "مستخدم جديد" : "New user"}
          onClose={() => setInviteOpen(false)}
        >
          <InviteUserForm
            onDone={() => {
              setMessage(locale === "ar" ? "أُنشئ المستخدم. شارك رابط إعداد كلمة المرور." : "User created. Share the password setup link.");
              void load();
            }}
          />
        </Modal>
      )}


      <DataStates loading={loading} error={error} empty={users.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                {/* §5.1: «جدول المستخدمين (الاسم، البريد، الأدوار، النطاق، الحالة)». */}
                <th className="p-3 text-start">{locale === "ar" ? "الاسم" : "Name"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "البريد" : "Email"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الأدوار" : "Roles"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النطاق" : "Scope"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-line last:border-0">
                  <td className="p-3">{locale === "ar" ? u.full_name_ar : u.full_name_en}</td>
                  <td className="p-3" dir="ltr">{u.email}</td>
                  <td className="p-3">{u.roles.join(", ")}</td>
                  <td className="p-3" dir="ltr">{u.company_ids.length ? u.company_ids.join(", ") : locale === "ar" ? "كل الشركات" : "All companies"}</td>
                  <td className="p-3">
                    <span className={u.is_active ? "chip-ok" : "chip-bad"}>{u.is_active ? (locale === "ar" ? "نشط" : "Active") : locale === "ar" ? "غير نشط" : "Inactive"}</span>
                  </td>
                  <td className="p-3">
                    {can("user:manage") && (
                      <button
                        type="button"
                        className={u.is_active ? "btn-bad" : "btn-ghost"}
                        onClick={() => void toggleActive(u)}
                      >
                        {u.is_active ? (locale === "ar" ? "إيقاف" : "Suspend") : locale === "ar" ? "إعادة تفعيل" : "Reactivate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>

      <h2 className="section-title mb-3 mt-6">{locale === "ar" ? "الأدوار المخصصة" : "Custom roles"}</h2>
      <div className="card table-scroll p-0">
        <table className="w-full min-w-[560px] border-collapse">
          <thead>
            <tr className="border-b border-line bg-pearl">
              <th className="p-3 text-start">{locale === "ar" ? "الدور" : "Role"}</th>
              <th className="p-3 text-start">{locale === "ar" ? "الوصف" : "Description"}</th>
              <th className="p-3 text-start">{locale === "ar" ? "الصلاحيات" : "Permissions"}</th>
            </tr>
          </thead>
          <tbody>
            {roles.filter((r) => !r.is_system).map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0">
                <td className="p-3">{locale === "ar" ? r.name_ar : r.name_en}</td>
                <td className="p-3 muted">{r.description ?? "—"}</td>
                <td className="p-3 muted" dir="ltr">{r.permission_codes.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Table 5: «دور مخصص» — name, description, modules and per-module actions. */}
      {roleOpen && can("role:manage") && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 p-4" role="dialog" aria-modal="true">
          <form onSubmit={createRole} className="card mx-auto my-6 w-full max-w-3xl space-y-4">
            <h2 className="section-title">{locale === "ar" ? "دور مخصص جديد" : "New custom role"}</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className="label" htmlFor="role-slug">{locale === "ar" ? "المعرّف" : "Slug"}</label>
                <input id="role-slug" className="input" dir="ltr" required value={newRole.slug} onChange={(e) => setNewRole({ ...newRole, slug: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="role-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}<span aria-hidden="true"> *</span></label>
                <input id="role-ar" className="input" dir="rtl" required value={newRole.name_ar} onChange={(e) => setNewRole({ ...newRole, name_ar: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="role-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
                <input id="role-en" className="input" dir="ltr" required value={newRole.name_en} onChange={(e) => setNewRole({ ...newRole, name_en: e.target.value })} />
              </div>
            </div>
            <div>
              <label className="label" htmlFor="role-desc">{locale === "ar" ? "الوصف" : "Description"}</label>
              <textarea id="role-desc" className="input min-h-16" value={newRole.description} onChange={(e) => setNewRole({ ...newRole, description: e.target.value })} />
            </div>

            <fieldset>
              <legend className="label">{locale === "ar" ? "الوحدات والإجراءات" : "Modules and actions"}</legend>
              <div className="space-y-3">
                {MODULE_ACTIONS.map((m) => (
                  <div key={m.key} className="rounded-control border border-line p-3">
                    <p className="mb-2 font-medium">{locale === "ar" ? m.ar : m.en}</p>
                    <div className="flex flex-wrap gap-3">
                      {m.actions.map((a) => (
                        <label key={`${m.key}-${a.key}`} className="flex items-center gap-2">
                          <input type="checkbox" checked={picked.includes(a.code)} onChange={() => togglePermission(a.code)} />
                          <span>{locale === "ar" ? a.ar : a.en}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="label">{locale === "ar" ? "صلاحيات إضافية" : "Additional grants"}</legend>
              <div className="flex flex-wrap gap-3">
                {EXTRA_GRANTS.map((a) => (
                  <label key={a.code} className="flex items-center gap-2">
                    <input type="checkbox" checked={picked.includes(a.code)} onChange={() => togglePermission(a.code)} />
                    <span>{locale === "ar" ? a.ar : a.en}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary">{locale === "ar" ? "إنشاء الدور" : "Create role"}</button>
              <button type="button" className="btn-ghost" onClick={() => setRoleOpen(false)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
            </div>
          </form>
        </div>
      )}
      <Toast message={message} />
    </section>
  );
}

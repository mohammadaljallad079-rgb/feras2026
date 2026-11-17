"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { api, loadError, Company, FormField } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const FIELD_TYPES = ["text", "number", "amount", "date", "boolean", "select"];

export default function FormBuilderPage() {
  const { locale, can } = useAuth();
  const [fields, setFields] = useState<FormField[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({ code: "", name_ar: "", name_en: "", field_type: "text", is_required: false, sector_scope: "", company_id: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setFields(await api.get<FormField[]>("/api/v1/form-fields"));
    } catch (e) {
      setError(loadError(e, locale));
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/form-fields", {
        ...form,
        sector_scope: form.sector_scope || null,
        company_id: form.company_id ? Number(form.company_id) : null,
      });
      setForm({ code: "", name_ar: "", name_en: "", field_type: "text", is_required: false, sector_scope: "", company_id: "" });
      setMessage(locale === "ar" ? "تمت إضافة الحقل. نسخة التعريف 1." : "Field added. Definition version 1.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر حفظ الحقل." : "Could not save the field.");
    }
  }

  async function toggleRequired(field: FormField) {
    setMessage(null);
    try {
      const updated = await api.patch<FormField>(`/api/v1/form-fields/${field.id}`, { is_required: !field.is_required });
      setMessage(locale === "ar" ? `تم التحديث. نسخة التعريف ${updated.version}.` : `Updated. Definition version ${updated.version}.`);
      await load();
    } catch {
      setMessage(locale === "ar" ? "فشل التحديث." : "The update failed.");
    }
  }

  async function deactivate(field: FormField) {
    setMessage(null);
    try {
      await api.post(`/api/v1/form-fields/${field.id}/deactivate`);
      setMessage(locale === "ar" ? "تم إيقاف الحقل. التقارير السابقة لم تتأثر." : "Field deactivated. Historical reports are unaffected.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "فشل الإجراء." : "The action failed.");
    }
  }

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{locale === "ar" ? "منشئ النماذج" : "Form builder"}</h1>
        <p className="muted">
          {locale === "ar"
            ? "تُخزَّن قيم التقارير مع نسخة تعريف الحقل، لذا لا تُفسد التغييرات التقارير السابقة."
            : "Report values are stored with their field-definition version, so changes never corrupt historical reports."}
        </p>
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      {can("form:manage") && (
        <form onSubmit={create} className="card mb-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="ff-code">{locale === "ar" ? "الرمز" : "Code"}</label>
            <input id="ff-code" className="input" dir="ltr" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="ff-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
            <input id="ff-ar" className="input" dir="rtl" required value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="ff-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
            <input id="ff-en" className="input" dir="ltr" required value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="ff-type">{locale === "ar" ? "نوع البيانات" : "Data type"}</label>
            <select id="ff-type" className="input" value={form.field_type} onChange={(e) => setForm({ ...form, field_type: e.target.value })}>
              {FIELD_TYPES.map((t) => (<option key={t} value={t}>{t}</option>))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="ff-sector">{locale === "ar" ? "نطاق القطاع" : "Sector scope"}</label>
            <input id="ff-sector" className="input" value={form.sector_scope} onChange={(e) => setForm({ ...form, sector_scope: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="ff-company">{locale === "ar" ? "نطاق الشركة" : "Company scope"}</label>
            <select id="ff-company" className="input" value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
              <option value="">{locale === "ar" ? "كل الشركات" : "All companies"}</option>
              {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input id="ff-required" type="checkbox" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
            <label htmlFor="ff-required">{locale === "ar" ? "حقل مطلوب" : "Required field"}</label>
          </div>
          <div className="flex items-end">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إضافة حقل" : "Add field"}</button>
          </div>
        </form>
      )}

      <DataStates loading={loading} error={error} empty={fields.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "الرمز" : "Code"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الاسم" : "Name"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النوع" : "Type"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "مطلوب" : "Required"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النطاق" : "Scope"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النسخة" : "Version"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f) => (
                <tr key={f.id} className="border-b border-line last:border-0">
                  <td className="p-3" dir="ltr">{f.code}</td>
                  <td className="p-3">{locale === "ar" ? f.name_ar : f.name_en}</td>
                  <td className="p-3">{f.field_type}</td>
                  <td className="p-3">{f.is_required ? (locale === "ar" ? "نعم" : "Yes") : locale === "ar" ? "لا" : "No"}</td>
                  <td className="p-3">
                    {f.company_id
                      ? companies.find((c) => c.id === f.company_id)?.[locale === "ar" ? "name_ar" : "name_en"]
                      : f.sector_scope ?? (locale === "ar" ? "عام" : "Global")}
                  </td>
                  <td className="p-3 tabular-nums" dir="ltr">{f.version}</td>
                  <td className="p-3">
                    <span className={f.is_active ? "chip-ok" : "chip-neutral"}>{f.is_active ? (locale === "ar" ? "مفعّل" : "Active") : locale === "ar" ? "موقوف" : "Inactive"}</span>
                  </td>
                  <td className="p-3">
                    {can("form:manage") && f.is_active && (
                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="btn-ghost" onClick={() => void toggleRequired(f)}>
                          {f.is_required ? (locale === "ar" ? "إلغاء الإلزام" : "Make optional") : locale === "ar" ? "جعله مطلوباً" : "Make required"}
                        </button>
                        <button type="button" className="btn-ghost" onClick={() => void deactivate(f)}>
                          {locale === "ar" ? "إيقاف" : "Deactivate"}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>
    </section>
  );
}

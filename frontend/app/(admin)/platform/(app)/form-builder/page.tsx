"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { Modal } from "@/components/Modal";
import { Toast } from "@/components/Toast";
import { api, loadError, Company, FormField } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Table 5 names two field types — «رقم / مبلغ» and «سؤال وجواب» — plus the
// date/flag kinds the report form already understands. Every value here must be
// a member of the backend FieldType enum, or the save is rejected with a 422.
const FIELD_TYPES: { value: string; ar: string; en: string }[] = [
  { value: "amount", ar: "رقم / مبلغ", en: "Number / amount" },
  { value: "number", ar: "رقم صحيح", en: "Whole number" },
  { value: "text", ar: "سؤال وجواب", en: "Question and answer" },
  { value: "textarea", ar: "نص طويل", en: "Long text" },
  { value: "date", ar: "تاريخ", en: "Date" },
  { value: "boolean", ar: "نعم / لا", en: "Yes / no" },
];

// Table 5: the scope is either a single company or a whole sector.
const SCOPES = [
  { value: "company", ar: "شركة واحدة", en: "One company" },
  { value: "sector", ar: "قطاع كامل", en: "Whole sector" },
];

function typeLabel(value: string, locale: string): string {
  const found = FIELD_TYPES.find((t) => t.value === value);
  if (!found) return value;
  return locale === "ar" ? found.ar : found.en;
}

export default function FormBuilderPage() {
  const { locale, can } = useAuth();
  const [fields, setFields] = useState<FormField[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [scope, setScope] = useState("company");
  const [form, setForm] = useState({ code: "", name_ar: "", name_en: "", field_type: "amount", is_required: false, sector_scope: "", company_id: "", parent_id: "" });
  // §5.1 / Table 5: «تعديل» opens a modal to edit the field definition. Editing
  // bumps the version and never rewrites past reports.
  const [editFor, setEditFor] = useState<FormField | null>(null);
  const [editScope, setEditScope] = useState("company");
  const [editForm, setEditForm] = useState({ name_ar: "", name_en: "", field_type: "amount", is_required: false, sector_scope: "", company_id: "", parent_id: "" });

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
        parent_id: form.parent_id ? Number(form.parent_id) : null,
        sector_scope: scope === "sector" ? form.sector_scope || null : null,
        company_id: scope === "company" && form.company_id ? Number(form.company_id) : null,
      });
      setForm({ code: "", name_ar: "", name_en: "", field_type: "amount", is_required: false, sector_scope: "", company_id: "", parent_id: "" });
      setFormOpen(false);
      setMessage(locale === "ar" ? "تمت إضافة الحقل. نسخة التعريف 1." : "Field added. Definition version 1.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر حفظ الحقل." : "Could not save the field.");
    }
  }

  async function deactivate(field: FormField) {
    setMessage(null);
    try {
      await api.post(`/api/v1/form-fields/${field.id}/deactivate`);
      setMessage(locale === "ar" ? "تم أرشفة الحقل. التقارير السابقة لم تتأثر." : "Field archived. Historical reports are unaffected.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "فشل الإجراء." : "The action failed.");
    }
  }

  function openEdit(field: FormField) {
    setEditFor(field);
    setEditScope(field.sector_scope ? "sector" : "company");
    setEditForm({
      name_ar: field.name_ar,
      name_en: field.name_en,
      field_type: field.field_type,
      is_required: field.is_required,
      sector_scope: field.sector_scope ?? "",
      company_id: field.company_id ? String(field.company_id) : "",
      parent_id: field.parent_id ? String(field.parent_id) : "",
    });
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editFor) return;
    setMessage(null);
    try {
      const updated = await api.patch<FormField>(`/api/v1/form-fields/${editFor.id}`, {
        ...editForm,
        parent_id: editForm.parent_id ? Number(editForm.parent_id) : null,
        sector_scope: editScope === "sector" ? editForm.sector_scope || null : null,
        company_id: editScope === "company" && editForm.company_id ? Number(editForm.company_id) : null,
      });
      setMessage(locale === "ar" ? `تم التعديل. نسخة التعريف ${updated.version}.` : `Field updated. Definition version ${updated.version}.`);
      setEditFor(null);
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر حفظ التعديل." : "Could not save the change.");
    }
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-title">{locale === "ar" ? "منشئ النماذج" : "Form builder"}</h1>
          <p className="muted">
            {locale === "ar"
              ? "تُخزَّن قيم التقارير مع نسخة تعريف الحقل، لذا لا تُفسد التغييرات التقارير السابقة."
              : "Report values are stored with their field-definition version, so changes never corrupt historical reports."}
          </p>
        </div>
        {can("form:manage") && (
          <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
            {locale === "ar" ? "إضافة حقل" : "Add field"}
          </button>
        )}
      </header>

      {formOpen && can("form:manage") && (
        <Modal
          title={locale === "ar" ? "إضافة حقل" : "Add field"}
          onClose={() => setFormOpen(false)}
          wide
        >
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-3">
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
            <label className="label" htmlFor="ff-type">{locale === "ar" ? "نوع الحقل" : "Field type"}</label>
            <select id="ff-type" className="input" value={form.field_type} onChange={(e) => setForm({ ...form, field_type: e.target.value })}>
              {FIELD_TYPES.map((t) => (<option key={t.value} value={t.value}>{locale === "ar" ? t.ar : t.en}</option>))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="ff-scope">{locale === "ar" ? "النطاق" : "Scope"}</label>
            <select id="ff-scope" className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
              {SCOPES.map((s) => (<option key={s.value} value={s.value}>{locale === "ar" ? s.ar : s.en}</option>))}
            </select>
          </div>
          {scope === "company" ? (
            <div>
              <label className="label" htmlFor="ff-company">{locale === "ar" ? "الشركة المستهدفة" : "Target company"}</label>
              <select id="ff-company" className="input" value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
                <option value="">{locale === "ar" ? "كل الشركات" : "All companies"}</option>
                {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
              </select>
            </div>
          ) : (
            <div>
              <label className="label" htmlFor="ff-sector">{locale === "ar" ? "القطاع المستهدف" : "Target sector"}</label>
              <input id="ff-sector" className="input" value={form.sector_scope} onChange={(e) => setForm({ ...form, sector_scope: e.target.value })} />
            </div>
          )}
          <div>
            <label className="label" htmlFor="ff-parent">{locale === "ar" ? "الحقل الرئيسي (اختياري)" : "Main field (optional)"}</label>
            <select id="ff-parent" className="input" value={form.parent_id} onChange={(e) => setForm({ ...form, parent_id: e.target.value })}>
              <option value="">{locale === "ar" ? "— بلا حقل رئيسي —" : "— No main field —"}</option>
              {fields.filter((f) => f.is_active && !f.parent_id).map((f) => (
                <option key={f.id} value={f.id}>{locale === "ar" ? f.name_ar : f.name_en}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input id="ff-required" type="checkbox" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} />
            <label htmlFor="ff-required">{locale === "ar" ? "إلزامي" : "Required"}</label>
          </div>
          <div className="flex items-end justify-end gap-2 sm:col-span-3">
            <button type="button" className="btn-ghost" onClick={() => setFormOpen(false)}>
              {locale === "ar" ? "إلغاء" : "Cancel"}
            </button>
            <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ" : "Save"}</button>
          </div>
        </form>
        </Modal>
      )}

      <DataStates loading={loading} error={error} empty={fields.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                {/* §5.1: «جدول حقول التقرير الشهري (الحقل بالعربية، بالإنجليزية،
                    النطاق، النوع، إلزامي، الحقل الرئيسي، الحالة)». */}
                <th className="p-3 text-start">{locale === "ar" ? "الحقل بالعربية" : "Field (Arabic)"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحقل بالإنجليزية" : "Field (English)"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النطاق" : "Scope"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "النوع" : "Type"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إلزامي" : "Required"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحقل الرئيسي" : "Main field"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f) => (
                <tr key={f.id} className="border-b border-line last:border-0">
                  <td className="p-3">{f.name_ar}</td>
                  <td className="p-3" dir="ltr">{f.name_en}</td>
                  <td className="p-3">
                    {f.company_id
                      ? companies.find((c) => c.id === f.company_id)?.[locale === "ar" ? "name_ar" : "name_en"]
                      : f.sector_scope ?? (locale === "ar" ? "عام" : "Global")}
                  </td>
                  <td className="p-3">{typeLabel(f.field_type, locale)}</td>
                  <td className="p-3">{f.is_required ? (locale === "ar" ? "نعم" : "Yes") : locale === "ar" ? "لا" : "No"}</td>
                  <td className="p-3">
                    {f.parent_id
                      ? (() => { const p = fields.find((x) => x.id === f.parent_id); return p ? (locale === "ar" ? p.name_ar : p.name_en) : `#${f.parent_id}`; })()
                      : "—"}
                  </td>
                  <td className="p-3">
                    <span className={f.is_active ? "chip-ok" : "chip-neutral"}>{f.is_active ? (locale === "ar" ? "مفعّل" : "Active") : locale === "ar" ? "مؤرشف" : "Archived"}</span>
                  </td>
                  <td className="p-3">
                    {can("form:manage") && f.is_active && (
                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="btn-ghost" onClick={() => openEdit(f)}>
                          {locale === "ar" ? "تعديل" : "Edit"}
                        </button>
                        <button type="button" className="btn-bad" onClick={() => void deactivate(f)}>
                          {locale === "ar" ? "أرشفة" : "Archive"}
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

      {/* §5.1 / Table 5: «تعديل» — edit the field definition. A saved change
          bumps the version; past reports keep the version they were saved with. */}
      {editFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <form onSubmit={saveEdit} className="card w-full max-w-2xl space-y-4">
            <h2 className="section-title">{locale === "ar" ? "تعديل الحقل" : "Edit field"}</h2>
            <p className="muted">
              {locale === "ar"
                ? `الرمز ${editFor.code} — التعديل لا يغيّر التقارير السابقة.`
                : `Code ${editFor.code} — editing does not change past reports.`}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="ef-ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
                <input id="ef-ar" className="input" dir="rtl" required value={editForm.name_ar} onChange={(e) => setEditForm({ ...editForm, name_ar: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="ef-en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
                <input id="ef-en" className="input" dir="ltr" required value={editForm.name_en} onChange={(e) => setEditForm({ ...editForm, name_en: e.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="ef-type">{locale === "ar" ? "نوع الحقل" : "Field type"}</label>
                <select id="ef-type" className="input" value={editForm.field_type} onChange={(e) => setEditForm({ ...editForm, field_type: e.target.value })}>
                  {FIELD_TYPES.map((t) => (<option key={t.value} value={t.value}>{locale === "ar" ? t.ar : t.en}</option>))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="ef-scope">{locale === "ar" ? "النطاق" : "Scope"}</label>
                <select id="ef-scope" className="input" value={editScope} onChange={(e) => setEditScope(e.target.value)}>
                  {SCOPES.map((s) => (<option key={s.value} value={s.value}>{locale === "ar" ? s.ar : s.en}</option>))}
                </select>
              </div>
              {editScope === "company" ? (
                <div>
                  <label className="label" htmlFor="ef-company">{locale === "ar" ? "الشركة المستهدفة" : "Target company"}</label>
                  <select id="ef-company" className="input" value={editForm.company_id} onChange={(e) => setEditForm({ ...editForm, company_id: e.target.value })}>
                    <option value="">{locale === "ar" ? "كل الشركات" : "All companies"}</option>
                    {companies.map((c) => (<option key={c.id} value={c.id}>{locale === "ar" ? c.name_ar : c.name_en}</option>))}
                  </select>
                </div>
              ) : (
                <div>
                  <label className="label" htmlFor="ef-sector">{locale === "ar" ? "القطاع المستهدف" : "Target sector"}</label>
                  <input id="ef-sector" className="input" value={editForm.sector_scope} onChange={(e) => setEditForm({ ...editForm, sector_scope: e.target.value })} />
                </div>
              )}
              <div>
                <label className="label" htmlFor="ef-parent">{locale === "ar" ? "الحقل الرئيسي (اختياري)" : "Main field (optional)"}</label>
                <select id="ef-parent" className="input" value={editForm.parent_id} onChange={(e) => setEditForm({ ...editForm, parent_id: e.target.value })}>
                  <option value="">{locale === "ar" ? "— بلا حقل رئيسي —" : "— No main field —"}</option>
                  {fields.filter((f) => f.is_active && !f.parent_id && f.id !== editFor.id).map((f) => (
                    <option key={f.id} value={f.id}>{locale === "ar" ? f.name_ar : f.name_en}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input id="ef-required" type="checkbox" checked={editForm.is_required} onChange={(e) => setEditForm({ ...editForm, is_required: e.target.checked })} />
                <label htmlFor="ef-required">{locale === "ar" ? "إلزامي" : "Required"}</label>
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ" : "Save"}</button>
              <button type="button" className="btn-ghost" onClick={() => setEditFor(null)}>{locale === "ar" ? "إلغاء" : "Cancel"}</button>
            </div>
          </form>
        </div>
      )}
      <Toast message={message} />
    </section>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, loadError, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthImage } from "@/components/AuthImage";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const { locale, can } = useAuth();
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState<Partial<Company>>({});
  const [people, setPeople] = useState<{ id: number; full_name_ar: string; full_name_en: string }[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await api.get<Company>(`/api/v1/companies/${params.id}`);
      setCompany(c);
      setForm(c);
    } catch (e) {
      setError(
        loadError(e, locale, {
          ar: "الشركة غير موجودة أو غير مصرّح بالوصول إليها.",
          en: "The company does not exist or you are not permitted to view it.",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [params.id, locale]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (edit && people.length === 0) {
      api
        .get<{ id: number; full_name_ar: string; full_name_en: string }[]>("/api/v1/users/directory")
        .then(setPeople)
        .catch(() => undefined);
    }
  }, [edit, people.length]);

  async function save() {
    setMessage(null);
    try {
      await api.patch(`/api/v1/companies/${params.id}`, {
        name_ar: form.name_ar,
        name_en: form.name_en,
        country: form.country,
        sector: form.sector,
        contact_email: form.contact_email,
        contact_phone: form.contact_phone,
        ownership_percent: form.ownership_percent,
        currency: form.currency,
        manager_user_id: form.manager_user_id ? Number(form.manager_user_id) : null,
        activation_notes: form.activation_notes || null,
      });
      setMessage(locale === "ar" ? "تم الحفظ." : "Saved.");
      setEdit(false);
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر الحفظ." : "Could not save.");
    }
  }

  async function act(verb: "activate" | "close") {
    setMessage(null);
    try {
      await api.post(`/api/v1/companies/${params.id}/${verb}`);
      setMessage(verb === "activate" ? (locale === "ar" ? "تم تفعيل الشركة." : "Company activated.") : locale === "ar" ? "تم إغلاق الشركة." : "Company closed.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "فشل الإجراء." : "The action failed.");
    }
  }

  async function uploadLogo(file: File) {
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("company_id", String(params.id));
      const stored = await api.upload<{ id: number }>("/api/v1/files", form);
      await api.patch(`/api/v1/companies/${params.id}`, { logo_file_id: stored.id });
      setMessage(locale === "ar" ? "تم رفع الشعار." : "Logo uploaded.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر رفع الشعار. تأكد من أن الملف صورة." : "The logo upload failed. Make sure the file is an image.");
    }
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{company ? (locale === "ar" ? company.name_ar : company.name_en) : "…"}</h1>
        <div className="flex flex-wrap items-center gap-2">
          {company && <StatusChip value={company.status} />}
          {company?.logo_url && (
            // The official logo is shown as uploaded; proportions and colours
            // are preserved with object-contain.
            <AuthImage path={company.logo_url} alt="" className="h-9 w-9 rounded object-contain" />
          )}
          {company && can("company:manage") && company.status !== "closed" && (
            <label className="btn-ghost cursor-pointer">
              {locale === "ar" ? "الشعار" : "Logo"}
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void uploadLogo(file);
                }}
              />
            </label>
          )}
          {can("company:manage") && (
            <button type="button" className="btn-ghost" onClick={() => setEdit((v) => !v)}>
              {edit ? (locale === "ar" ? "إلغاء" : "Cancel") : locale === "ar" ? "تعديل" : "Edit"}
            </button>
          )}
          {company?.status === "draft" && can("company:manage") && (
            <button type="button" className="btn-gold" onClick={() => void act("activate")}>
              {locale === "ar" ? "تفعيل" : "Activate"}
            </button>
          )}
          {company?.status === "active" && can("company:manage") && (
            <button type="button" className="btn-ghost" onClick={() => void act("close")}>
              {locale === "ar" ? "إغلاق" : "Close"}
            </button>
          )}
        </div>
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      <DataStates loading={loading} error={error} empty={!company}>
        {company && (
          <div className="card grid gap-4 sm:grid-cols-2">
            {edit ? (
              <>
                {(
                  [
                    ["name_ar", locale === "ar" ? "الاسم بالعربية" : "Arabic name"],
                    ["name_en", locale === "ar" ? "الاسم بالإنجليزية" : "English name"],
                    ["country", locale === "ar" ? "الدولة" : "Country"],
                    ["sector", locale === "ar" ? "القطاع" : "Sector"],
                    ["contact_email", locale === "ar" ? "البريد الإلكتروني" : "Contact email"],
                    ["contact_phone", locale === "ar" ? "الهاتف" : "Contact phone"],
                    ["ownership_percent", locale === "ar" ? "نسبة الملكية" : "Ownership percentage"],
                    ["currency", locale === "ar" ? "العملة" : "Currency"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key}>
                    <label className="label" htmlFor={`co-${key}`}>{label}</label>
                    <input
                      id={`co-${key}`}
                      className="input"
                      dir={["name_ar"].includes(key) ? "rtl" : "ltr"}
                      value={String(form[key] ?? "")}
                      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    />
                  </div>
                ))}
                <div>
                  <label className="label" htmlFor="co-manager">{locale === "ar" ? "مدير الشركة" : "Company manager"}</label>
                  <select
                    id="co-manager"
                    className="input"
                    value={String(form.manager_user_id ?? "")}
                    onChange={(e) => setForm({ ...form, manager_user_id: e.target.value ? Number(e.target.value) : null })}
                  >
                    <option value="">{locale === "ar" ? "— بلا مدير —" : "— No manager —"}</option>
                    {people.map((p) => (
                      <option key={p.id} value={p.id}>
                        {locale === "ar" ? p.full_name_ar : p.full_name_en}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="label" htmlFor="co-activation">{locale === "ar" ? "معلومات التفعيل" : "Activation information"}</label>
                  <textarea
                    id="co-activation"
                    className="input"
                    rows={3}
                    value={String(form.activation_notes ?? "")}
                    onChange={(e) => setForm({ ...form, activation_notes: e.target.value })}
                  />
                </div>
                <div className="sm:col-span-2">
                  <button type="button" className="btn-primary" onClick={() => void save()}>
                    {locale === "ar" ? "حفظ" : "Save"}
                  </button>
                </div>
              </>
            ) : (
              <>
                {(
                  [
                    ["code", locale === "ar" ? "رمز الشركة" : "Company code"],
                    ["name_ar", locale === "ar" ? "الاسم بالعربية" : "Arabic name"],
                    ["name_en", locale === "ar" ? "الاسم بالإنجليزية" : "English name"],
                    ["country", locale === "ar" ? "الدولة" : "Country"],
                    ["sector", locale === "ar" ? "القطاع" : "Sector"],
                    ["contact_email", locale === "ar" ? "البريد الإلكتروني" : "Contact email"],
                    ["contact_phone", locale === "ar" ? "الهاتف" : "Contact phone"],
                    ["ownership_percent", locale === "ar" ? "نسبة الملكية" : "Ownership percentage"],
                    ["currency", locale === "ar" ? "العملة" : "Currency"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key}>
                    <dt className="muted">{label}</dt>
                    <dd dir={key === "name_ar" ? "rtl" : "ltr"}>{String(company[key] ?? "—")}</dd>
                  </div>
                ))}
                <div>
                  <dt className="muted">{locale === "ar" ? "مدير الشركة" : "Company manager"}</dt>
                  <dd>
                    {company.manager_name_ar || company.manager_name_en
                      ? locale === "ar"
                        ? company.manager_name_ar
                        : company.manager_name_en
                      : "—"}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="muted">{locale === "ar" ? "معلومات التفعيل" : "Activation information"}</dt>
                  <dd>{company.activation_notes || "—"}</dd>
                </div>
              </>
            )}
          </div>
        )}
      </DataStates>
    </section>
  );
}

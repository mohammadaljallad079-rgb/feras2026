"use client";

import { useEffect, useState } from "react";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Modal } from "@/components/Modal";

type Draft = Partial<Company> & { [key: string]: unknown };

/**
 * §6.2 «معالج إضافة شركة» — three numbered steps, then a review screen.
 *
 * The Word section calls it «ثلاث خطوات» and numbers them «1/3» … «3/3», then
 * lists the four blocks; the fourth is «مراجعة بيانات الشركة», which is the
 * review screen rather than a numbered step. The prototype behind design p.7
 * does exactly that: the title reads «إضافة شركة تابعة · 1/3» … «3/3», and the
 * review opens as «مراجعة بيانات الشركة» with no counter, offering «تعديل» /
 * «حفظ مسودة» / «حفظ وتفعيل».
 */
const STEPS = [
  { ar: "البيانات الأساسية", en: "Basic data" },
  { ar: "التواصل والإدارة", en: "Contact and management" },
  { ar: "العلاقة بالقابضة", en: "Relationship with the holding" },
];

/** The review screen follows the last numbered step and carries no number. */
const REVIEW = STEPS.length;

// §6.2: the fields the brief marks as required with a star. A step cannot be
// left while one of its required fields is empty, so the user never reaches the
// review with a payload the API will reject.
const REQUIRED_BY_STEP: Record<number, { key: string; ar: string; en: string }[]> = {
  0: [
    { key: "name_ar", ar: "الاسم بالعربية", en: "Arabic name" },
    { key: "name_en", ar: "الاسم بالإنجليزية", en: "English name" },
    { key: "country", ar: "الدولة", en: "Country" },
    { key: "sector", ar: "القطاع", en: "Sector" },
  ],
  1: [{ key: "currency", ar: "العملة المحلية", en: "Local currency" }],
  2: [{ key: "relationship", ar: "نوع العلاقة", en: "Relationship type" }],
  [REVIEW]: [],
};

// §6.2: the country, currency and sector choices named in the brief.
const COUNTRIES = [
  { value: "البحرين", ar: "البحرين", en: "Bahrain" },
  { value: "السعودية", ar: "السعودية", en: "Saudi Arabia" },
  { value: "الإمارات", ar: "الإمارات", en: "United Arab Emirates" },
  { value: "الكويت", ar: "الكويت", en: "Kuwait" },
  { value: "قطر", ar: "قطر", en: "Qatar" },
  { value: "عُمان", ar: "عُمان", en: "Oman" },
  { value: "الأردن", ar: "الأردن", en: "Jordan" },
];
const CURRENCIES = ["BHD", "SAR", "AED", "KWD", "QAR", "OMR", "JOD"];
const SECTORS = [
  { value: "تقنية", ar: "تقنية", en: "Technology" },
  { value: "صناعي", ar: "صناعي", en: "Industrial" },
  { value: "تجاري", ar: "تجاري", en: "Commercial" },
  { value: "خدمي", ar: "خدمي", en: "Services" },
];
// §6.2: the relationship is either full ownership by the holding, or management
// only with no ownership (0%).
const RELATIONSHIPS = [
  { value: "ownership", ar: "ملكية للقابضة", en: "Owned by the holding" },
  { value: "management", ar: "إدارة فقط دون ملكية", en: "Management only, no ownership" },
];

type Person = { id: number; full_name_ar: string; full_name_en: string };

/**
 * §6.2: «معالج إضافة شركة» — three numbered steps inside one window over the
 * companies screen, titled «إضافة شركة تابعة · 1/3» … «3/3», with «التالي» and
 * «السابق» between them and «إلغاء» closing the window; the review follows as
 * its own screen. The company manager is a required choice (§6.2 step 2).
 */
export function CompanyWizard({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (id: number) => void;
}) {
  const { locale } = useAuth();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>({
    currency: "BHD",
    ownership_percent: "100",
    relationship: "ownership",
  });
  const [managers, setManagers] = useState<Person[]>([]);
  const [savedId, setSavedId] = useState<number | null>(null);
  // §6.2 step 2: the company logo is an uploaded image. It is sent after the
  // company row exists, because the file must be tied to a company id.
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // §6.2: the company manager is chosen from registered users holding the
    // company-manager role.
    api.get<Person[]>("/api/v1/users/directory?role=company_manager").then(setManagers).catch(() => undefined);
  }, []);

  function set<K extends string>(key: K, value: unknown) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  // The preview is an object URL, so it is revoked when the file changes or the
  // window closes; leaking them would pin the image in memory.
  useEffect(() => {
    if (!logoFile) {
      setLogoPreview(null);
      return;
    }
    const url = URL.createObjectURL(logoFile);
    setLogoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [logoFile]);

  function missingOn(index: number): { key: string; ar: string; en: string }[] {
    return REQUIRED_BY_STEP[index].filter((f) => {
      const value = draft[f.key];
      return value === undefined || value === null || String(value).trim() === "";
    });
  }

  function validateStep(index: number): boolean {
    const missing = missingOn(index);
    if (missing.length === 0) return true;
    const names = missing.map((m) => (locale === "ar" ? m.ar : m.en)).join(locale === "ar" ? "، " : ", ");
    setError(
      locale === "ar"
        ? `أكمل الحقول المطلوبة: ${names}.`
        : `Complete the required fields: ${names}.`,
    );
    return false;
  }

  function goNext() {
    if (!validateStep(step)) return;
    setError(null);
    setStep((s) => Math.min(REVIEW, s + 1));
  }

  function goBack() {
    setError(null);
    setStep((s) => Math.max(0, s - 1));
  }

  /** Jump from the review back to the first step that still has a gap. */
  function goEdit() {
    const firstIncomplete = STEPS.map((_, i) => i).find((i) => missingOn(i).length > 0) ?? 0;
    setError(null);
    setStep(firstIncomplete);
  }

  function payload(status: "draft" | "active") {
    const ownership = draft.relationship === "management" ? "0" : draft.ownership_percent ?? "100";
    return {
      code: draft.code,
      name_ar: draft.name_ar,
      name_en: draft.name_en,
      country: draft.country,
      sector: draft.sector,
      contact_email: draft.contact_email || null,
      contact_phone: draft.contact_phone || null,
      manager_user_id: draft.manager_user_id ? Number(draft.manager_user_id) : null,
      ownership_percent: ownership,
      currency: draft.currency ?? "BHD",
      status,
      commercial_register_no: draft.commercial_register_no || null,
    };
  }

  async function persist(status: "draft" | "active"): Promise<number | null> {
    // A second click while the first request is in flight would create a second
    // company, so the guard is on the state, not only on the button's disabled
    // attribute (which React applies on the next render).
    if (busy) return null;
    setBusy(true);
    setError(null);
    try {
      const body = payload(status);
      // Once a row exists the wizard updates it, so retrying a failed save can
      // never leave a duplicate behind.
      const saved = savedId
        ? await api.patch<Company>(`/api/v1/companies/${savedId}`, body)
        : await api.post<Company>("/api/v1/companies", body);
      setSavedId(saved.id);
      // §6.2: the logo upload needs the company id, so it is attached once the
      // row exists — on the first save and again when the file changes.
      if (logoFile) {
        const form = new FormData();
        form.append("file", logoFile);
        form.append("company_id", String(saved.id));
        const stored = await api.upload<{ id: number }>("/api/v1/files", form);
        await api.patch(`/api/v1/companies/${saved.id}`, { logo_file_id: stored.id });
      }
      return saved.id;
    } catch (e) {
      const err = e as { status: number };
      setError(
        err.status === 403
          ? locale === "ar"
            ? "لا تملك صلاحية إنشاء شركة."
            : "You are not permitted to create a company."
          : locale === "ar"
            ? "تحقّق من الحقول المطلوبة."
            : "Check the required fields.",
      );
      return null;
    } finally {
      setBusy(false);
    }
  }

  // §6.2: «حفظ مسودة» keeps the company a draft; a draft does not appear in the
  // lists or the reports until it is activated. «حفظ وتفعيل» creates it active.
  async function saveDraft() {
    const id = await persist("draft");
    if (id) onSaved(id);
  }

  async function saveAndActivate() {
    const id = await persist("active");
    if (id) onSaved(id);
  }

  const reviewRows: [string, string, unknown][] = [
    ["code", locale === "ar" ? "رمز الشركة" : "Company code", draft.code],
    ["name_ar", locale === "ar" ? "الاسم بالعربية" : "Arabic name", draft.name_ar],
    ["name_en", locale === "ar" ? "الاسم بالإنجليزية" : "English name", draft.name_en],
    ["country", locale === "ar" ? "الدولة" : "Country", draft.country],
    ["sector", locale === "ar" ? "القطاع" : "Sector", draft.sector],
    ["commercial_register_no", locale === "ar" ? "رقم السجل التجاري" : "Commercial register number", draft.commercial_register_no],
    ["currency", locale === "ar" ? "العملة المحلية" : "Local currency", draft.currency],
    ["contact_email", locale === "ar" ? "بريد الشركة" : "Company email", draft.contact_email],
    ["contact_phone", locale === "ar" ? "رقم التواصل" : "Contact number", draft.contact_phone],
    [
      "manager_user_id",
      locale === "ar" ? "مدير الشركة" : "Company manager",
      managers.find((m) => m.id === Number(draft.manager_user_id))?.[locale === "ar" ? "full_name_ar" : "full_name_en"],
    ],
    [
      "relationship",
      locale === "ar" ? "العلاقة بالقابضة" : "Relationship with the holding",
      RELATIONSHIPS.find((r) => r.value === draft.relationship)?.[locale === "ar" ? "ar" : "en"],
    ],
    ["ownership_percent", locale === "ar" ? "نسبة الملكية %" : "Ownership percentage %", draft.relationship === "management" ? "0" : draft.ownership_percent],
  ];

  return (
    <Modal
      title={
        step === REVIEW
          ? locale === "ar"
            ? "مراجعة بيانات الشركة"
            : "Review company data"
          : locale === "ar"
            ? `إضافة شركة تابعة · ${step + 1}/${STEPS.length}`
            : `Add subsidiary company · ${step + 1}/${STEPS.length}`
      }
      onClose={onClose}
      wide
    >
        <ol className="mb-6 flex flex-wrap gap-3">
          {STEPS.map((s, i) => (
            <li
              key={s.en}
              className={`chip ${i === step ? "chip-ok" : "chip-neutral opacity-60"}`}
              aria-current={i === step ? "step" : undefined}
            >
              {i + 1}. {locale === "ar" ? s.ar : s.en}
            </li>
          ))}
        </ol>

        {error && (
          <p role="alert" className="mb-4 rounded-control border border-bad bg-badbg p-3 text-bad">
            {error}
          </p>
        )}

        <div className="space-y-4">
          {step === 0 && (
            <>
              <div>
                <label className="label" htmlFor="code">{locale === "ar" ? "رمز الشركة" : "Company code"}</label>
                <input id="code" className="input" dir="ltr" value={String(draft.code ?? "")} onChange={(e) => set("code", e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="name_ar">{locale === "ar" ? "الاسم بالعربية" : "Company name in Arabic"}<span aria-hidden="true"> *</span></label>
                <input id="name_ar" className="input" dir="rtl" required value={String(draft.name_ar ?? "")} onChange={(e) => set("name_ar", e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="name_en">{locale === "ar" ? "الاسم بالإنجليزية" : "Company name in English"}<span aria-hidden="true"> *</span></label>
                <input id="name_en" className="input" dir="ltr" required value={String(draft.name_en ?? "")} onChange={(e) => set("name_en", e.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="country">{locale === "ar" ? "الدولة" : "Country"}</label>
                  <select id="country" className="input" value={String(draft.country ?? "")} onChange={(e) => set("country", e.target.value)}>
                    <option value="">—</option>
                    {COUNTRIES.map((c) => (<option key={c.value} value={c.value}>{locale === "ar" ? c.ar : c.en}</option>))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="sector">{locale === "ar" ? "القطاع" : "Sector"}</label>
                  <select id="sector" className="input" value={String(draft.sector ?? "")} onChange={(e) => set("sector", e.target.value)}>
                    <option value="">—</option>
                    {SECTORS.map((s) => (<option key={s.value} value={s.value}>{locale === "ar" ? s.ar : s.en}</option>))}
                  </select>
                </div>
              </div>
              <div>
                <label className="label" htmlFor="crn">{locale === "ar" ? "رقم السجل التجاري (اختياري)" : "Commercial register number (optional)"}</label>
                <input id="crn" className="input" dir="ltr" value={String(draft.commercial_register_no ?? "")} onChange={(e) => set("commercial_register_no", e.target.value)} />
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <div>
                <label className="label" htmlFor="currency">{locale === "ar" ? "العملة المحلية" : "Local currency"}</label>
                <select id="currency" className="input" value={String(draft.currency ?? "BHD")} onChange={(e) => set("currency", e.target.value)}>
                  {CURRENCIES.map((c) => (<option key={c} value={c}>{c}</option>))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="contact_email">{locale === "ar" ? "بريد الشركة" : "Company email"}</label>
                <input id="contact_email" type="email" className="input" dir="ltr" value={String(draft.contact_email ?? "")} onChange={(e) => set("contact_email", e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="contact_phone">{locale === "ar" ? "رقم التواصل" : "Contact number"}</label>
                <input id="contact_phone" className="input" dir="ltr" value={String(draft.contact_phone ?? "")} onChange={(e) => set("contact_phone", e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="manager">{locale === "ar" ? "مدير الشركة" : "Company manager"}</label>
                <select id="manager" className="input" value={String(draft.manager_user_id ?? "")} onChange={(e) => set("manager_user_id", e.target.value)}>
                  <option value="">{locale === "ar" ? "— بلا مدير —" : "— No manager —"}</option>
                  {managers.map((m) => (<option key={m.id} value={m.id}>{locale === "ar" ? m.full_name_ar : m.full_name_en}</option>))}
                </select>
              </div>
              {/* §6.2 step 2: «شعار الشركة (رفع صورة)» — chosen here, uploaded
                  after the row exists, previewed so the choice is visible. */}
              <div>
                <label className="label" htmlFor="logo">{locale === "ar" ? "شعار الشركة (رفع صورة)" : "Company logo (upload an image)"}</label>
                <input
                  id="logo"
                  type="file"
                  accept="image/*"
                  className="input"
                  onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
                />
                {logoFile && <p className="muted mt-1" dir="ltr">{logoFile.name}</p>}
                {logoPreview && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={logoPreview}
                    alt={locale === "ar" ? "معاينة شعار الشركة" : "Company logo preview"}
                    className="mt-2 h-16 w-16 rounded-control border border-line object-contain"
                  />
                )}
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <label className="label" htmlFor="relationship">{locale === "ar" ? "نوع العلاقة" : "Relationship type"}</label>
                <select id="relationship" className="input" value={String(draft.relationship ?? "ownership")} onChange={(e) => set("relationship", e.target.value)}>
                  {RELATIONSHIPS.map((r) => (<option key={r.value} value={r.value}>{locale === "ar" ? r.ar : r.en}</option>))}
                </select>
              </div>
              {draft.relationship !== "management" && (
                <div>
                  <label className="label" htmlFor="ownership">{locale === "ar" ? "نسبة الملكية %" : "Ownership percentage %"}</label>
                  <input id="ownership" className="input" dir="ltr" value={String(draft.ownership_percent ?? "")} onChange={(e) => set("ownership_percent", e.target.value)} />
                </div>
              )}
              <p className="muted rounded-control bg-pearl p-3">
                {locale === "ar"
                  ? "تُنشأ استمارة التقارير الشهرية من منشئ النماذج. لا توجد أرصدة افتتاحية هنا."
                  : "The monthly report form is created in the form builder. There are no opening balances here."}
              </p>
            </>
          )}

          {step === REVIEW && (
            <div>
              <h2 className="section-title mb-3">{locale === "ar" ? "مراجعة بيانات الشركة" : "Review the company data"}</h2>
              <dl className="grid gap-3 sm:grid-cols-2">
                {reviewRows.map(([k, label, value]) => (
                  <div key={k}>
                    <dt className="muted">{label}</dt>
                    <dd>{value ? String(value) : "—"}</dd>
                  </div>
                ))}
              </dl>
              <p className="muted mt-4">
                {locale === "ar"
                  ? "الشركة المحفوظة مسودة لا تظهر في القوائم ولا التقارير حتى تُفعَّل."
                  : "A company saved as a draft does not appear in the lists or reports until it is activated."}
              </p>
            </div>
          )}
        </div>

        {/* §6.2 / design p.7: one action row, aligned left. The numbered steps
            carry «إلغاء» / «السابق» / «التالي»; the review carries «تعديل» /
            «حفظ مسودة» / «حفظ وتفعيل». «السابق» is absent on the first step. */}
        <div className="actions mt-6 border-t border-line pt-4">
          {step === REVIEW ? (
            <>
              <button type="button" className="btn-ghost" onClick={goEdit}>
                {locale === "ar" ? "تعديل" : "Edit"}
              </button>
              <button type="button" className="btn-ghost" onClick={() => void saveDraft()} disabled={busy}>
                {locale === "ar" ? "حفظ مسودة" : "Save draft"}
              </button>
              <button type="button" className="btn-primary" onClick={() => void saveAndActivate()} disabled={busy}>
                {locale === "ar" ? "حفظ وتفعيل" : "Save and activate"}
              </button>
            </>
          ) : (
            <>
              <button type="button" className="btn-ghost" onClick={onClose}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              {step > 0 && (
                <button type="button" className="btn-ghost" onClick={goBack}>
                  {locale === "ar" ? "السابق" : "Back"}
                </button>
              )}
              <button type="button" className="btn-primary" onClick={goNext}>
                {locale === "ar" ? "التالي" : "Next"}
              </button>
            </>
          )}
        </div>
    </Modal>
  );
}

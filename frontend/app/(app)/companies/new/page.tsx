"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { t } from "@/lib/i18n";

type Draft = Partial<Company> & { [key: string]: unknown };

const STEPS = [
  { ar: "البيانات الأساسية", en: "Basic data" },
  { ar: "بيانات التواصل", en: "Contact details" },
  { ar: "الملكية والعملة", en: "Ownership and currency" },
  { ar: "المراجعة", en: "Review" },
];

export default function NewCompanyPage() {
  const { locale } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>({ currency: "SAR", ownership_percent: "100", status: "draft" });
  const [savedId, setSavedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set<K extends string>(key: K, value: unknown) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function saveDraft(): Promise<number | null> {
    setBusy(true);
    setError(null);
    try {
      const payload = {
        code: draft.code,
        name_ar: draft.name_ar,
        name_en: draft.name_en,
        country: draft.country,
        sector: draft.sector,
        contact_email: draft.contact_email ?? null,
        contact_phone: draft.contact_phone ?? null,
        ownership_percent: draft.ownership_percent ?? "100",
        currency: draft.currency ?? "SAR",
        status: "draft",
      };
      const saved = savedId
        ? await api.patch<Company>(`/api/v1/companies/${savedId}`, payload)
        : await api.post<Company>("/api/v1/companies", payload);
      setSavedId(saved.id);
      return saved.id;
    } catch (e) {
      const err = e as { status: number; detail: unknown };
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

  async function finish() {
    const id = await saveDraft();
    if (id) router.push(`/companies/${id}`);
  }

  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="page-title mb-2">{t("companies", "wizard", locale) === "wizard" ? "إنشاء شركة (أربع خطوات)" : t("companies", "wizard", locale)}</h1>
      <ol className="mb-6 flex flex-wrap gap-3">
        {STEPS.map((s, i) => (
          <li
            key={s.en}
            className={`chip ${i === step ? "chip-ok" : "chip-neutral"}`}
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

      <div className="card space-y-4">
        {step === 0 && (
          <>
            <div>
              <label className="label" htmlFor="code">{locale === "ar" ? "رمز الشركة" : "Company code"}</label>
              <input id="code" className="input" dir="ltr" value={String(draft.code ?? "")} onChange={(e) => set("code", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="name_ar">{locale === "ar" ? "الاسم بالعربية" : "Arabic name"}</label>
              <input id="name_ar" className="input" dir="rtl" value={String(draft.name_ar ?? "")} onChange={(e) => set("name_ar", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="name_en">{locale === "ar" ? "الاسم بالإنجليزية" : "English name"}</label>
              <input id="name_en" className="input" dir="ltr" value={String(draft.name_en ?? "")} onChange={(e) => set("name_en", e.target.value)} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="country">{locale === "ar" ? "الدولة" : "Country"}</label>
                <input id="country" className="input" value={String(draft.country ?? "")} onChange={(e) => set("country", e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="sector">{locale === "ar" ? "القطاع" : "Sector"}</label>
                <input id="sector" className="input" value={String(draft.sector ?? "")} onChange={(e) => set("sector", e.target.value)} />
              </div>
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <div>
              <label className="label" htmlFor="contact_email">{locale === "ar" ? "البريد الإلكتروني" : "Contact email"}</label>
              <input id="contact_email" type="email" className="input" dir="ltr" value={String(draft.contact_email ?? "")} onChange={(e) => set("contact_email", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="contact_phone">{locale === "ar" ? "الهاتف" : "Contact phone"}</label>
              <input id="contact_phone" className="input" dir="ltr" value={String(draft.contact_phone ?? "")} onChange={(e) => set("contact_phone", e.target.value)} />
            </div>
          </>
        )}

        {step === 2 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="ownership">{locale === "ar" ? "نسبة الملكية" : "Ownership percentage"}</label>
              <input id="ownership" className="input" dir="ltr" value={String(draft.ownership_percent ?? "")} onChange={(e) => set("ownership_percent", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="currency">{locale === "ar" ? "العملة" : "Currency"}</label>
              <input id="currency" className="input" dir="ltr" value={String(draft.currency ?? "")} onChange={(e) => set("currency", e.target.value)} />
            </div>
          </div>
        )}

        {step === 3 && (
          <dl className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ["code", locale === "ar" ? "رمز الشركة" : "Company code"],
                ["name_ar", locale === "ar" ? "الاسم بالعربية" : "Arabic name"],
                ["name_en", locale === "ar" ? "الاسم بالإنجليزية" : "English name"],
                ["country", locale === "ar" ? "الدولة" : "Country"],
                ["sector", locale === "ar" ? "القطاع" : "Sector"],
                ["contact_email", locale === "ar" ? "البريد الإلكتروني" : "Contact email"],
                ["ownership_percent", locale === "ar" ? "نسبة الملكية" : "Ownership percentage"],
                ["currency", locale === "ar" ? "العملة" : "Currency"],
              ] as const
            ).map(([k, label]) => (
              <div key={k}>
                <dt className="muted">{label}</dt>
                <dd dir="ltr">{String(draft[k] ?? "—")}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4">
          <button type="button" className="btn-ghost" onClick={() => void saveDraft()} disabled={busy}>
            {locale === "ar" ? "حفظ كمسودة" : "Save draft"}
          </button>
          <div className="flex gap-2">
            <button type="button" className="btn-ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
              {locale === "ar" ? "السابق" : "Back"}
            </button>
            {step < STEPS.length - 1 ? (
              <button type="button" className="btn-primary" onClick={() => setStep((s) => s + 1)}>
                {locale === "ar" ? "التالي" : "Next"}
              </button>
            ) : (
              <button type="button" className="btn-primary" onClick={() => void finish()} disabled={busy}>
                {locale === "ar" ? "إنشاء الشركة" : "Create company"}
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

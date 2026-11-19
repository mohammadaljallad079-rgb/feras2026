"use client";

import { useState } from "react";
import type { Bi, Locale } from "@/lib/site";

type Kind = "contact" | "service_request" | "opportunity" | "job_application";

const T: Record<string, { ar: string; en: string }> = {
  name: { ar: "الاسم", en: "Name" },
  email: { ar: "البريد الإلكتروني", en: "Email" },
  phone: { ar: "رقم التواصل", en: "Contact number" },
  service_type: { ar: "نوع الخدمة", en: "Service type" },
  country: { ar: "دولة المشروع", en: "Project country" },
  subject: { ar: "موضوع الفرصة", en: "Opportunity subject" },
  expertise: { ar: "مجال الاهتمام أو الخبرة", en: "Area of interest or expertise" },
  message: { ar: "وصف مختصر", en: "Brief description" },
  cv: { ar: "السيرة الذاتية", en: "CV" },
  study: { ar: "ملف الدراسة أو المرفقات", en: "Study file or attachments" },
  consent: {
    ar: "أوافق على معالجة بياناتي وفق سياسة الخصوصية.",
    en: "I agree to the processing of my data under the privacy policy.",
  },
  submit: { ar: "إرسال الطلب", en: "Send request" },
  sending: { ar: "جارٍ الإرسال…", en: "Sending…" },
  cancel: { ar: "إلغاء (العودة للرئيسية)", en: "Cancel (back to home)" },
  viewPolicy: { ar: "عرض السياسة", en: "View policy" },
  ok: {
    ar: "تم استلام طلبك وتسجيله. رقم المرجع:",
    en: "Your request was received and recorded. Reference number:",
  },
  err: { ar: "تعذّر إرسال الطلب. تحقق من الحقول وحاول مجددًا.", en: "Could not send the request. Check the fields and try again." },
  required: { ar: "هذا الحقل مطلوب.", en: "This field is required." },
  consent_required: { ar: "يجب الموافقة على سياسة الخصوصية.", en: "Consent to the privacy policy is required." },
};

export type PublicFormProps = {
  kind: Kind;
  locale: Locale;
  /** Options for a select field (bilingual). */
  services?: { id: number; name_ar: string; name_en: string }[];
  countries?: Bi[];
  /** Show a file field; `required` for the CV. */
  file?: { label: keyof typeof T; required: boolean };
  consentHref: string;
};

export function PublicForm({ kind, locale, services = [], countries = [], file, consentHref }: PublicFormProps) {
  const ar = locale === "ar";
  const t = (k: keyof typeof T) => T[k][locale];

  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const needsPhone = kind !== "contact";
  const needsService = kind === "service_request";
  const needsCountry = kind === "opportunity";
  const needsSubject = kind === "opportunity";
  const needsExpertise = kind === "job_application";
  // Table 13 names the field «رقم التواصل» on the service form and «الهاتف» on
  // the other two.
  const phoneLabel = needsService
    ? { ar: "رقم التواصل", en: "Contact number" }
    : { ar: "الهاتف", en: "Phone" };

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = e.currentTarget;
    const data = new FormData(form);
    const consent = data.get("consent") === "on";
    if (!consent) {
      setError(t("consent_required"));
      return;
    }

    setBusy(true);
    try {
      const fileInput = form.querySelector<HTMLInputElement>('input[type="file"]');
      const hasFile = Boolean(fileInput?.files?.length);
      let res: Response;
      if (hasFile) {
        // Multipart path: the backend records the row and links the attachment
        // in one transaction.
        const body = new FormData();
        for (const field of ["name", "email", "phone", "message", "service_type", "country", "subject", "expertise"]) {
          const v = data.get(field);
          if (typeof v === "string" && v) body.append(field, v);
        }
        body.append("kind", kind);
        body.append("consent", "true");
        if (fileInput?.files?.[0]) body.append("attachment", fileInput.files[0]);
        res = await fetch("/api/backend/api/v1/public/submissions/with-file", { method: "POST", body });
      } else {
        res = await fetch("/api/backend/api/v1/public/submissions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind,
            name: data.get("name"),
            email: data.get("email"),
            phone: data.get("phone") || null,
            message: data.get("message") || null,
            service_type: data.get("service_type") || null,
            country: data.get("country") || null,
            subject: data.get("subject") || null,
            expertise: data.get("expertise") || null,
            consent: true,
          }),
        });
      }
      if (!res.ok) {
        setError(t("err"));
        return;
      }
      const payload = (await res.json()) as { reference_no: string | null };
      setDone(payload.reference_no ?? "");
      form.reset();
    } catch {
      setError(t("err"));
    } finally {
      setBusy(false);
    }
  }

  if (done !== null) {
    return (
      <div className="site-card border-brand-deep/30 bg-brand-mist" role="status" aria-live="polite">
        <p className="text-[15px] font-semibold text-brand-deep">
          {t("ok")} <span dir="ltr" className="font-mono">{done}</span>
        </p>
      </div>
    );
  }

  return (
    <form className="site-card grid gap-4" onSubmit={onSubmit} noValidate>
      {/* Table 13: every form page carries the «Start Up Sphere Gateway» brand
          and a note that the data is used to process the request under the
          privacy policy. */}
      <div className="border-b border-brand-line pb-3">
        <p className="text-[13px] font-bold uppercase tracking-widest text-brand-sand">
          {ar ? "بوابة ستارت أب سفير" : "Start Up Sphere Gateway"}
        </p>
        <p className="mt-1 text-[13px] text-brand-slate">
          {ar
            ? "تُستخدم بياناتك لمعالجة طلبك وفق سياسة الخصوصية."
            : "Your data is used to process your request under the privacy policy."}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="site-label" htmlFor="f-name">{t("name")} <span className="site-req">*</span></label>
          <input id="f-name" name="name" className="site-field" required maxLength={255} autoComplete="name" />
        </div>
        <div>
          <label className="site-label" htmlFor="f-email">{t("email")} <span className="site-req">*</span></label>
          <input id="f-email" name="email" type="email" className="site-field" required autoComplete="email" dir="ltr" />
        </div>
      </div>

      {needsPhone && (
        <div>
          <label className="site-label" htmlFor="f-phone">{phoneLabel[locale]} <span className="site-req">*</span></label>
          <input id="f-phone" name="phone" className="site-field" required dir="ltr" autoComplete="tel" />
        </div>
      )}

      {needsService && (
        <div>
          <label className="site-label" htmlFor="f-service">{t("service_type")} <span className="site-req">*</span></label>
          <select id="f-service" name="service_type" className="site-field" required defaultValue="">
            <option value="" disabled>{ar ? "اختر الخدمة" : "Select a service"}</option>
            {services.map((s) => (
              <option key={s.id} value={ar ? s.name_ar : s.name_en}>
                {ar ? s.name_ar : s.name_en}
              </option>
            ))}
          </select>
        </div>
      )}

      {needsCountry && (
        <div>
          <label className="site-label" htmlFor="f-country">{t("country")} <span className="site-req">*</span></label>
          <select id="f-country" name="country" className="site-field" required defaultValue="">
            <option value="" disabled>{ar ? "اختر الدولة" : "Select a country"}</option>
            {countries.map((c, i) => {
              const label = (ar ? c.ar : c.en) ?? "";
              return <option key={`${label}-${i}`} value={label}>{label}</option>;
            })}
          </select>
        </div>
      )}

      {needsSubject && (
        <div>
          <label className="site-label" htmlFor="f-subject">{t("subject")} <span className="site-req">*</span></label>
          <input id="f-subject" name="subject" className="site-field" required maxLength={255} />
        </div>
      )}

      {needsExpertise && (
        <div>
          <label className="site-label" htmlFor="f-expertise">{t("expertise")}</label>
          <input id="f-expertise" name="expertise" className="site-field" maxLength={255} />
        </div>
      )}

      <div>
        <label className="site-label" htmlFor="f-message">
          {t("message")} {needsCountry && <span className="site-req">*</span>}
        </label>
        <textarea
          id="f-message"
          name="message"
          className="site-field min-h-[120px]"
          rows={5}
          required={needsCountry}
        />
      </div>

      {file && (
        <div>
          <label className="site-label" htmlFor="f-file">
            {t(file.label)} {file.required && <span className="site-req">*</span>}
          </label>
          <input
            id="f-file"
            type="file"
            className="site-field"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
            required={file.required}
          />
        </div>
      )}

      <label className="flex items-start gap-3 text-[14px] text-brand-slate">
        <input type="checkbox" name="consent" className="mt-1" required />
        <span>
          {t("consent")}{" "}
          <a href={consentHref} className="text-brand-deep underline">
            {ar ? "سياسة الخصوصية" : "Privacy policy"}
          </a>
        </span>
      </label>

      {error && (
        <p role="alert" className="text-[14px] text-[#b3261e]">
          {error}
        </p>
      )}

      {/* Table 13: the service-request form carries «إرسال الطلب», «إلغاء (العودة
          للرئيسية)» and a «عرض السياسة» link. The other forms just send. */}
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="site-btn site-btn-primary w-fit" disabled={busy}>
          {busy ? t("sending") : needsService ? t("submit") : ar ? "إرسال" : "Submit"}
        </button>
        {needsService && (
          <>
            <a href={`/${locale}`} className="site-btn site-btn-outline w-fit">
              {t("cancel")}
            </a>
            <a href={consentHref} className="text-[14px] text-brand-deep underline">
              {t("viewPolicy")}
            </a>
          </>
        )}
      </div>
    </form>
  );
}

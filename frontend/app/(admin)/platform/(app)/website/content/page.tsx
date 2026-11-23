"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { Toast } from "@/components/Toast";
import { api, loadErrorState } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * Content editor for the public website.
 *
 * Every value here is the single source of truth for the public pages: editing
 * a field changes what `/[locale]` renders after the revalidate window. Values
 * still awaiting owner approval carry `needs_review`, and the editor surfaces
 * that rather than hiding it.
 */

type Setting = { id: number; key: string; value_ar: string | null; value_en: string | null };
type Section = {
  id: number;
  key: string;
  title_ar: string | null;
  title_en: string | null;
  body_ar: string | null;
  body_en: string | null;
  sort_order: number;
  is_visible: boolean;
  needs_review: boolean;
};
type Slide = {
  id: number;
  eyebrow_ar: string | null;
  eyebrow_en: string | null;
  title_ar: string;
  title_en: string;
  body_ar: string | null;
  body_en: string | null;
  cta_primary_label_ar: string | null;
  cta_primary_label_en: string | null;
  cta_primary_href: string | null;
  cta_secondary_label_ar: string | null;
  cta_secondary_label_en: string | null;
  cta_secondary_href: string | null;
  sort_order: number;
  is_active: boolean;
};
type Service = {
  id: number;
  slug: string;
  name_ar: string;
  name_en: string;
  description_ar: string | null;
  description_en: string | null;
  sort_order: number;
  is_active: boolean;
  needs_review: boolean;
};
type NavLink = {
  id: number;
  location: string;
  label_ar: string;
  label_en: string;
  href: string;
  sort_order: number;
  is_active: boolean;
};

type Tab = "settings" | "sections" | "slides" | "services" | "nav";

const SETTING_LABELS: Record<string, { ar: string; en: string }> = {
  brand_name: { ar: "اسم الشركة", en: "Company name" },
  brand_short: { ar: "الاسم المختصر", en: "Short name" },
  seo_title: { ar: "عنوان الصفحة (SEO)", en: "Page title (SEO)" },
  seo_description: { ar: "وصف الموقع (SEO)", en: "Site description (SEO)" },
  contact_email: { ar: "البريد الإلكتروني", en: "Contact email" },
  contact_phone: { ar: "رقم الهاتف", en: "Contact phone" },
  country: { ar: "الدولة", en: "Country" },
  opportunity_notice: { ar: "تنبيه الفرص", en: "Opportunity notice" },
};

export default function SiteContentPage() {
  const { locale, can } = useAuth();
  const ar = locale === "ar";
  const [tab, setTab] = useState<Tab>("settings");
  const [settings, setSettings] = useState<Setting[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [nav, setNav] = useState<NavLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, sec, sl, sv, nv] = await Promise.all([
        api.get<Setting[]>("/api/v1/website/settings"),
        api.get<Section[]>("/api/v1/website/sections"),
        api.get<Slide[]>("/api/v1/website/slides"),
        api.get<Service[]>("/api/v1/website/services"),
        api.get<NavLink[]>("/api/v1/website/nav"),
      ]);
      setSettings(s);
      setSections(sec);
      setSlides(sl);
      setServices(sv);
      setNav(nv);
      setError(null);
    } catch (e) {
      setError(loadErrorState(e, locale));
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(path: string, body: unknown, okAr: string, okEn: string) {
    setMessage(null);
    try {
      await api.patch(path, body);
      setMessage(ar ? okAr : okEn);
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(
        err.status === 403
          ? ar
            ? "لا تملك صلاحية تعديل محتوى الموقع."
            : "You are not permitted to edit website content."
          : ar
            ? "تعذّر حفظ التغييرات."
            : "Could not save the changes.",
      );
    }
  }

  const tabs: { id: Tab; ar: string; en: string }[] = [
    { id: "settings", ar: "الإعدادات", en: "Settings" },
    { id: "sections", ar: "الأقسام", en: "Sections" },
    { id: "slides", ar: "الشرائح", en: "Slides" },
    { id: "services", ar: "الخدمات", en: "Services" },
    { id: "nav", ar: "قوائم التنقل", en: "Navigation" },
  ];

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{ar ? "محتوى الموقع" : "Website content"}</h1>
        <p className="muted">
          {ar
            ? "هذا المحتوى يظهر على الموقع العام مباشرة. القيم التي لم تُعتمد تبقى موسومة بانتظار المراجعة."
            : "This content appears on the public site directly. Values not yet approved stay flagged for review."}
        </p>
      </header>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist">
        {tabs.map((tb) => (
          <button
            key={tb.id}
            type="button"
            role="tab"
            aria-selected={tab === tb.id}
            className={tab === tb.id ? "btn-primary" : "btn-ghost"}
            onClick={() => setTab(tb.id)}
          >
            {ar ? tb.ar : tb.en}
          </button>
        ))}
      </div>


      <DataStates loading={loading} error={error} empty={false}>
        {tab === "settings" && (
          <div className="grid gap-3">
            {settings.map((s) => (
              <SettingRow
                key={s.key}
                setting={s}
                label={SETTING_LABELS[s.key]}
                ar={ar}
                canEdit={can("site:manage")}
                onSave={(body) => save(`/api/v1/website/settings/${s.key}`, body, "تم الحفظ.", "Saved.")}
              />
            ))}
          </div>
        )}

        {tab === "sections" && (
          <div className="grid gap-3">
            {sections.map((s) => (
              <SectionRow
                key={s.id}
                section={s}
                ar={ar}
                canEdit={can("site:manage")}
                onSave={(body) => save(`/api/v1/website/sections/${s.id}`, body, "تم حفظ القسم.", "Section saved.")}
              />
            ))}
          </div>
        )}

        {tab === "slides" && (
          <div className="grid gap-3">
            {slides.map((s) => (
              <SlideRow
                key={s.id}
                slide={s}
                ar={ar}
                canEdit={can("site:manage")}
                onSave={(body) => save(`/api/v1/website/slides/${s.id}`, body, "تم حفظ الشريحة.", "Slide saved.")}
              />
            ))}
          </div>
        )}

        {tab === "services" && (
          <div className="grid gap-3">
            {services.map((s) => (
              <ServiceRow
                key={s.id}
                service={s}
                ar={ar}
                canEdit={can("site:manage")}
                onSave={(body) => save(`/api/v1/website/services/${s.id}`, body, "تم حفظ الخدمة.", "Service saved.")}
              />
            ))}
          </div>
        )}

        {tab === "nav" && (
          <div className="grid gap-3">
            {nav.map((n) => (
              <NavRow
                key={n.id}
                link={n}
                ar={ar}
                canEdit={can("site:manage")}
                onSave={(body) => save(`/api/v1/website/nav/${n.id}`, body, "تم حفظ الرابط.", "Link saved.")}
              />
            ))}
          </div>
        )}
      </DataStates>
      <Toast message={message} />
    </section>
  );
}

/** A single bilingual field pair with its own save button. */
function Field({
  label,
  value,
  onChange,
  dir,
  multiline,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  dir?: "ltr" | "rtl";
  multiline?: boolean;
  disabled?: boolean;
}) {
  return (
    <label className="grid gap-1">
      <span className="text-secondary muted">{label}</span>
      {multiline ? (
        <textarea className="input" rows={3} value={value} dir={dir} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input className="input" value={value} dir={dir} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
      )}
    </label>
  );
}

function SettingRow({
  setting,
  label,
  ar,
  canEdit,
  onSave,
}: {
  setting: Setting;
  label?: { ar: string; en: string };
  ar: boolean;
  canEdit: boolean;
  onSave: (body: unknown) => void;
}) {
  const [va, setVa] = useState(setting.value_ar ?? "");
  const [ve, setVe] = useState(setting.value_en ?? "");
  const name = label ? (ar ? label.ar : label.en) : setting.key;
  return (
    <div className="card grid gap-3">
      <div className="flex items-center justify-between">
        <h2 className="section-title">{name}</h2>
        <code className="muted" dir="ltr">{setting.key}</code>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={ar ? "العربية" : "Arabic"} value={va} dir="rtl" onChange={setVa} disabled={!canEdit} />
        <Field label={ar ? "الإنجليزية" : "English"} value={ve} dir="ltr" onChange={setVe} disabled={!canEdit} />
      </div>
      {canEdit && (
        <button type="button" className="btn-primary w-fit" onClick={() => onSave({ value_ar: va, value_en: ve })}>
          {ar ? "حفظ" : "Save"}
        </button>
      )}
    </div>
  );
}

function SectionRow({
  section,
  ar,
  canEdit,
  onSave,
}: {
  section: Section;
  ar: boolean;
  canEdit: boolean;
  onSave: (body: unknown) => void;
}) {
  const [ta, setTa] = useState(section.title_ar ?? "");
  const [te, setTe] = useState(section.title_en ?? "");
  const [ba, setBa] = useState(section.body_ar ?? "");
  const [be, setBe] = useState(section.body_en ?? "");
  const [visible, setVisible] = useState(section.is_visible);
  return (
    <div className="card grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="section-title">
          {section.key}
          {section.needs_review && <span className="chip-warn ms-2">{ar ? "بانتظار المراجعة" : "Needs review"}</span>}
        </h2>
        <label className="flex items-center gap-2 text-secondary">
          <input type="checkbox" checked={visible} disabled={!canEdit} onChange={(e) => setVisible(e.target.checked)} />
          {ar ? "ظاهر" : "Visible"}
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={ar ? "العنوان (عربي)" : "Title (Arabic)"} value={ta} dir="rtl" onChange={setTa} disabled={!canEdit} />
        <Field label={ar ? "العنوان (إنجليزي)" : "Title (English)"} value={te} dir="ltr" onChange={setTe} disabled={!canEdit} />
        <Field label={ar ? "النص (عربي)" : "Body (Arabic)"} value={ba} dir="rtl" multiline onChange={setBa} disabled={!canEdit} />
        <Field label={ar ? "النص (إنجليزي)" : "Body (English)"} value={be} dir="ltr" multiline onChange={setBe} disabled={!canEdit} />
      </div>
      {canEdit && (
        <button
          type="button"
          className="btn-primary w-fit"
          onClick={() => onSave({ title_ar: ta, title_en: te, body_ar: ba, body_en: be, is_visible: visible })}
        >
          {ar ? "حفظ" : "Save"}
        </button>
      )}
    </div>
  );
}

function SlideRow({
  slide,
  ar,
  canEdit,
  onSave,
}: {
  slide: Slide;
  ar: boolean;
  canEdit: boolean;
  onSave: (body: unknown) => void;
}) {
  const [ea, setEa] = useState(slide.eyebrow_ar ?? "");
  const [ee, setEe] = useState(slide.eyebrow_en ?? "");
  const [ta, setTa] = useState(slide.title_ar);
  const [te, setTe] = useState(slide.title_en);
  const [ba, setBa] = useState(slide.body_ar ?? "");
  const [be, setBe] = useState(slide.body_en ?? "");
  const [pl, setPl] = useState(slide.cta_primary_label_ar ?? "");
  const [plen, setPlen] = useState(slide.cta_primary_label_en ?? "");
  const [ph, setPh] = useState(slide.cta_primary_href ?? "");
  const [sl, setSl] = useState(slide.cta_secondary_label_ar ?? "");
  const [slen, setSlen] = useState(slide.cta_secondary_label_en ?? "");
  const [sh, setSh] = useState(slide.cta_secondary_href ?? "");
  const [active, setActive] = useState(slide.is_active);
  return (
    <div className="card grid gap-3">
      <div className="flex items-center justify-between">
        <h2 className="section-title">{ar ? `شريحة #${slide.id}` : `Slide #${slide.id}`}</h2>
        <label className="flex items-center gap-2 text-secondary">
          <input type="checkbox" checked={active} disabled={!canEdit} onChange={(e) => setActive(e.target.checked)} />
          {ar ? "مفعّلة" : "Active"}
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={ar ? "الوسم (عربي)" : "Tag line (Arabic)"} value={ea} dir="rtl" onChange={setEa} disabled={!canEdit} />
        <Field label={ar ? "الوسم (إنجليزي)" : "Tag line (English)"} value={ee} dir="ltr" onChange={setEe} disabled={!canEdit} />
        <Field label={ar ? "العنوان (عربي)" : "Title (Arabic)"} value={ta} dir="rtl" onChange={setTa} disabled={!canEdit} />
        <Field label={ar ? "العنوان (إنجليزي)" : "Title (English)"} value={te} dir="ltr" onChange={setTe} disabled={!canEdit} />
        <Field label={ar ? "النص (عربي)" : "Body (Arabic)"} value={ba} dir="rtl" multiline onChange={setBa} disabled={!canEdit} />
        <Field label={ar ? "النص (إنجليزي)" : "Body (English)"} value={be} dir="ltr" multiline onChange={setBe} disabled={!canEdit} />
        <Field label={ar ? "زر رئيسي (عربي)" : "Primary button (Arabic)"} value={pl} dir="rtl" onChange={setPl} disabled={!canEdit} />
        <Field label={ar ? "زر رئيسي (إنجليزي)" : "Primary button (English)"} value={plen} dir="ltr" onChange={setPlen} disabled={!canEdit} />
        <Field label={ar ? "رابط الزر الرئيسي" : "Primary button link"} value={ph} dir="ltr" onChange={setPh} disabled={!canEdit} />
        <Field label={ar ? "زر ثانوي (عربي)" : "Secondary button (Arabic)"} value={sl} dir="rtl" onChange={setSl} disabled={!canEdit} />
        <Field label={ar ? "زر ثانوي (إنجليزي)" : "Secondary button (English)"} value={slen} dir="ltr" onChange={setSlen} disabled={!canEdit} />
        <Field label={ar ? "رابط الزر الثانوي" : "Secondary button link"} value={sh} dir="ltr" onChange={setSh} disabled={!canEdit} />
      </div>
      {canEdit && (
        <button
          type="button"
          className="btn-primary w-fit"
          onClick={() =>
            onSave({
              eyebrow_ar: ea,
              eyebrow_en: ee,
              title_ar: ta,
              title_en: te,
              body_ar: ba,
              body_en: be,
              cta_primary_label_ar: pl,
              cta_primary_label_en: plen,
              cta_primary_href: ph,
              cta_secondary_label_ar: sl,
              cta_secondary_label_en: slen,
              cta_secondary_href: sh,
              is_active: active,
            })
          }
        >
          {ar ? "حفظ" : "Save"}
        </button>
      )}
    </div>
  );
}

function ServiceRow({
  service,
  ar,
  canEdit,
  onSave,
}: {
  service: Service;
  ar: boolean;
  canEdit: boolean;
  onSave: (body: unknown) => void;
}) {
  const [na, setNa] = useState(service.name_ar);
  const [ne, setNe] = useState(service.name_en);
  const [da, setDa] = useState(service.description_ar ?? "");
  const [de, setDe] = useState(service.description_en ?? "");
  const [active, setActive] = useState(service.is_active);
  const [review, setReview] = useState(service.needs_review);
  return (
    <div className="card grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="section-title">
          <code dir="ltr">{service.slug}</code>
          {service.needs_review && <span className="chip-warn ms-2">{ar ? "بانتظار المراجعة" : "Needs review"}</span>}
        </h2>
        <div className="flex gap-4 text-secondary">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={active} disabled={!canEdit} onChange={(e) => setActive(e.target.checked)} />
            {ar ? "مفعّلة" : "Active"}
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={review} disabled={!canEdit} onChange={(e) => setReview(e.target.checked)} />
            {ar ? "بانتظار المراجعة" : "Needs review"}
          </label>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={ar ? "الاسم (عربي)" : "Name (Arabic)"} value={na} dir="rtl" onChange={setNa} disabled={!canEdit} />
        <Field label={ar ? "الاسم (إنجليزي)" : "Name (English)"} value={ne} dir="ltr" onChange={setNe} disabled={!canEdit} />
        <Field label={ar ? "الوصف (عربي)" : "Description (Arabic)"} value={da} dir="rtl" multiline onChange={setDa} disabled={!canEdit} />
        <Field label={ar ? "الوصف (إنجليزي)" : "Description (English)"} value={de} dir="ltr" multiline onChange={setDe} disabled={!canEdit} />
      </div>
      {canEdit && (
        <button
          type="button"
          className="btn-primary w-fit"
          onClick={() =>
            onSave({
              name_ar: na,
              name_en: ne,
              description_ar: da,
              description_en: de,
              is_active: active,
              needs_review: review,
            })
          }
        >
          {ar ? "حفظ" : "Save"}
        </button>
      )}
    </div>
  );
}

function NavRow({
  link,
  ar,
  canEdit,
  onSave,
}: {
  link: NavLink;
  ar: boolean;
  canEdit: boolean;
  onSave: (body: unknown) => void;
}) {
  const [la, setLa] = useState(link.label_ar);
  const [le, setLe] = useState(link.label_en);
  const [href, setHref] = useState(link.href);
  const [active, setActive] = useState(link.is_active);
  return (
    <div className="card grid gap-3">
      <div className="flex items-center justify-between">
        <h2 className="section-title">
          {link.location === "header" ? (ar ? "القائمة العلوية" : "Header menu") : ar ? "قائمة التذييل" : "Footer menu"}
        </h2>
        <label className="flex items-center gap-2 text-secondary">
          <input type="checkbox" checked={active} disabled={!canEdit} onChange={(e) => setActive(e.target.checked)} />
          {ar ? "مفعّل" : "Active"}
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label={ar ? "التسمية (عربي)" : "Label (Arabic)"} value={la} dir="rtl" onChange={setLa} disabled={!canEdit} />
        <Field label={ar ? "التسمية (إنجليزي)" : "Label (English)"} value={le} dir="ltr" onChange={setLe} disabled={!canEdit} />
        <Field label={ar ? "الرابط" : "Link"} value={href} dir="ltr" onChange={setHref} disabled={!canEdit} />
      </div>
      {canEdit && (
        <button
          type="button"
          className="btn-primary w-fit"
          onClick={() => onSave({ label_ar: la, label_en: le, href, is_active: active })}
        >
          {ar ? "حفظ" : "Save"}
        </button>
      )}
    </div>
  );
}

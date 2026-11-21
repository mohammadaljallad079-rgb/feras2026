"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { pick, type Locale, type SiteSlide } from "@/lib/site";

/**
 * Hero slider. The slides come from the CMS. Auto-advance pauses on hover and
 * on keyboard focus, and every control is a real button or link so the slider
 * is usable without a mouse.
 */
export function HeroSlider({ locale, slides }: { locale: Locale; slides: SiteSlide[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const ar = locale === "ar";

  useEffect(() => {
    if (paused || slides.length <= 1) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % slides.length), 7000);
    return () => window.clearInterval(id);
  }, [paused, slides.length]);

  if (slides.length === 0) {
    return (
      <section className="bg-gradient-to-br from-brand-deep to-brand-ink py-24 text-white">
        <div className="site-container">
          <h1 className="text-[42px] font-bold leading-tight">
            {ar ? "ستارت أب سفير القابضة" : "Start Up Sphere Holding"}
          </h1>
        </div>
      </section>
    );
  }

  return (
    <section
      className="relative overflow-hidden bg-brand-deep text-white"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
      aria-roledescription="carousel"
      aria-label={ar ? "أبرز الرسائل" : "Highlights"}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 [background:radial-gradient(1100px_520px_at_78%_-10%,rgba(12,143,173,.35),transparent_60%),linear-gradient(115deg,#075e73_0%,#0a7c94_58%,#0d2230_100%)]"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-[0.14] [background-image:linear-gradient(rgba(255,255,255,.14)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.14)_1px,transparent_1px)] [background-size:64px_64px]"
      />

      <div className="site-container relative py-24">
        {/* Every slide stays in the DOM so all deck headlines are crawlable;
            only the active one is shown. */}
        {slides.map((s, i) => {
          const active = i === Math.min(index, slides.length - 1);
          const Heading = active ? "h1" : "p";
          return (
            <div key={s.id} hidden={!active} aria-hidden={!active}>
              {s.eyebrow_ar || s.eyebrow_en ? (
                <p className="site-eyebrow">{pick(locale, s.eyebrow_ar, s.eyebrow_en)}</p>
              ) : null}
              <Heading className="mt-5 max-w-[820px] text-[38px] font-bold leading-tight tracking-tight sm:text-[46px]">
                {pick(locale, s.title_ar, s.title_en)}
              </Heading>
              {(s.body_ar || s.body_en) && (
                <p className="mt-5 max-w-[620px] text-[17px] text-[#c9dbe2]">
                  {pick(locale, s.body_ar, s.body_en)}
                </p>
              )}

              <div className="mt-9 flex flex-wrap gap-3">
                {s.cta_primary_label_ar || s.cta_primary_label_en ? (
                  <Link
                    href={`/${locale}${s.cta_primary_href || "/service-request"}`}
                    className="site-btn site-btn-sand"
                  >
                    {pick(locale, s.cta_primary_label_ar, s.cta_primary_label_en)}
                  </Link>
                ) : null}
                {s.cta_secondary_label_ar || s.cta_secondary_label_en ? (
                  <Link
                    href={`/${locale}${s.cta_secondary_href || "/opportunities"}`}
                    className="site-btn site-btn-ghost"
                  >
                    {pick(locale, s.cta_secondary_label_ar, s.cta_secondary_label_en)}
                  </Link>
                ) : null}
              </div>
            </div>
          );
        })}

        {slides.length > 1 && (
          <div className="mt-12 flex items-center gap-3" role="tablist" aria-label={ar ? "الشرائح" : "Slides"}>
            {slides.map((s, i) => (
              <button
                key={s.id}
                type="button"
                role="tab"
                aria-selected={i === index}
                aria-label={ar ? `الشريحة ${i + 1}` : `Slide ${i + 1}`}
                onClick={() => setIndex(i)}
                className={`h-1.5 rounded-full transition-all ${
                  i === index ? "w-13 bg-brand-sand" : "w-8 bg-white/30"
                }`}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

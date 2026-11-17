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

  const slide = slides[Math.min(index, slides.length - 1)];

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
        <p className="site-eyebrow">{ar ? "شركة قابضة بحرينية" : "A Bahraini holding company"}</p>
        <h1
          key={slide.id}
          className="mt-5 max-w-[820px] text-[38px] font-bold leading-tight tracking-tight sm:text-[46px]"
        >
          {pick(locale, slide.title_ar, slide.title_en)}
        </h1>
        {(slide.body_ar || slide.body_en) && (
          <p className="mt-5 max-w-[620px] text-[17px] text-[#c9dbe2]">
            {pick(locale, slide.body_ar, slide.body_en)}
          </p>
        )}

        <div className="mt-9 flex flex-wrap gap-3">
          {slide.cta_primary_label_ar || slide.cta_primary_label_en ? (
            <Link
              href={`/${locale}${slide.cta_primary_href || "/service-request"}`}
              className="site-btn site-btn-sand"
            >
              {pick(locale, slide.cta_primary_label_ar, slide.cta_primary_label_en)}
            </Link>
          ) : null}
          {slide.cta_secondary_label_ar || slide.cta_secondary_label_en ? (
            <Link
              href={`/${locale}${slide.cta_secondary_href || "/opportunities"}`}
              className="site-btn site-btn-ghost"
            >
              {pick(locale, slide.cta_secondary_label_ar, slide.cta_secondary_label_en)}
            </Link>
          ) : null}
        </div>

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

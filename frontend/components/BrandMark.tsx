"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Official brand mark.
 *
 * `/brand/holding-logo.png` is served straight from `frontend/public/brand/`
 * and is used exactly as supplied: never recoloured, cropped or redrawn. Only
 * the rendered height is constrained, so the artwork keeps its own aspect ratio
 * (the supplied file is a landscape 245x132 lockup).
 *
 * The artwork is dark teal drawn on transparency, so it reads well on a light
 * card but loses contrast on the navy sidebar and on dark-mode cards — on the
 * sidebar only ~3.9:1 on average, with 18.8% of its pixels under the 3:1 that
 * WCAG 1.4.11 asks of a graphical object. Rather than alter its colours,
 * `plate` seats it on a light surface, the usual way a light-background logo is
 * carried on dark chrome.
 */
export function BrandMark({
  name,
  size = 36,
  tone = "onDark",
  plate,
  layout = "row",
}: {
  /** Optional label beside or under the mark; omit when the screen already
   *  shows the platform name, so it is not printed twice. */
  name?: string;
  size?: number;
  /** "onDark" for the navy sidebar, "onCard" for card surfaces. */
  tone?: "onDark" | "onCard";
  /**
   * Light plate behind the mark. Defaults to "always" on the navy sidebar and
   * "adaptive" (dark theme only) on cards; pass "none" to opt out.
   */
  plate?: "always" | "adaptive" | "none";
  /** "row" puts the label beside the mark; "stack" puts it underneath, which
   *  suits the wide lockup in the narrow sidebar. */
  layout?: "row" | "stack";
}) {
  const [failed, setFailed] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);

  // The mark is server-rendered, so a missing file 404s before React hydrates
  // and `onError` never fires; the page would keep a broken-image icon. Re-check
  // on mount so a deployment without the asset degrades to the name alone.
  useEffect(() => {
    const img = imgRef.current;
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, []);

  const mode = plate ?? (tone === "onDark" ? "always" : "adaptive");
  const plateClass =
    mode === "always" ? "brand-plate brand-plate-solid" : mode === "adaptive" ? "brand-plate brand-plate-adaptive" : "";

  return (
    <span className={`flex ${layout === "stack" ? "flex-col items-start gap-2" : "items-center gap-3"}`}>
      {!failed && (
        <span className={plateClass}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={imgRef}
            className="block"
            src="/brand/holding-logo.png"
            alt={name ?? ""}
            height={size}
            style={{ height: size, width: "auto" }}
            onError={() => setFailed(true)}
          />
        </span>
      )}
      {name && (
        <span className={`text-section font-semibold ${tone === "onDark" ? "text-white" : "text-ink"}`}>{name}</span>
      )}
    </span>
  );
}

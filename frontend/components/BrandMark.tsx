"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Official brand mark.
 *
 * The platform must use the supplied STARTUP / Safir Holding logo unchanged:
 * `/brand/holding-logo.png` is served straight from `frontend/public/brand/`.
 * The image is never recoloured, cropped or redrawn — it is placed at its own
 * aspect ratio and only its rendered height is constrained.
 *
 * When that file has not been supplied yet, the component falls back to a
 * neutral text mark and flags itself with `data-logo="missing"` so the gap is
 * visible in the DOM and in the screenshot audit rather than silently passing
 * as the approved branding.
 */
export function BrandMark({
  name,
  size = 36,
  tone = "onDark",
}: {
  name: string;
  size?: number;
  /** "onDark" for the navy sidebar, "onCard" for light surfaces. */
  tone?: "onDark" | "onCard";
}) {
  const [failed, setFailed] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);

  // The logo is server-rendered, so a missing file 404s before React hydrates
  // and `onError` never fires — the page would show a broken-image icon with an
  // empty box. Re-check on mount to catch that pre-hydration failure.
  useEffect(() => {
    const img = imgRef.current;
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, []);

  return (
    <span className="flex items-center gap-3">
      {failed ? (
        // Deliberately neutral — pearl, not the gold brand accent — so it can
        // never be mistaken for approved branding. The reference defers the
        // logo to the designer (page 32), so nothing here imitates one.
        <span
          data-logo="missing"
          title="Official logo not supplied: expected frontend/public/brand/holding-logo.png"
          className="flex items-center justify-center rounded-control border border-dashed border-sidefg/40 bg-sidefg/10 font-semibold text-sidefg"
          style={{ height: size, width: size }}
          aria-hidden="true"
        >
          ⌾
        </span>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          ref={imgRef}
          data-logo="official"
          src="/brand/holding-logo.png"
          alt={name}
          height={size}
          style={{ height: size, width: "auto" }}
          onError={() => setFailed(true)}
        />
      )}
      <span className={`text-section font-semibold ${tone === "onDark" ? "text-white" : "text-ink"}`}>
        {name}
      </span>
    </span>
  );
}

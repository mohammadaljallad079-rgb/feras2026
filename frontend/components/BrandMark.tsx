"use client";

import { useState } from "react";

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

  return (
    <span className="flex items-center gap-3">
      {failed ? (
        <span
          data-logo="missing"
          title="Official logo not supplied: expected frontend/public/brand/holding-logo.png"
          className="flex items-center justify-center rounded-full bg-gold font-bold text-goldink"
          style={{ height: size, width: size }}
          aria-hidden="true"
        >
          ص
        </span>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
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

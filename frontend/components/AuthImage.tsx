"use client";

import { useEffect, useState } from "react";
import { getAccessToken } from "@/lib/api";

/**
 * Renders a private file served by the authenticated download endpoint.
 *
 * A plain ``<img src>`` cannot carry the bearer token, so the bytes are fetched
 * with the token and shown through an object URL. The server still authorizes
 * every request; this only solves the transport, not the access check.
 */
export function AuthImage({
  path,
  alt = "",
  className,
}: {
  path: string;
  alt?: string;
  className?: string;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let revoked = false;
    let objectUrl: string | null = null;
    const token = getAccessToken();
    void (async () => {
      try {
        const resp = await fetch(`/api/backend${path}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!resp.ok) return;
        const blob = await resp.blob();
        objectUrl = URL.createObjectURL(blob);
        if (revoked) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setUrl(objectUrl);
      } catch {
        // A missing logo is not an error state; the caller shows a placeholder.
      }
    })();
    return () => {
      revoked = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (!url) return null;
  // The source is a blob: URL built from an authenticated fetch, which the
  // Next.js image optimiser cannot reach.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} className={className} />;
}

"use client";

import { useEffect, useState } from "react";

/** Design p.4: the toast is visible for 3 seconds, then it goes away on its own. */
const TOAST_MS = 3000;

/**
 * §2 «الرسالة العابرة (Toast): تأكيد قصير أسفل الشاشة بعد الإجراء» — the
 * confirmation of an action is a short message pinned to the bottom of the
 * screen rather than a block in the page flow.
 *
 * The message hides itself after 3 seconds (design reference page 4). The timer
 * is keyed on the message text so that repeating the same action restarts it
 * instead of leaving the second confirmation without a deadline.
 */
export function Toast({
  message,
  tone = "ok",
}: {
  message: string | null;
  tone?: "ok" | "bad";
}) {
  const [shown, setShown] = useState<string | null>(message);

  useEffect(() => {
    setShown(message);
    if (!message) return;
    const id = window.setTimeout(() => setShown(null), TOAST_MS);
    return () => window.clearTimeout(id);
  }, [message]);

  if (!shown) return null;
  return (
    <p
      role="status"
      aria-live="polite"
      className={`fixed inset-x-4 bottom-6 z-50 mx-auto max-w-lg rounded-control border p-3 text-center shadow-lg ${
        tone === "bad" ? "border-bad bg-badbg text-bad" : "border-line bg-pearl text-ink"
      }`}
    >
      {message}
    </p>
  );
}

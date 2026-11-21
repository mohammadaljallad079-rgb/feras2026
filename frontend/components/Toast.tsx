"use client";

/**
 * §2 «الرسالة العابرة (Toast): تأكيد قصير أسفل الشاشة بعد الإجراء» — the
 * confirmation of an action is a short message pinned to the bottom of the
 * screen rather than a block in the page flow. The next action replaces it.
 */
export function Toast({
  message,
  tone = "ok",
}: {
  message: string | null;
  tone?: "ok" | "bad";
}) {
  if (!message) return null;
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

"use client";

import { useEffect, useRef } from "react";

/**
 * §2 «النوافذ المنبثقة (Modal): لكل نموذج أو تأكيد، وفيها زر إلغاء وزر حفظ/إرسال»
 * — every add form is a window over the screen with its own cancel and
 * save/send buttons, never an always-visible block in the page flow (§6.4).
 */
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panel.current?.querySelector<HTMLElement>("input, select, textarea, button")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        ref={panel}
        className={`card my-6 w-full space-y-4 ${wide ? "max-w-3xl" : "max-w-2xl"}`}
      >
        <h2 className="section-title">{title}</h2>
        {children}
      </div>
    </div>
  );
}

/**
 * Sidebar icon system (reference page 32, item 10: «تصميم الشعار ونظام أيقونات
 * للقائمة الجانبية»).
 *
 * A single stroked 24×24 grid so every sidebar entry carries a mark in the same
 * visual weight as the gold brand accent. Each icon is drawn from primitives
 * only — no icon-font dependency — and inherits `currentColor`, so it follows
 * the sidebar foreground and the active-item highlight automatically.
 */

export type NavIconName =
  | "dashboard"
  | "companies"
  | "reports"
  | "accounting"
  | "serviceRequests"
  | "leads"
  | "opportunities"
  | "directives"
  | "hr"
  | "website"
  | "advisor"
  | "assistant"
  | "formBuilder"
  | "users"
  | "audit";

const PATHS: Record<NavIconName, React.ReactNode> = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </>
  ),
  companies: (
    <>
      <path d="M3 21h18" />
      <path d="M5 21V5a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v16" />
      <path d="M14 21V10h4a1 1 0 0 1 1 1v10" />
      <path d="M8 8h3M8 12h3M8 16h3M17 14h1M17 18h1" />
    </>
  ),
  reports: (
    <>
      <path d="M6 2h9l4 4v16H6z" />
      <path d="M15 2v4h4" />
      <path d="M9 12h6M9 16h6M9 8h2" />
    </>
  ),
  accounting: (
    <>
      <rect x="4" y="3" width="16" height="18" rx="1" />
      <path d="M8 7h8M8 11h8M8 15h4" />
      <path d="M15 18.5a2.5 2.5 0 1 1 0-5" />
    </>
  ),
  serviceRequests: (
    <>
      <path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z" />
      <path d="M8 9h8M8 13h5" />
    </>
  ),
  leads: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M5 21a7 7 0 0 1 14 0" />
      <path d="M19 4v4M17 6h4" />
    </>
  ),
  opportunities: (
    <>
      <path d="M3 17l5-5 4 4 8-8" />
      <path d="M15 8h5v5" />
      <path d="M3 21h18" />
    </>
  ),
  directives: (
    <>
      <path d="M4 4h16v13l-4 4H4z" />
      <path d="M9 9h7M9 13h5" />
    </>
  ),
  hr: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
      <path d="M17 8.5h4M17 12h4M17 15.5h4" />
    </>
  ),
  website: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z" />
    </>
  ),
  advisor: (
    <>
      <path d="M12 3l2.6 5.5 6 .9-4.3 4.2 1 5.9L12 16.7 6.7 19.5l1-5.9L3.4 9.4l6-.9z" />
    </>
  ),
  assistant: (
    <>
      <path d="M12 3v3M12 18v3M4.2 7.2l2.1 2.1M17.7 14.7l2.1 2.1M3 12h3M18 12h3M4.2 16.8l2.1-2.1M17.7 9.3l2.1-2.1" />
      <circle cx="12" cy="12" r="4" />
    </>
  ),
  formBuilder: (
    <>
      <rect x="3" y="4" width="18" height="5" rx="1" />
      <rect x="3" y="15" width="10" height="5" rx="1" />
      <path d="M18 14v6M15 17h6" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
      <circle cx="18" cy="9" r="2.5" />
      <path d="M15 20a5 5 0 0 1 6.5-4.3" />
    </>
  ),
  audit: (
    <>
      <path d="M9 3h6a1 1 0 0 1 1 1v1H8V4a1 1 0 0 1 1-1z" />
      <path d="M8 5H6a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2" />
      <path d="M9 11l2 2 4-4" />
      <path d="M9 17h6" />
    </>
  ),
};

export function NavIcon({ name, className }: { name: NavIconName; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className ?? "shrink-0"}
    >
      {PATHS[name]}
    </svg>
  );
}

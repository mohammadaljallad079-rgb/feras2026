"use client";

import { ResourceTable, Column } from "@/components/ResourceTable";
import { useAuth } from "@/lib/auth";

type AuditEvent = {
  id: number;
  created_at: string;
  actor_id: number | null;
  actor_label: string | null;
  role_label: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  company_id: number | null;
};

export default function AuditPage() {
  const { locale } = useAuth();
  const columns: Column<AuditEvent>[] = [
    { key: "created_at", headerAr: "التاريخ", headerEn: "Date", numeric: true, render: (r) => <span dir="ltr">{r.created_at.slice(0, 19).replace("T", " ")}</span> },
    { key: "actor", headerAr: "المستخدم", headerEn: "User", render: (r) => <span dir="ltr">{r.actor_label ?? r.actor_id ?? "—"}</span> },
    { key: "role", headerAr: "الدور", headerEn: "Role", render: (r) => r.role_label ?? "—" },
    { key: "action", headerAr: "الإجراء", headerEn: "Action", render: (r) => <span dir="ltr">{r.action}</span> },
  ];

  return (
    <>
      {/* PDF page 21: read-only log; passwords and keys are never recorded. */}
      <p className="muted mb-4">
        {locale === "ar"
          ? "سجل النشاط — للعرض فقط. لا يسجل كلمات المرور أو المفاتيح."
          : "Activity log — read only. Passwords and keys are never recorded."}
      </p>
      <ResourceTable<AuditEvent>
        titleAr="سجل النشاط"
        titleEn="Activity log"
        endpoint="/api/v1/audit"
        columns={columns}
        permission="audit:view"
      />
    </>
  );
}

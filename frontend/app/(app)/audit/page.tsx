"use client";

import { ResourceTable, Column } from "@/components/ResourceTable";

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
  const columns: Column<AuditEvent>[] = [
    { key: "created_at", headerAr: "الوقت", headerEn: "Timestamp", numeric: true, render: (r) => <span dir="ltr">{r.created_at.slice(0, 19).replace("T", " ")}</span> },
    { key: "actor", headerAr: "المستخدم", headerEn: "User", render: (r) => <span dir="ltr">{r.actor_label ?? r.actor_id ?? "—"}</span> },
    { key: "role", headerAr: "الدور", headerEn: "Role", render: (r) => r.role_label ?? "—" },
    { key: "action", headerAr: "الإجراء", headerEn: "Action", render: (r) => <span dir="ltr">{r.action}</span> },
    { key: "target", headerAr: "السجل المستهدف", headerEn: "Target record", render: (r) => <span dir="ltr">{r.target_type ? `${r.target_type}#${r.target_id ?? ""}` : "—"}</span> },
    { key: "company", headerAr: "نطاق الشركة", headerEn: "Company scope", numeric: true, render: (r) => <span dir="ltr">{r.company_id ?? "—"}</span> },
  ];

  return (
    <ResourceTable<AuditEvent>
      titleAr="سجل النشاط"
      titleEn="Activity log"
      endpoint="/api/v1/audit"
      columns={columns}
      permission="audit:view"
    />
  );
}

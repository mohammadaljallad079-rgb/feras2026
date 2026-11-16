"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Person = { id: number; full_name_ar: string; full_name_en: string };

type Directive = {
  id: number;
  title: string;
  body: string;
  created_by_id: number;
  recipient_id: number;
  company_id: number | null;
  follow_up_on: string | null;
  status: string;
  sent_at: string | null;
  received_at: string | null;
  completed_at: string | null;
  escalation_note: string | null;
  created_at: string;
};

export default function DirectivesPage() {
  const { locale, can, me } = useAuth();
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<Directive[]>([]);
  const [overdue, setOverdue] = useState<Directive[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [form, setForm] = useState({ title: "", body: "", recipient_id: "", follow_up_on: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Directive[]>("/api/v1/directives"));
      setOverdue(await api.get<Directive[]>("/api/v1/directives/overdue").catch(() => []));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Person[]>("/api/v1/users").then(setPeople).catch(() => undefined);
  }, [load]);

  // The AI assistant's source record links here as ?open=<id>; scroll that
  // directive into view so the link lands on the record it cites.
  const deepLink = searchParams.get("open");
  useEffect(() => {
    if (!deepLink || rows.length === 0) return;
    document.getElementById(`directive-${deepLink}`)?.scrollIntoView({ block: "start" });
  }, [deepLink, rows.length]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.post("/api/v1/directives", {
        ...form,
        recipient_id: Number(form.recipient_id),
        follow_up_on: form.follow_up_on || null,
      });
      setForm({ title: "", body: "", recipient_id: "", follow_up_on: "" });
      setMessage(locale === "ar" ? "تم إنشاء التوجيه." : "Directive created.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر إنشاء التوجيه." : "Could not create the directive.");
    }
  }

  async function act(id: number, verb: string) {
    setMessage(null);
    try {
      await api.post(`/api/v1/directives/${id}/${verb}`);
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(
        err.status === 403
          ? locale === "ar"
            ? "هذا الإجراء متاح للمستلم فقط."
            : "This action is available to the recipient only."
          : locale === "ar"
            ? "فشل الإجراء."
            : "The action failed.",
      );
    }
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{locale === "ar" ? "التوجيهات التنفيذية" : "Executive directives"}</h1>
        {overdue.length > 0 && (
          <span className="chip-bad">
            {locale === "ar" ? `متأخر: ${overdue.length}` : `Overdue: ${overdue.length}`}
          </span>
        )}
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      {can("directive:create") && (
        <form onSubmit={create} className="card mb-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="dir-title">{locale === "ar" ? "عنوان التوجيه" : "Directive title"}</label>
            <input id="dir-title" className="input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="dir-recipient">{locale === "ar" ? "المستلم" : "Recipient"}</label>
            <select id="dir-recipient" className="input" required value={form.recipient_id} onChange={(e) => setForm({ ...form, recipient_id: e.target.value })}>
              <option value="">—</option>
              {people.map((u) => (
                <option key={u.id} value={u.id}>{locale === "ar" ? u.full_name_ar : u.full_name_en}</option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="dir-body">{locale === "ar" ? "النص" : "Text"}</label>
            <textarea id="dir-body" className="input min-h-20" required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="dir-follow">{locale === "ar" ? "تاريخ المتابعة" : "Follow-up date"}</label>
            <input id="dir-follow" type="date" className="input" dir="ltr" value={form.follow_up_on} onChange={(e) => setForm({ ...form, follow_up_on: e.target.value })} />
          </div>
          <div className="flex items-end">
            <button type="submit" className="btn-primary">{locale === "ar" ? "إنشاء" : "Create"}</button>
          </div>
        </form>
      )}

      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[720px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "العنوان" : "Title"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "المستلم" : "Recipient"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "تاريخ المتابعة" : "Follow-up"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const isOverdue = overdue.some((o) => o.id === r.id);
                const isRecipient = me?.id === r.recipient_id;
                return (
                  <tr key={r.id} id={`directive-${r.id}`} className="border-b border-line last:border-0">
                    <td className="p-3">
                      {r.title}
                      {isOverdue && <span className="chip-bad ms-2">{locale === "ar" ? "متأخر" : "Overdue"}</span>}
                    </td>
                    <td className="p-3">
                      {(() => {
                        const u = people.find((x) => x.id === r.recipient_id);
                        return u ? (locale === "ar" ? u.full_name_ar : u.full_name_en) : `#${r.recipient_id}`;
                      })()}
                    </td>
                    <td className="p-3" dir="ltr">{r.follow_up_on ?? "—"}</td>
                    <td className="p-3"><StatusChip value={r.status} /></td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        {r.status === "draft" && can("directive:create") && (
                          <button type="button" className="btn-primary" onClick={() => void act(r.id, "send")}>
                            {locale === "ar" ? "إرسال" : "Send"}
                          </button>
                        )}
                        {r.status === "sent" && isRecipient && (
                          <button type="button" className="btn-gold" onClick={() => void act(r.id, "receive")}>
                            {locale === "ar" ? "إقرار الاستلام" : "Acknowledge receipt"}
                          </button>
                        )}
                        {r.status === "received" && isRecipient && (
                          <button type="button" className="btn-primary" onClick={() => void act(r.id, "complete")}>
                            {locale === "ar" ? "إنجاز" : "Complete"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </DataStates>
    </section>
  );
}

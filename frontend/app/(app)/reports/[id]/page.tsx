"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, FormField, MonthlyReport } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

type ReportEvent = { from_status: string | null; to_status: string; reason: string | null; created_at: string };

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const { locale, can } = useAuth();
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [fields, setFields] = useState<FormField[]>([]);
  const [history, setHistory] = useState<ReportEvent[]>([]);
  const [values, setValues] = useState<Record<number, string>>({});
  const [commentary, setCommentary] = useState("");
  const [reason, setReason] = useState("");
  const [statementName, setStatementName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get<MonthlyReport>(`/api/v1/reports/${params.id}`);
      setReport(r);
      setCommentary(r.commentary ?? "");
      setValues(
        Object.fromEntries(
          r.values.map((v) => [v.field_id, v.value_number ?? v.value_text ?? ""]),
        ),
      );
      const h = await api.get<ReportEvent[]>(`/api/v1/reports/${params.id}/history`);
      setHistory(h);
      const f = await api.get<FormField[]>("/api/v1/form-fields").catch(() => []);
      setFields(f);
    } catch (e) {
      const err = e as { status: number };
      setError(
        err.status === 404
          ? locale === "ar"
            ? "التقرير غير موجود أو غير مصرّح بالوصول إليه."
            : "The report does not exist or you are not permitted to view it."
          : locale === "ar"
            ? "تعذّر تحميل البيانات."
            : "Could not load data.",
      );
    } finally {
      setLoading(false);
    }
  }, [params.id, locale]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(fn: () => Promise<unknown>, okAr: string, okEn: string) {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
      setMessage(locale === "ar" ? okAr : okEn);
      await load();
    } catch (e) {
      const err = e as { status: number; detail: unknown };
      setMessage(
        err.status === 409
          ? locale === "ar"
            ? "التقرير مقفل أو في حالة لا تسمح بهذا الإجراء."
            : "The report is locked or in a state that does not allow this action."
          : err.status === 422
            ? locale === "ar"
              ? "تحقّق من الحقول المطلوبة والمرفقات."
              : "Check the required fields and attachments."
            : locale === "ar"
              ? "فشل الإجراء."
              : "The action failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  const locked = report ? ["approved", "forwarded"].includes(report.status) : false;
  const editable = report ? ["draft", "returned"].includes(report.status) : false;

  async function uploadStatement(file: File) {
    setUploading(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      if (report) form.append("company_id", String(report.company_id));
      const stored = await api.upload<{ id: number; original_name: string }>("/api/v1/files", form);
      await api.put(`/api/v1/reports/${params.id}/values`, { bank_statement_file_id: stored.id, values: [] });
      setStatementName(stored.original_name);
      setMessage(locale === "ar" ? "تم رفع كشف الحساب." : "Bank statement uploaded.");
      await load();
    } catch {
      setMessage(locale === "ar" ? "تعذّر رفع الملف." : "The upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function saveValues() {
    await run(
      () =>
        api.put(`/api/v1/reports/${params.id}/values`, {
          commentary,
          values: Object.entries(values)
            .filter(([, v]) => v !== "")
            .map(([field_id, v]) => {
              const field = fields.find((f) => f.id === Number(field_id));
              const numeric = field?.field_type === "amount" || field?.field_type === "number";
              return { field_id: Number(field_id), value_number: numeric ? v : null, value_text: numeric ? null : v };
            }),
        }),
      "تم الحفظ.",
      "Saved.",
    );
  }

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">
          {locale === "ar" ? "التقرير الشهري" : "Monthly report"} #{params.id}
        </h1>
        {report && <StatusChip value={report.status} />}
      </header>

      {message && (
        <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">
          {message}
        </p>
      )}
      {locked && (
        <p className="mb-4 rounded-control border border-warn bg-warnbg p-3 text-warn">
          {locale === "ar" ? "التقرير معتمد ومقفل." : "The report is approved and locked."}
        </p>
      )}
      <p className="muted mb-4">
        {locale === "ar"
          ? "تُعرض المبالغ بعملة الشركة ولا تُجمع عملات مختلفة في إجمالي واحد."
          : "Amounts are shown in the company currency; different currencies are never summed into one total."}
      </p>

      <DataStates loading={loading} error={error} empty={!report}>
        {report && (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="card space-y-4 lg:col-span-2">
              <h2 className="section-title">{locale === "ar" ? "قيم التقرير" : "Report values"}</h2>
              {fields
                .filter((f) => f.is_active)
                .sort((a, b) => Number(Boolean(a.parent_id)) - Number(Boolean(b.parent_id)) || a.display_order - b.display_order)
                .map((f) => {
                  const parent = f.parent_id ? fields.find((p) => p.id === f.parent_id) : undefined;
                  return (
                  <div key={f.id} className={parent ? "ps-6" : undefined}>
                    <label className="label" htmlFor={`field-${f.id}`}>
                      {parent && (
                        <span className="me-2 text-gold" aria-label={locale === "ar" ? "حقل فرعي" : "Subfield"}>↳</span>
                      )}
                      {locale === "ar" ? f.name_ar : f.name_en}
                      {f.is_required && <span aria-hidden="true"> *</span>}
                    </label>
                    <input
                      id={`field-${f.id}`}
                      className="input"
                      dir={f.field_type === "amount" || f.field_type === "number" ? "ltr" : undefined}
                      disabled={!editable}
                      value={values[f.id] ?? ""}
                      onChange={(e) => setValues((v) => ({ ...v, [f.id]: e.target.value }))}
                    />
                  </div>
                  );
                })}
              <div>
                <label className="label" htmlFor="commentary">
                  {locale === "ar" ? "التعليق الإداري" : "Administrative commentary"}
                </label>
                <textarea
                  id="commentary"
                  className="input min-h-24"
                  disabled={!editable}
                  value={commentary}
                  onChange={(e) => setCommentary(e.target.value)}
                />
              </div>

              {/* PDF p.23: the bank statement is mandatory before submission. */}
              <div className="border-t border-line pt-4">
                <label className="label" htmlFor="bank-statement">
                  {locale === "ar" ? "كشف الحساب البنكي للشهر (إلزامي)" : "Bank statement for the month (required)"}
                  <span aria-hidden="true"> *</span>
                </label>
                {report.bank_statement_file_id ? (
                  <p className="flex flex-wrap items-center gap-2">
                    <span className="chip-ok">{locale === "ar" ? "مرفق" : "Attached"}</span>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => void api.download(`/api/v1/files/${report.bank_statement_file_id}/download`, "bank-statement")}
                    >
                      {statementName ?? (locale === "ar" ? "تنزيل الكشف" : "Download statement")}
                    </button>
                  </p>
                ) : (
                  <p className="muted">{locale === "ar" ? "كشف الحساب غير مرفق" : "Bank statement not attached"}</p>
                )}
                {editable && can("report:submit") && (
                  <input
                    id="bank-statement"
                    type="file"
                    className="input mt-2"
                    accept=".pdf,.png,.jpg,.jpeg,.xlsx,.csv"
                    disabled={uploading}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) void uploadStatement(file);
                    }}
                  />
                )}
              </div>

              <div className="flex flex-wrap gap-2 border-t border-line pt-4">
                {editable && can("report:submit") && (
                  <>
                    <button type="button" className="btn-ghost" onClick={() => void saveValues()} disabled={busy}>
                      {locale === "ar" ? "حفظ" : "Save"}
                    </button>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={busy}
                      onClick={() => void run(() => api.post(`/api/v1/reports/${params.id}/submit`), "تم الإرسال إلى المحاسبة.", "Submitted to accounting.")}
                    >
                      {locale === "ar" ? "إرسال إلى المحاسبة" : "Submit to accounting"}
                    </button>
                  </>
                )}
                {report.status === "submitted" && can("report:review") && (
                  <>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={busy}
                      onClick={() => void run(() => api.post(`/api/v1/reports/${params.id}/approve`), "تم الاعتماد.", "Approved.")}
                    >
                      {locale === "ar" ? "اعتماد" : "Approve"}
                    </button>
                    <input
                      className="input w-auto"
                      placeholder={locale === "ar" ? "سبب الإعادة" : "Return reason"}
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-ghost"
                      disabled={busy || reason.trim().length < 3}
                      onClick={() => void run(() => api.post(`/api/v1/reports/${params.id}/return`, { reason }), "تمت الإعادة.", "Returned.")}
                    >
                      {locale === "ar" ? "إعادة" : "Return"}
                    </button>
                  </>
                )}
                {report.status === "approved" && can("report:forward") && (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy}
                    onClick={() => void run(() => api.post(`/api/v1/reports/${params.id}/forward`), "تم الإرسال للإدارة.", "Sent to management.")}
                  >
                    {locale === "ar" ? "إرسال للإدارة" : "Send to management"}
                  </button>
                )}
                {can("report:export") && (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => void api.download(`/api/v1/reports/${params.id}/export`, `report-${params.id}.xlsx`)}
                  >
                    {locale === "ar" ? "تصدير Excel" : "Export Excel"}
                  </button>
                )}
              </div>
            </div>

            <div className="card">
              <h2 className="section-title mb-3">{locale === "ar" ? "سجل التقرير" : "Report history"}</h2>
              {history.length === 0 ? (
                <p className="muted">{locale === "ar" ? "لا توجد بيانات لعرضها." : "No data to display."}</p>
              ) : (
                <ol className="space-y-3">
                  {history.map((h, i) => (
                    <li key={i} className="border-b border-line pb-2 last:border-0">
                      <div className="flex items-center gap-2">
                        <StatusChip value={h.to_status} />
                        <span className="muted" dir="ltr">
                          {h.created_at.slice(0, 16).replace("T", " ")}
                        </span>
                      </div>
                      {h.reason && <p className="muted mt-1">{h.reason}</p>}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}
      </DataStates>
    </section>
  );
}

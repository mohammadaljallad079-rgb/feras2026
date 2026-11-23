"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, loadErrorState, Company, FormField, MonthlyReport } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { ReportStatusChip } from "@/components/StatusChip";
import { Toast } from "@/components/Toast";

type ReportEvent = { from_status: string | null; to_status: string; reason: string | null; created_at: string };

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { locale, can } = useAuth();
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [fields, setFields] = useState<FormField[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
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
  // §7.3: the return-for-correction modal.
  const [returning, setReturning] = useState(false);

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
      const cs = await api.get<Company[]>("/api/v1/companies?include_holding=true&include_closed=true").catch(() => []);
      setCompanies(cs);
    } catch (e) {
      setError(
        loadErrorState(e, locale, {
          ar: "التقرير غير موجود أو غير مصرّح بالوصول إليه.",
          en: "The report does not exist or you are not permitted to view it.",
        }),
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

  // §7.4: a field appears in a company's report only within its scope — a
  // sector field only for that sector, a company field only for that company,
  // an unscoped field for every company. Mirrors the backend's `_applies`, which
  // validates the same rule on submit. Until the company is known the list is
  // left unfiltered rather than blanked.
  const reportCompany = report ? companies.find((c) => c.id === report.company_id) : undefined;
  const scopedFields = reportCompany
    ? fields.filter(
        (f) =>
          (f.company_id === null || f.company_id === reportCompany.id) &&
          (!f.sector_scope || f.sector_scope === reportCompany.sector),
      )
    : fields;

  // §7.3: the «التقرير الإداري» table — one row per field that carries a value,
  // shown as label and value in the company's own currency. Rows follow the
  // report's saved values, so a field removed from the builder still appears.
  const managementRows = (report?.values ?? []).flatMap((v) => {
    const field = fields.find((f) => f.id === v.field_id);
    const raw = v.value_number ?? v.value_text;
    if (raw === null || raw === undefined || raw === "") return [];
    const numeric = v.value_number !== null && v.value_number !== undefined;
    return [
      {
        id: v.field_id,
        name_ar: v.field_name_ar ?? field?.name_ar ?? `#${v.field_id}`,
        name_en: v.field_name_en ?? field?.name_en ?? `#${v.field_id}`,
        numeric,
        display: numeric
          ? `${Number(v.value_number).toLocaleString("en-US", { maximumFractionDigits: 2 })} ${report?.currency ?? ""}`.trim()
          : String(v.value_text),
      },
    ];
  });

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
        <div className="flex flex-wrap items-center gap-2">
          {report && <ReportStatusChip value={report.status} />}
          {/* Table 3 / Table 9: «رجوع» returns to the reports list for every role. */}
          <button type="button" className="btn-ghost" onClick={() => router.push("/platform/reports")}>
            {locale === "ar" ? "رجوع" : "Back"}
          </button>
        </div>
      </header>

      {locked && (
        <p className="mb-4 rounded-control border border-warn bg-warnbg p-3 text-warn">
          {locale === "ar" ? "التقرير معتمد ومقفل." : "The report is approved and locked."}
        </p>
      )}
      {/* Table 8: a report returned for edit shows the accountant's reason in an
          alert at the top of the page, and the manager edits and resubmits. */}
      {report?.status === "returned" && report.returned_reason && (
        <p role="alert" className="mb-4 rounded-control border border-warn bg-warnbg p-3 text-warn">
          <span className="font-semibold">{locale === "ar" ? "أُعيد للتعديل: " : "Returned for edit: "}</span>
          {report.returned_reason}
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
              {scopedFields
                .filter((f) => f.is_active)
                .sort((a, b) => Number(Boolean(a.parent_id)) - Number(Boolean(b.parent_id)) || a.display_order - b.display_order)
                .map((f) => {
                  const parent = f.parent_id ? scopedFields.find((p) => p.id === f.parent_id) : undefined;
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
                      {locale === "ar" ? "حفظ المسودة" : "Save draft"}
                    </button>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={busy}
                      onClick={() => void run(() => api.post(`/api/v1/reports/${params.id}/submit`), "تم الإرسال إلى المحاسبة.", "Submitted to accounting.")}
                    >
                      {locale === "ar" ? "إرسال للمحاسبة" : "Submit to accounting"}
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
                    <button
                      type="button"
                      className="btn-bad"
                      disabled={busy}
                      onClick={() => setReturning(true)}
                    >
                      {locale === "ar" ? "إعادة للتصحيح" : "Return for correction"}
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
                    {locale === "ar" ? "تنزيل Excel" : "Download Excel"}
                  </button>
                )}
              </div>
            </div>

            {/* §7.3: the report page carries a «التقرير الإداري» section — a
                field/value table of the submitted numbers in the company's local
                currency — plus a «سجل التغييرات» (change log). */}
            <div className="space-y-4">
            <div className="card">
              <h2 className="section-title mb-3">{locale === "ar" ? "التقرير الإداري" : "Management report"}</h2>
              {managementRows.length === 0 ? (
                <p className="muted">{locale === "ar" ? "لا توجد بيانات لعرضها." : "No data to display."}</p>
              ) : (
                <div className="table-scroll">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="p-2 text-start">{locale === "ar" ? "الحقل" : "Field"}</th>
                      <th className="p-2 text-start">{locale === "ar" ? "القيمة" : "Value"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {managementRows.map((row) => (
                      <tr key={row.id} className="border-b border-line last:border-0">
                        <td className="p-2">{locale === "ar" ? row.name_ar : row.name_en}</td>
                        <td className="p-2 tabular-nums" dir={row.numeric ? "ltr" : undefined}>
                          {row.display}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
              <p className="muted mt-3">
                {locale === "ar"
                  ? `المبالغ بعملة الشركة (${report?.currency ?? "—"}).`
                  : `Amounts are in the company currency (${report?.currency ?? "—"}).`}
              </p>
            </div>

            <div className="card">
              <h2 className="section-title mb-3">{locale === "ar" ? "سجل التغييرات" : "Change log"}</h2>
              {history.length === 0 ? (
                <p className="muted">{locale === "ar" ? "لا توجد بيانات لعرضها." : "No data to display."}</p>
              ) : (
                <ol className="space-y-3">
                  {history.map((h, i) => (
                    <li key={i} className="border-b border-line pb-2 last:border-0">
                      <div className="flex items-center gap-2">
                        <ReportStatusChip value={h.to_status} />
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
          </div>
        )}
      </DataStates>

      {/* §7.3: «إعادة للتعديل» — the reason is mandatory and must be clear. */}
      {returning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (reason.trim().length < 3) return;
              setReturning(false);
              void run(() => api.post(`/api/v1/reports/${params.id}/return`, { reason }), "تمت الإعادة.", "Returned.");
            }}
            className="card w-full max-w-md space-y-4"
          >
            <h2 className="section-title">{locale === "ar" ? "إعادة للتعديل" : "Return for correction"}</h2>
            <div>
              <label className="label" htmlFor="return-reason">
                {locale === "ar" ? "السبب (إلزامي، واضح) *" : "Reason (mandatory, clear) *"}
              </label>
              <textarea
                id="return-reason"
                className="input min-h-24"
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-ghost" onClick={() => setReturning(false)}>
                {locale === "ar" ? "إلغاء" : "Cancel"}
              </button>
              <button type="submit" className="btn-bad" disabled={reason.trim().length < 3}>
                {locale === "ar" ? "إعادة" : "Return"}
              </button>
            </div>
          </form>
        </div>
      )}
      <Toast message={message} />
    </section>
  );
}

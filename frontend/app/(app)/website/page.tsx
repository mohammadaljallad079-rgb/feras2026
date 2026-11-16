"use client";

import { useCallback, useEffect, useState } from "react";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";
import { api, Company } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Submission = {
  id: number;
  kind: string;
  name: string;
  email: string;
  phone: string | null;
  message: string | null;
  company_id: number | null;
  status: string;
  converted_type: string | null;
  converted_id: number | null;
  created_at: string;
};

export default function WebsitePage() {
  const { locale, can } = useAuth();
  const [rows, setRows] = useState<Submission[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Submission[]>("/api/v1/website/submissions"));
    } catch {
      setError(locale === "ar" ? "تعذّر تحميل البيانات." : "Could not load data.");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void load();
    api.get<Company[]>("/api/v1/companies").then(setCompanies).catch(() => undefined);
  }, [load]);

  async function convert(id: number, target: string) {
    setMessage(null);
    try {
      await api.post(`/api/v1/website/submissions/${id}/convert`, { target });
      setMessage(locale === "ar" ? "تم التحويل إلى سجل داخلي." : "Converted to an internal record.");
      await load();
    } catch (e) {
      const err = e as { status: number };
      setMessage(
        err.status === 409
          ? locale === "ar"
            ? "تم تحويل هذا الطلب مسبقاً."
            : "This submission was already converted."
          : locale === "ar"
            ? "فشل التحويل."
            : "Conversion failed.",
      );
    }
  }

  async function toggleVisibility(companyId: number, next: boolean) {
    setMessage(null);
    try {
      await api.patch(`/api/v1/website/companies/${companyId}/visibility`, { public_visible: next });
      setMessage(locale === "ar" ? "تم تحديث الظهور العام." : "Public visibility updated.");
      setCompanies(await api.get<Company[]>("/api/v1/companies"));
    } catch {
      setMessage(locale === "ar" ? "تعذّر تحديث الظهور." : "Could not update visibility.");
    }
  }

  return (
    <section>
      <header className="mb-6">
        <h1 className="page-title">{locale === "ar" ? "إدارة الموقع" : "Website management"}</h1>
        <p className="muted">
          {locale === "ar"
            ? "نماذج الموقع العام محفوظة في المنصة. تصميم الموقع العام نفسه غير محدد في المرجع، لذا فهو مؤقت."
            : "Public form submissions are stored in the platform. The public site's own design is not specified by the reference, so it is provisional."}
        </p>
      </header>
      {message && <p role="status" className="mb-4 rounded-control border border-line bg-pearl p-3">{message}</p>}

      <h2 className="section-title mb-3">{locale === "ar" ? "صندوق النماذج العامة" : "Public form inbox"}</h2>
      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[760px] border-collapse">
            <thead>
              <tr className="border-b border-line bg-pearl">
                <th className="p-3 text-start">{locale === "ar" ? "النوع" : "Kind"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الاسم" : "Name"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "التواصل" : "Contact"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الرسالة" : "Message"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{locale === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="p-3">{r.kind}</td>
                  <td className="p-3">{r.name}</td>
                  <td className="p-3" dir="ltr">{r.email}</td>
                  <td className="p-3 max-w-xs truncate">{r.message ?? "—"}</td>
                  <td className="p-3"><StatusChip value={r.status} /></td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      {r.status !== "converted" && can("website:manage") && (
                        <>
                          <button type="button" className="btn-primary" onClick={() => void convert(r.id, "lead")}>
                            {locale === "ar" ? "تحويل إلى عميل محتمل" : "Convert to lead"}
                          </button>
                          <button type="button" className="btn-ghost" onClick={() => void convert(r.id, "service_request")}>
                            {locale === "ar" ? "تحويل إلى طلب خدمة" : "Convert to service request"}
                          </button>
                        </>
                      )}
                      {r.status === "converted" && (
                        <span className="muted" dir="ltr">{r.converted_type} #{r.converted_id}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>

      {can("website:manage") && (
        <>
          <h2 className="section-title mb-3 mt-6">{locale === "ar" ? "ظهور الشركات في الموقع" : "Company website visibility"}</h2>
          <div className="card table-scroll p-0">
            <table className="w-full min-w-[520px] border-collapse">
              <thead>
                <tr className="border-b border-line bg-pearl">
                  <th className="p-3 text-start">{locale === "ar" ? "الشركة" : "Company"}</th>
                  <th className="p-3 text-start">{locale === "ar" ? "ظاهر للعامة" : "Publicly visible"}</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.id} className="border-b border-line last:border-0">
                    <td className="p-3">{locale === "ar" ? c.name_ar : c.name_en}</td>
                    <td className="p-3">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={c.public_visible} onChange={(e) => void toggleVisibility(c.id, e.target.checked)} />
                        <span className="muted">{c.public_visible ? (locale === "ar" ? "نعم" : "Yes") : locale === "ar" ? "لا" : "No"}</span>
                      </label>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

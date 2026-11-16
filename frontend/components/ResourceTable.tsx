"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DataStates } from "@/components/DataStates";
import { StatusChip } from "@/components/StatusChip";

export type Column<T> = {
  key: string;
  headerAr: string;
  headerEn: string;
  render: (row: T) => React.ReactNode;
  numeric?: boolean;
};

/**
 * A generic, permission-aware list screen: real API data, loading/empty/error
 * states, a working refresh button and a wide-table container that scrolls
 * inside itself so the page never scrolls horizontally at 400px.
 */
export function ResourceTable<T extends { id: number }>({
  titleAr,
  titleEn,
  endpoint,
  columns,
  actions,
  createHref,
  createLabelAr,
  createLabelEn,
  permission,
  filters,
}: {
  titleAr: string;
  titleEn: string;
  endpoint: string;
  columns: Column<T>[];
  actions?: (row: T, reload: () => void) => React.ReactNode;
  createHref?: string;
  createLabelAr?: string;
  createLabelEn?: string;
  permission?: string;
  filters?: React.ReactNode;
}) {
  const { locale, can } = useAuth();
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<T[]>(endpoint);
      setRows(data);
    } catch (e) {
      const err = e as ApiError;
      setError(
        err.status === 403
          ? locale === "ar"
            ? "لا تملك صلاحية عرض هذه البيانات."
            : "You are not permitted to view this data."
          : locale === "ar"
            ? "تعذّر تحميل البيانات."
            : "Could not load data.",
      );
    } finally {
      setLoading(false);
    }
  }, [endpoint, locale]);

  useEffect(() => {
    void load();
  }, [load]);

  const permitted = !permission || can(permission);

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{locale === "ar" ? titleAr : titleEn}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-ghost" onClick={() => void load()}>
            {locale === "ar" ? "تحديث القائمة" : "Refresh listing"}
          </button>
          {createHref && createLabelAr && permitted && (
            <a className="btn-primary" href={createHref}>
              {locale === "ar" ? createLabelAr : createLabelEn}
            </a>
          )}
        </div>
      </header>
      {filters && <div className="mb-4 flex flex-wrap items-end gap-3">{filters}</div>}
      <DataStates loading={loading} error={error} empty={rows.length === 0}>
        <div className="card table-scroll p-0">
          <table className="w-full min-w-[640px] border-collapse text-base">
            <thead>
              <tr className="border-b border-line bg-pearl text-start">
                {columns.map((c) => (
                  <th key={c.key} className="whitespace-nowrap p-3 text-start section-title">
                    {locale === "ar" ? c.headerAr : c.headerEn}
                  </th>
                ))}
                {actions && <th className="p-3 text-start section-title">{locale === "ar" ? "إجراءات" : "Actions"}</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line last:border-0">
                  {columns.map((c) => (
                    <td key={c.key} className={`p-3 ${c.numeric ? "tabular-nums" : ""}`} dir={c.numeric ? "ltr" : undefined}>
                      {c.render(row)}
                    </td>
                  ))}
                  {actions && (
                    <td className="p-3">
                      <div className="flex flex-wrap items-center gap-2">{actions(row, load)}</div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataStates>
    </section>
  );
}

export { StatusChip };

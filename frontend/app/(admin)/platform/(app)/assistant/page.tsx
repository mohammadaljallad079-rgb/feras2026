"use client";

import { useCallback, useEffect, useState } from "react";
import { api, AiAnswer } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type AiStatus = { provider: string; model: string; configured: boolean; message_ar: string };
type AiSummary = {
  period_label_ar: string;
  period_label_en: string;
  scope_ar: string;
  scope_en: string;
  sections: { key: string; title_ar: string; title_en: string; lines_ar: string[]; lines_en: string[] }[];
  sources: { label_ar: string; label_en: string; kind: string; url: string; status: string; currency: string }[];
};
type AiSettings = {
  provider: string;
  model: string;
  base_url: string;
  has_api_key: boolean;
  api_key_hint: string | null;
  configured: boolean;
  model_classes: string[];
  env_key_locked: boolean;
};
type TestResult = { ok: boolean; provider: string; model: string; message_ar: string; message_en: string };

export default function AssistantPage() {
  const { locale, can } = useAuth();
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [summary, setSummary] = useState<AiSummary | null>(null);
  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [keyDraft, setKeyDraft] = useState("");
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState<AiAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canConfigure = can("ai:configure");

  const load = useCallback(async () => {
    setStatus(await api.get<AiStatus>("/api/v1/ai/status").catch(() => null));
    setSummary(await api.get<AiSummary>("/api/v1/ai/summary").catch(() => null));
    if (canConfigure) {
      setSettings(await api.get<AiSettings>("/api/v1/ai/settings").catch(() => null));
    }
  }, [canConfigure]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setSettingsMessage(null);
    try {
      const payload: Record<string, unknown> = {
        provider: settings.provider,
        model: settings.model,
        base_url: settings.base_url,
      };
      // The key is sent only when the owner typed a new one; it is never read back.
      if (keyDraft) payload.api_key = keyDraft;
      const updated = await api.put<AiSettings>("/api/v1/ai/settings", payload);
      setSettings(updated);
      setKeyDraft("");
      setSettingsMessage(locale === "ar" ? "تم حفظ الإعدادات." : "Settings saved.");
      await load();
    } catch {
      setSettingsMessage(locale === "ar" ? "تعذّر حفظ الإعدادات." : "Could not save the settings.");
    }
  }

  async function testConnection() {
    setSettingsMessage(null);
    setTestResult(await api.post<TestResult>("/api/v1/ai/settings/test", {}).catch(() => null));
  }

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await api.post<AiAnswer>("/api/v1/ai/ask", { prompt }));
    } catch (e) {
      const err = e as { status: number };
      setError(
        err.status === 502
          ? locale === "ar"
            ? "فشل الاتصال بمزوّد الذكاء الاصطناعي. لم يتم اختلاق أي إجابة."
            : "The AI provider call failed. No answer was invented."
          : locale === "ar"
            ? "تعذّر تنفيذ الطلب."
            : "The request could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto max-w-4xl">
      <header className="mb-6">
        <h1 className="page-title">{locale === "ar" ? "المساعد الذكي" : "AI assistant"}</h1>
        <p className="muted">
          {locale === "ar"
            ? "الإجابات مبنية فقط على السجلات المصرّح بها، مع ذكر المصادر ودرجة الثقة."
            : "Answers are grounded only in permitted records, with sources and a confidence level."}
        </p>
      </header>

      {status && (
        <p
          role="status"
          className={`mb-4 rounded-control border p-3 ${status.configured ? "border-ok bg-okbg text-ok" : "border-warn bg-warnbg text-warn"}`}
        >
          {status.configured
            ? locale === "ar"
              ? `المزوّد: ${status.provider} — النموذج: ${status.model}`
              : `Provider: ${status.provider} — Model: ${status.model}`
            : locale === "ar"
              ? status.message_ar
              : "The assistant is not configured: no AI provider key is set on the server."}
        </p>
      )}

      {/* PDF page 17: executive summary with period, scope and source records. */}
      {summary && (
        <article className="card mb-4">
          <h2 className="section-title mb-1">{locale === "ar" ? "ملخص المالك الذكي" : "Owner smart summary"}</h2>
          <p className="muted mb-3">
            {locale === "ar"
              ? `النطاق: ${summary.scope_ar}`
              : `Scope: ${summary.scope_en}`}
          </p>
          <div className="space-y-3">
            {summary.sections.map((s) => (
              <div key={s.key}>
                <h3 className="font-semibold">{locale === "ar" ? s.title_ar : s.title_en}</h3>
                <ul className="mt-1 list-disc ps-5 text-secondary">
                  {(locale === "ar" ? s.lines_ar : s.lines_en).map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          {summary.sources.length > 0 && (
            <>
              <h3 className="section-title mb-2 mt-4">{locale === "ar" ? "السجلات المصدرية" : "Source records"}</h3>
              <ul className="space-y-1">
                {summary.sources.map((s, i) => (
                  <li key={i}>
                    <a className="underline" href={s.url}>{locale === "ar" ? s.label_ar : s.label_en}</a>
                    <span className="chip-neutral ms-2">{s.currency}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </article>
      )}

      <form onSubmit={ask} className="card mb-4">
        <label className="label" htmlFor="ai-prompt">{locale === "ar" ? "اسأل المساعد" : "Ask the assistant"}</label>
        <textarea id="ai-prompt" className="input min-h-24" required value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <button type="submit" className="btn-primary mt-3" disabled={busy}>
          {locale === "ar" ? "إرسال السؤال" : "Send question"}
        </button>
      </form>

      {error && <p role="alert" className="mb-4 rounded-control border border-bad bg-badbg p-3 text-bad">{error}</p>}

      {answer && (
        <article className="card mb-4">
          <p className="whitespace-pre-wrap">{answer.answer}</p>
          <dl className="mt-4 grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="muted">{locale === "ar" ? "درجة الثقة" : "Confidence"}</dt>
              <dd><span className="chip-neutral">{answer.confidence}</span></dd>
            </div>
            <div>
              <dt className="muted">{locale === "ar" ? "المزوّد" : "Provider"}</dt>
              <dd dir="ltr">{answer.provider} / {answer.model}</dd>
            </div>
          </dl>
          <h2 className="section-title mb-2 mt-4">{locale === "ar" ? "المصادر" : "Sources"}</h2>
          {answer.sources.length === 0 ? (
            <p className="muted">{locale === "ar" ? "لا توجد مصادر. لم يتم اختلاق أي دليل." : "No sources. No evidence was invented."}</p>
          ) : (
            <ul className="space-y-1">
              {answer.sources.map((s, i) => (
                <li key={i} className="border-b border-line pb-1 last:border-0">
                  <span className="chip-neutral me-2">{s.kind}</span>
                  {s.url ? (
                    <a className="underline" href={s.url}>{s.label}</a>
                  ) : (
                    // A source the platform cannot open is shown as text, not as
                    // a link that goes nowhere.
                    <span>{s.label}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </article>
      )}

      {/* PDF page 17: owner-only OpenAI settings — hidden key, test, model class. */}
      {canConfigure && settings && (
        <form onSubmit={saveSettings} className="card">
          <h2 className="section-title mb-1">{locale === "ar" ? "إعدادات المزوّد (للمالك)" : "Provider settings (owner)"}</h2>
          <p className="muted mb-3">
            {locale === "ar"
              ? "المفتاح مخفي ولا يُعاد أبداً من الخادم. اتركه فارغاً للإبقاء عليه كما هو."
              : "The key is hidden and is never returned by the server. Leave it empty to keep the current one."}
          </p>
          {settingsMessage && <p role="status" className="mb-3 rounded-control bg-pearl p-2">{settingsMessage}</p>}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="ai-provider">{locale === "ar" ? "المزوّد" : "Provider"}</label>
              <input id="ai-provider" className="input" dir="ltr" value={settings.provider} onChange={(e) => setSettings({ ...settings, provider: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ai-model">{locale === "ar" ? "فئة النموذج" : "Model class"}</label>
              <select id="ai-model" className="input" dir="ltr" value={settings.model} onChange={(e) => setSettings({ ...settings, model: e.target.value })}>
                {settings.model_classes.map((m) => (<option key={m} value={m}>{m}</option>))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="ai-base">{locale === "ar" ? "عنوان الخدمة" : "Base URL"}</label>
              <input id="ai-base" className="input" dir="ltr" value={settings.base_url} onChange={(e) => setSettings({ ...settings, base_url: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ai-key">{locale === "ar" ? "مفتاح API" : "API key"}</label>
              <input
                id="ai-key"
                type="password"
                className="input"
                dir="ltr"
                autoComplete="off"
                placeholder={settings.has_api_key ? (settings.api_key_hint ?? "••••••") : "sk-…"}
                disabled={settings.env_key_locked}
                value={keyDraft}
                onChange={(e) => setKeyDraft(e.target.value)}
              />
              {settings.env_key_locked && (
                <p className="muted mt-1">
                  {locale === "ar" ? "المفتاح مُدار من بيئة الخادم." : "The key is managed by the server environment."}
                </p>
              )}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="submit" className="btn-primary">{locale === "ar" ? "حفظ الإعدادات" : "Save settings"}</button>
            <button type="button" className="btn-ghost" onClick={() => void testConnection()}>
              {locale === "ar" ? "اختبار الاتصال" : "Test connection"}
            </button>
          </div>
          {testResult && (
            <p
              role="status"
              className={`mt-3 rounded-control border p-2 ${testResult.ok ? "border-ok bg-okbg text-ok" : "border-warn bg-warnbg text-warn"}`}
            >
              {locale === "ar" ? testResult.message_ar : testResult.message_en}
            </p>
          )}
        </form>
      )}
    </section>
  );
}

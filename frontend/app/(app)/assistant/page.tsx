"use client";

import { useEffect, useState } from "react";
import { api, AiAnswer } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type AiStatus = { provider: string; model: string; configured: boolean; message_ar: string };

export default function AssistantPage() {
  const { locale } = useAuth();
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState<AiAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<AiStatus>("/api/v1/ai/status").then(setStatus).catch(() => undefined);
  }, []);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await api.post<AiAnswer>("/api/v1/ai/ask", { prompt }));
    } catch (e) {
      const err = e as { status: number; detail: unknown };
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
    <section className="mx-auto max-w-3xl">
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

      <form onSubmit={ask} className="card mb-4">
        <label className="label" htmlFor="ai-prompt">{locale === "ar" ? "اسأل المساعد" : "Ask the assistant"}</label>
        <textarea
          id="ai-prompt"
          className="input min-h-24"
          required
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <button type="submit" className="btn-primary mt-3" disabled={busy}>
          {locale === "ar" ? "إرسال السؤال" : "Send question"}
        </button>
      </form>

      {error && <p role="alert" className="mb-4 rounded-control border border-bad bg-badbg p-3 text-bad">{error}</p>}

      {answer && (
        <article className="card">
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
                  <a className="underline" href={s.url ?? "#"}>{s.label}</a>
                </li>
              ))}
            </ul>
          )}
        </article>
      )}
    </section>
  );
}

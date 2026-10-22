'use client';

import { FormEvent, useEffect, useState } from 'react';
import { PublicLunaClient, type LunaStatus } from '@/src/clients/PublicLunaClient';
import { useCourse } from '@/src/contexts/CourseContext';
import SectionCard from '@/src/components/SectionCard';
import Button from '@/src/components/ui/Button';
import LunaAnswer from '@/src/components/student/LunaAnswer';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    title: 'Lena fragen (KI-Tutorin)',
    question: 'Frage',
    code: 'Dein Code oder Ergebnis',
    waiting: 'Warte auf Lena …',
    ask: 'Lena fragen',
    expired: 'Die Anfrage an Lena ist abgelaufen oder nicht verfügbar. Versuche es erneut.',
    unavailable: 'Lena ist nicht verfügbar.',
    queued: 'In Warteschlange',
    running: 'Lena antwortet …',
    failed: 'Lena konnte nicht antworten. Versuche es erneut.',
  },
  en: {
    title: 'Ask Lena (AI tutor)',
    question: 'Question',
    code: 'Your code or result',
    waiting: 'Waiting for Lena…',
    ask: 'Ask Lena',
    expired: 'Lena request expired or unavailable. Try again.',
    unavailable: 'Lena is unavailable.',
    queued: 'Queued',
    running: 'Lena is answering…',
    failed: 'Lena could not answer. Try again.',
  },
};

const client = new PublicLunaClient();
const jobKey = (assignmentId: string) => `computor:luna:${assignmentId}`;

export default function PublicLunaPanel({
  assignmentId,
  language,
}: {
  assignmentId: string;
  language?: UiLanguage;
}) {
  const uiLanguage = useUiLanguage();
  const t = COPY[language ?? uiLanguage];
  const { course } = useCourse();
  const [available, setAvailable] = useState(false);
  const [question, setQuestion] = useState('');
  const [submittedText, setSubmittedText] = useState('');
  const [jobId, setJobId] = useState<string | null>(() =>
    typeof window === 'undefined' ? null : window.sessionStorage.getItem(jobKey(assignmentId))
  );
  const [result, setResult] = useState<LunaStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!course?.public) return;
    let active = true;
    client.availability()
      .then(({ enabled }) => { if (active) setAvailable(enabled); })
      .catch(() => { if (active) setAvailable(false); });
    return () => { active = false; };
  }, [course?.public]);

  useEffect(() => {
    if (!jobId || result?.state === 'done' || result?.state === 'failed') return;
    let active = true;
    async function refresh() {
      try {
        const current = await client.status(jobId as string);
        if (active) {
          setResult(current);
          if (current.state === 'done' || current.state === 'failed') {
            setBusy(false);
            window.sessionStorage.removeItem(jobKey(assignmentId));
          }
        }
      } catch {
        if (active) {
          setError(t.expired);
          setBusy(false);
          setJobId(null);
          window.sessionStorage.removeItem(jobKey(assignmentId));
        }
      }
    }
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, [assignmentId, jobId, result?.state, t]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    setJobId(null);
    try {
      const accepted = await client.ask(assignmentId, question.trim(), submittedText);
      setJobId(accepted.id);
      window.sessionStorage.setItem(jobKey(assignmentId), accepted.id);
      setResult({ state: 'queued' });
    } catch (cause) {
      setBusy(false);
      setError(cause instanceof Error ? cause.message : t.unavailable);
    }
  }

  if (!course?.public || !available) return null;

  return (
    <SectionCard title={t.title}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-sm font-medium text-body" htmlFor="luna-question">{t.question}</label>
        <textarea
          id="luna-question"
          className="w-full rounded-md border border-rule-strong bg-surface p-2 text-body"
          rows={3}
          maxLength={6000}
          required
          disabled={busy}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <label className="block text-sm font-medium text-body" htmlFor="luna-submission">{t.code}</label>
        <textarea
          id="luna-submission"
          className="w-full rounded-md border border-rule-strong bg-surface p-2 font-mono text-sm text-body"
          rows={6}
          maxLength={16000}
          disabled={busy}
          value={submittedText}
          onChange={(event) => setSubmittedText(event.target.value)}
        />
        <Button type="submit" loading={busy} loadingLabel={t.waiting}>{t.ask}</Button>
      </form>
      {error && <p role="alert" className="mt-3 text-sm text-danger-text">{error}</p>}
      {result?.state === 'queued' && <p className="mt-3 text-sm text-muted">{t.queued}</p>}
      {result?.state === 'running' && <p className="mt-3 text-sm text-muted">{t.running}</p>}
      {result?.state === 'failed' && <p className="mt-3 text-sm text-muted">{t.failed}</p>}
      {result?.state === 'done' && (
        <div className="mt-3">
          <LunaAnswer answer={result.answer} />
        </div>
      )}
    </SectionCard>
  );
}

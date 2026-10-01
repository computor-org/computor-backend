'use client';

import { FormEvent, useEffect, useState } from 'react';
import { PublicLunaClient, type LunaStatus } from '@/src/clients/PublicLunaClient';
import { useCourse } from '@/src/contexts/CourseContext';
import SectionCard from '@/src/components/SectionCard';
import Button from '@/src/components/ui/Button';

const client = new PublicLunaClient();
const jobKey = (assignmentId: string) => `computor:luna:${assignmentId}`;

export default function PublicLunaPanel({ assignmentId }: { assignmentId: string }) {
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
          setError('Luna request expired or unavailable. Try again.');
          setBusy(false);
          setJobId(null);
          window.sessionStorage.removeItem(jobKey(assignmentId));
        }
      }
    }
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, [assignmentId, jobId, result?.state]);

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
      setError(cause instanceof Error ? cause.message : 'Luna is unavailable.');
    }
  }

  if (!course?.public || !available) return null;

  return (
    <SectionCard title="Ask Luna">
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-sm font-medium text-body" htmlFor="luna-question">Question</label>
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
        <label className="block text-sm font-medium text-body" htmlFor="luna-submission">Your code or result</label>
        <textarea
          id="luna-submission"
          className="w-full rounded-md border border-rule-strong bg-surface p-2 font-mono text-sm text-body"
          rows={6}
          maxLength={16000}
          disabled={busy}
          value={submittedText}
          onChange={(event) => setSubmittedText(event.target.value)}
        />
        <Button type="submit" loading={busy} loadingLabel="Waiting for Luna…">Ask Luna</Button>
      </form>
      {error && <p role="alert" className="mt-3 text-sm text-danger-text">{error}</p>}
      {result?.state === 'queued' && <p className="mt-3 text-sm text-muted">Queued</p>}
      {result?.state === 'running' && <p className="mt-3 text-sm text-muted">Luna is answering…</p>}
      {result?.state === 'failed' && <p className="mt-3 text-sm text-muted">Luna could not answer. Try again.</p>}
      {result?.state === 'done' && (
        <p className="mt-3 whitespace-pre-wrap text-sm text-body">{result.answer}</p>
      )}
    </SectionCard>
  );
}

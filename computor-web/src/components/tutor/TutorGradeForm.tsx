'use client';

import { useState } from 'react';
import Button from '@/src/components/ui/Button';
import ErrorBanner from '@/src/components/ErrorBanner';
import Notice from '@/src/components/ui/Notice';
import { inputCls } from '@/src/components/ui/tokens';
import { GRADING_STATUS, type GradingStatusSlug } from '@/src/components/student/gradingStatus';
import type { GradingStatus, TutorGradeCreate } from 'types/generated';

/** Slug order matches the numeric GradingStatus persisted by the backend. */
const STATUS_ORDER: GradingStatusSlug[] = [
  'not_reviewed',
  'corrected',
  'correction_necessary',
  'improvement_possible',
];

/**
 * Turn the form fields into the PATCH body. The grade is entered as a
 * percentage and sent as a 0..1 fraction; an empty field sends no grade.
 * Returns an error string when the input cannot be sent.
 */
export function toGradeBody(
  percent: string,
  status: GradingStatusSlug,
  feedback: string,
  artifactId?: string | null,
): TutorGradeCreate | string {
  const trimmed = percent.trim();
  let grade: number | null = null;
  if (trimmed !== '') {
    const n = Number(trimmed.replace(',', '.'));
    if (!Number.isFinite(n) || n < 0 || n > 100) return 'The grade must be a number from 0 to 100.';
    grade = Math.round(n * 10) / 1000;
  }
  return {
    grade,
    status: STATUS_ORDER.indexOf(status) as GradingStatus,
    feedback: feedback.trim() || null,
    artifact_id: artifactId ?? null,
  };
}

export default function TutorGradeForm({
  artifactId,
  initialPercent,
  onSubmit,
}: {
  /** The submission being graded; the backend falls back to the latest one. */
  artifactId?: string | null;
  initialPercent?: number | null;
  onSubmit: (body: TutorGradeCreate) => Promise<void>;
}) {
  const [percent, setPercent] = useState(
    initialPercent != null ? String(Math.round(initialPercent * 1000) / 10) : '',
  );
  const [status, setStatus] = useState<GradingStatusSlug>('corrected');
  const [feedback, setFeedback] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = toGradeBody(percent, status, feedback, artifactId);
    if (typeof body === 'string') {
      setError(body);
      return;
    }
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await onSubmit(body);
      setSaved(true);
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Saving the grade failed');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3" aria-label="Grade submission">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="grade-percent" className="text-xs font-medium text-muted">Grade (%)</label>
          <input
            id="grade-percent"
            inputMode="decimal"
            className={inputCls}
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
            placeholder="e.g. 85"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="grade-status" className="text-xs font-medium text-muted">Status</label>
          <select
            id="grade-status"
            className={inputCls}
            value={status}
            onChange={(e) => setStatus(e.target.value as GradingStatusSlug)}
          >
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>{GRADING_STATUS[s].label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="grade-feedback" className="text-xs font-medium text-muted">Feedback for the student</label>
        <textarea
          id="grade-feedback"
          rows={4}
          className={inputCls}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
      </div>
      <ErrorBanner>{error}</ErrorBanner>
      {saved && <Notice tone="success">Grade saved.</Notice>}
      <Button type="submit" disabled={saving}>
        {saving ? 'Saving…' : 'Save grade'}
      </Button>
    </form>
  );
}

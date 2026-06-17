'use client';

import { useState } from 'react';
import type { AnalyticsCutoffs } from '@/src/api/analytics';
import { isoToLocalInput, localInputToIso } from './format';

/**
 * Submission and grading cutoffs are independent report parameters, not stored
 * filters: changing them re-reads the same snapshot. Empty means "use the
 * snapshot's recorded cutoffs".
 *
 * Inputs initialise from the applied `value`; the parent remounts this via a
 * `key` derived from the applied cutoffs so Apply/Reset re-seed the drafts
 * without an in-effect state sync.
 */
export default function CutoffControls({
  value,
  onApply,
  disabled,
}: {
  value: AnalyticsCutoffs;
  onApply: (next: AnalyticsCutoffs) => void;
  disabled?: boolean;
}) {
  const [submission, setSubmission] = useState(isoToLocalInput(value.submissionCutoff));
  const [grading, setGrading] = useState(isoToLocalInput(value.gradingCutoff));

  const dirty =
    isoToLocalInput(value.submissionCutoff) !== submission ||
    isoToLocalInput(value.gradingCutoff) !== grading;

  const apply = () => {
    onApply({
      submissionCutoff: localInputToIso(submission),
      gradingCutoff: localInputToIso(grading),
    });
  };

  const clear = () => {
    setSubmission('');
    setGrading('');
    onApply({ submissionCutoff: null, gradingCutoff: null });
  };

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
      <Field
        id="submission-cutoff"
        label="Submission cutoff"
        value={submission}
        onChange={setSubmission}
        disabled={disabled}
      />
      <Field
        id="grading-cutoff"
        label="Grading cutoff"
        value={grading}
        onChange={setGrading}
        disabled={disabled}
      />
      <button
        type="button"
        onClick={apply}
        disabled={disabled || !dirty}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Apply cutoffs
      </button>
      {(submission || grading) && (
        <button
          type="button"
          onClick={clear}
          disabled={disabled}
          className="rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-50"
        >
          Reset
        </button>
      )}
    </div>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-gray-600">
        {label}
      </label>
      <input
        id={id}
        type="datetime-local"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
      />
    </div>
  );
}

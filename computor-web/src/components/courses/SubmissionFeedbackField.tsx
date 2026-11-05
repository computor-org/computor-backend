'use client';

import { useUiLanguage } from '@/src/hooks/useUiLanguage';

export type SubmissionFeedback = 'tests' | 'tests_and_lena' | 'human';

const MODES: SubmissionFeedback[] = ['tests', 'tests_and_lena', 'human'];

const COPY = {
  de: {
    tests: {
      label: 'Nur Tests',
      detail: 'Das Ergebnis der offiziellen Tests ist die Bewertung und erscheint sofort. Keine Abgabe wartet auf eine Prüfung.',
    },
    tests_and_lena: {
      label: 'Tests und Lena',
      detail: 'Wie „Nur Tests“; zusätzlich schreibt Lena eine kurze, als KI gekennzeichnete Rückmeldung. Die Bewertung ändert sie nicht.',
    },
    human: {
      label: 'Tutorinnen und Tutoren',
      detail: 'Tutorinnen und Tutoren bewerten die Abgaben; die Tests sind nur ein Hinweis.',
    },
  },
  en: {
    tests: {
      label: 'Tests only',
      detail: 'The result of the official tests is the grade and is shown at once. No submission waits for a review.',
    },
    tests_and_lena: {
      label: 'Tests and Lena',
      detail: 'As "Tests only", and Lena writes short feedback marked as AI feedback. She does not change the grade.',
    },
    human: {
      label: 'Tutors',
      detail: 'Tutors grade the submissions; the tests are only a hint.',
    },
  },
};

/**
 * Who grades an official submission in this course. Radios rather than a
 * select so each mode's consequence for learners is visible before choosing.
 */
export default function SubmissionFeedbackField({
  value,
  onChange,
  label,
  disabled,
}: {
  value: SubmissionFeedback;
  label: string;
  onChange: (next: SubmissionFeedback) => void;
  disabled?: boolean;
}) {
  const t = COPY[useUiLanguage()];
  return (
    <div role="radiogroup" aria-label={label} className="space-y-2">
      {MODES.map((mode) => (
        <label key={mode} className="flex items-start gap-3 text-sm text-body">
          <input
            type="radio"
            name="submission-feedback"
            value={mode}
            checked={value === mode}
            disabled={disabled}
            onChange={() => onChange(mode)}
            className="mt-0.5 h-4 w-4 border-rule-strong text-accent-text focus:ring-accent-line disabled:opacity-50"
          />
          <span>
            <span className="block font-medium text-fg">{t[mode].label}</span>
            <span className="block text-xs text-muted">{t[mode].detail}</span>
          </span>
        </label>
      ))}
    </div>
  );
}

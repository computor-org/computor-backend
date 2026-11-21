'use client';

import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    label: (name: string) => `${name} als KI-Tutorin in diesem Kurs eintragen`,
    detail: (name: string) =>
      `${name} wird Mitglied des Kurses mit der Rolle Tutor und beantwortet Fragen, in denen sie mit @${name} erwähnt wird. Ohne diesen Eintrag bleibt @${name} in diesem Kurs unbeantwortet.`,
  },
  en: {
    label: (name: string) => `Enrol ${name} as AI tutor in this course`,
    detail: (name: string) =>
      `${name} becomes a course member with the tutor role and answers questions that mention @${name}. Without it, @${name} gets no answer in this course.`,
  },
};

/**
 * Per-course switch that enrols the deployment's AI tutor as `_tutor`
 * (issues#618).
 *
 * The tutor agent only answers in courses it is a member of, and a new course
 * has no such member. A checkbox like `TutorAgentAutoRouteField`: it sits
 * inside a form and takes effect on Save (or on Create) with the rest of it,
 * through `PUT /courses/{id}/tutor-agent`.
 */
export default function TutorAgentEnrolField({
  name,
  value,
  onChange,
  disabled,
}: {
  name: string;
  value: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  const t = COPY[useUiLanguage()];
  return (
    <label className="flex items-start gap-3 text-sm text-body">
      <input
        type="checkbox"
        checked={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-rule-strong text-accent-text focus:ring-accent-line disabled:opacity-50"
      />
      <span>
        <span className="block font-medium text-fg">{t.label(name)}</span>
        <span className="block text-xs text-muted">{t.detail(name)}</span>
      </span>
    </label>
  );
}

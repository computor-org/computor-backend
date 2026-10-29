// The state a learner's assignment row shows as its dot (computor-org/issues#554).
//
// The dot used to carry the content type's colour, so every assignment was
// yellow whether untouched, submitted or graded. It now says where the learner
// stands: a tutor's verdict first, else whether the work is submitted. The
// colours are the ones the VS Code extension uses for the same states
// (computor-vscode src/utils/contentIconSvg.ts), so both clients read alike.

import type { UiLanguage } from '@/src/hooks/useUiLanguage';

export type AssignmentState = 'open' | 'submitted' | 'corrected' | 'improvement_possible' | 'correction_necessary';

export const ASSIGNMENT_STATES: AssignmentState[] = [
  'open', 'submitted', 'corrected', 'improvement_possible', 'correction_necessary',
];

export const ASSIGNMENT_STATE_COLOR: Record<AssignmentState, string> = {
  open: '#cbd5e1',
  submitted: '#c084fc',
  corrected: '#57cc5d',
  improvement_possible: '#fdba4d',
  correction_necessary: '#fc4a4a',
};

const LABEL: Record<UiLanguage, Record<AssignmentState, string>> = {
  de: {
    open: 'Offen',
    submitted: 'Eingereicht',
    corrected: 'Korrigiert',
    improvement_possible: 'Verbesserung möglich',
    correction_necessary: 'Korrektur nötig',
  },
  en: {
    open: 'Open',
    submitted: 'Submitted',
    corrected: 'Corrected',
    improvement_possible: 'Improvement possible',
    correction_necessary: 'Correction necessary',
  },
};

export function assignmentStateLabel(state: AssignmentState, language: UiLanguage): string {
  return LABEL[language][state];
}

export interface StateContent {
  submitted?: boolean | null;
  /** Grading status slug; `not_reviewed` is no verdict. */
  status?: string | null;
}

export function assignmentState(item: StateContent): AssignmentState {
  // The extension also accepts the older `correction_possible` spelling.
  const status = item.status === 'correction_possible' ? 'improvement_possible' : item.status;
  if (status === 'corrected' || status === 'improvement_possible' || status === 'correction_necessary') return status;
  return item.submitted ? 'submitted' : 'open';
}

/** A unit is submitted once every assignment beneath it is, else open. */
export function unitState(progress: { submitted: number; total: number } | undefined): AssignmentState {
  return progress && progress.total > 0 && progress.submitted === progress.total ? 'submitted' : 'open';
}

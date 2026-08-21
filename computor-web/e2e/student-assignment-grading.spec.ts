import { test, expect } from '@playwright/test';
import { currentGrading, isStaleGrading, statusSlug } from '../src/components/student/GradingPanel';
import {
  gradingStatusLabel,
  gradingStatusTone,
  isGradingVerdict,
} from '../src/components/student/gradingStatus';
import { graderName } from '../src/utils/graderName';
import type {
  SubmissionGroupGradingList,
  SubmissionGroupStudentGet,
} from '../src/generated/types/courses';

// Minimal gradings — only the fields the selectors read.
const grading = (over: Partial<SubmissionGroupGradingList>): SubmissionGroupGradingList =>
  ({
    id: 'g',
    submission_group_id: 'sg',
    graded_by_course_member_id: 'cm',
    grading: 1,
    status: 1,
    created_at: '2026-01-01T00:00:00Z',
    ...over,
  }) as SubmissionGroupGradingList;

const group = (
  gradings: SubmissionGroupGradingList[],
  latest?: string | null,
): SubmissionGroupStudentGet =>
  ({ id: 'sg', gradings, latest_submitted_artifact_id: latest ?? null }) as SubmissionGroupStudentGet;

test('the grade shown is the newest one on the latest submitted artifact', () => {
  const g = group(
    [
      // Newest overall, but it grades a superseded attempt.
      grading({ id: 'old-artifact', artifact_id: 'a1', graded_at: '2026-03-01T00:00:00Z', grading: 0.9 }),
      grading({ id: 'current', artifact_id: 'a2', graded_at: '2026-02-01T00:00:00Z', grading: 0.6 }),
      grading({ id: 'superseded', artifact_id: 'a2', graded_at: '2026-01-01T00:00:00Z', grading: 0.3 }),
    ],
    'a2',
  );
  expect(currentGrading(g)?.id).toBe('current');
  expect(isStaleGrading(g, currentGrading(g))).toBe(false);
});

test('a grade left only on an earlier submission is flagged as stale', () => {
  const g = group([grading({ id: 'x', artifact_id: 'a1', graded_at: '2026-01-01T00:00:00Z' })], 'a2');
  expect(currentGrading(g)?.id).toBe('x');
  expect(isStaleGrading(g, currentGrading(g))).toBe(true);
});

test('without an artifact link the newest grading wins, and is never stale', () => {
  // Rows written before artifact_id existed, and groups with nothing submitted.
  const g = group([
    grading({ id: 'newer', graded_at: '2026-02-01T00:00:00Z' }),
    grading({ id: 'older', graded_at: '2026-01-01T00:00:00Z' }),
  ]);
  expect(currentGrading(g)?.id).toBe('newer');
  expect(isStaleGrading(g, currentGrading(g))).toBe(false);
});

test('graded_at wins over created_at when they disagree', () => {
  // A re-grade moves graded_at without touching the row's created_at.
  const g = group([
    grading({ id: 'regraded', created_at: '2026-01-01T00:00:00Z', graded_at: '2026-05-01T00:00:00Z' }),
    grading({ id: 'later-row', created_at: '2026-03-01T00:00:00Z' }),
  ]);
  expect(currentGrading(g)?.id).toBe('regraded');
});

test('no gradings means no current grade', () => {
  expect(currentGrading(group([]))).toBeNull();
  expect(currentGrading(null)).toBeNull();
  expect(currentGrading(undefined)).toBeNull();
});

test('numeric GradingStatus maps onto the slug vocabulary', () => {
  expect(statusSlug(0)).toBe('not_reviewed');
  expect(statusSlug(1)).toBe('corrected');
  expect(statusSlug(2)).toBe('correction_necessary');
  expect(statusSlug(3)).toBe('improvement_possible');
  expect(statusSlug(null)).toBeNull();
  expect(statusSlug(99)).toBeNull();
});

test('status labels and tones read the same everywhere', () => {
  expect(gradingStatusLabel('correction_necessary')).toBe('Correction necessary');
  expect(gradingStatusTone('correction_necessary')).toBe('error');
  expect(gradingStatusTone('corrected')).toBe('success');
  expect(gradingStatusTone('improvement_possible')).toBe('warning');
  expect(gradingStatusTone('not_reviewed')).toBe('muted');
  // Unknown and absent both read as "nothing to say".
  expect(gradingStatusLabel(undefined)).toBe('-');
  expect(gradingStatusLabel('something_else')).toBe('-');
});

test('only a human verdict earns a chip in the list', () => {
  expect(isGradingVerdict('correction_necessary')).toBe(true);
  expect(isGradingVerdict('corrected')).toBe(true);
  expect(isGradingVerdict('improvement_possible')).toBe(true);
  expect(isGradingVerdict('not_reviewed')).toBe(false);
  expect(isGradingVerdict(null)).toBe(false);
});

test('a grader with no name is null, never a raw uuid', () => {
  expect(graderName({ user_id: 'u1', user: { given_name: 'Ada', family_name: 'Lovelace' } })).toBe(
    'Ada Lovelace',
  );
  expect(graderName({ user_id: 'u1', user: { given_name: 'Ada' } })).toBe('Ada');
  expect(graderName({ user_id: 'u1' })).toBeNull();
  expect(graderName(null)).toBeNull();
});

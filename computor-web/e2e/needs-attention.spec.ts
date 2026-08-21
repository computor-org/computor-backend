import { test, expect } from '@playwright/test';
import {
  selectNeedsAttention,
  DEFAULT_REASONS,
  type AttentionReason,
} from '../src/components/dashboard/NeedsAttention';
import type { CourseContentStudentList } from '../src/generated/types/courses';

// Minimal rows — only the fields the selector reads.
const row = (over: Partial<CourseContentStudentList>): CourseContentStudentList =>
  ({
    id: over.path ?? 'x',
    path: 'w1.a',
    course_id: 'c1',
    course_content_kind_id: 'assignment',
    course_content_type_id: 't',
    position: 0,
    result_count: 0,
    submission_count: 0,
    color: '#fff',
    course_content_type: {} as never,
    ...over,
  }) as CourseContentStudentList;

const titles = new Map([['c1', 'Course One'], ['c2', 'Course Two']]);
const paths = (items: { content: CourseContentStudentList }[]) => items.map((i) => i.content.path);

test('only tutor-reviewed correction_necessary by default', () => {
  const items = selectNeedsAttention(
    [
      row({ path: 'a', status: 'correction_necessary' }),
      row({ path: 'b', status: 'improvement_possible' }),
      row({ path: 'c', status: 'corrected' }),
      row({ path: 'd', status: 'not_reviewed' }),
      row({ path: 'e', status: null }),
      // Not submitted / failing tests used to appear here and no longer do.
      row({ path: 'f', submitted: false, status: null }),
      row({ path: 'g', submitted: true, status: 'corrected', result: { result: 0.2 } as never }),
      row({ path: 'h', submitted: true, unreviewed_count: 3, status: 'not_reviewed' }),
    ],
    titles,
  );
  expect(paths(items)).toEqual(['a']);
});

test('improvement_possible is available but opt-in', () => {
  const rows = [
    row({ path: 'imp', status: 'improvement_possible' }),
    row({ path: 'corr', status: 'correction_necessary' }),
  ];
  expect(paths(selectNeedsAttention(rows, titles))).toEqual(['corr']);

  const both: AttentionReason[] = ['correction_necessary', 'improvement_possible'];
  // correction_necessary outranks improvement_possible.
  expect(paths(selectNeedsAttention(rows, titles, both))).toEqual(['corr', 'imp']);
  expect(paths(selectNeedsAttention(rows, titles, ['improvement_possible']))).toEqual(['imp']);
});

test('units are excluded — their status is aggregated from these very rows', () => {
  const items = selectNeedsAttention(
    [
      row({ path: 'w1', course_content_kind_id: 'unit', status: 'correction_necessary' }),
      row({ path: 'w1.a', status: 'correction_necessary' }),
    ],
    titles,
  );
  expect(paths(items)).toEqual(['w1.a']);
});

test('content hidden from the student is never listed', () => {
  const items = selectNeedsAttention(
    [row({ path: 'hidden', status: 'correction_necessary', visible_effective: false })],
    titles,
  );
  expect(items).toEqual([]);
});

test('groups across courses, and resolves each course title', () => {
  const items = selectNeedsAttention(
    [
      row({ path: 'z', course_id: 'c2', status: 'correction_necessary' }),
      row({ path: 'y', course_id: 'c1', status: 'correction_necessary' }),
    ],
    titles,
  );
  expect(items.map((i) => `${i.courseTitle}/${i.content.path}`)).toEqual([
    'Course One/y',
    'Course Two/z',
  ]);
});

test('DEFAULT_REASONS is the narrow set', () => {
  expect(DEFAULT_REASONS).toEqual(['correction_necessary']);
});

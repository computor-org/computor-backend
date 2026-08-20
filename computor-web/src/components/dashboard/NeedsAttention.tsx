'use client';

import Link from 'next/link';
import Badge from '@/src/components/Badge';
import Panel from '@/src/components/ui/Panel';
import type { Tone } from '@/src/components/ui/tones';
import { displayName } from '@/src/utils/displayName';
import type { CourseContentStudentList } from 'types/generated';

/**
 * What a student still has to do, across every course they are in.
 *
 * There is no notion of a due date anywhere in the schema — the columns were
 * dropped in c4e5f6a7b8c9_drop_team_formation_fields — so this deliberately does
 * not claim anything is "due" or "upcoming". It reports the three states that
 * are actually knowable from a course content: never submitted, submitted but
 * not passing, and waiting on a tutor.
 */
export type AttentionReason = 'not-submitted' | 'failing' | 'awaiting-review';

const REASON: Record<AttentionReason, { label: string; tone: Tone; rank: number }> = {
  // Ranked by how much of the student's own action is left: work that is failing
  // outranks work not started, which outranks work already handed to someone else.
  failing: { label: 'Not passing', tone: 'error', rank: 0 },
  'not-submitted': { label: 'Not submitted', tone: 'warning', rank: 1 },
  'awaiting-review': { label: 'Awaiting review', tone: 'info', rank: 2 },
};

export interface AttentionItem {
  content: CourseContentStudentList;
  reason: AttentionReason;
  courseTitle: string;
}

/**
 * Assignments only — a unit is a container, not work — and only the ones a
 * student can still act on. Returns them worst-first.
 */
export function selectNeedsAttention(
  contents: CourseContentStudentList[],
  courseTitles: Map<string, string>,
): AttentionItem[] {
  const items: AttentionItem[] = [];

  for (const content of contents) {
    if (content.course_content_kind_id !== 'assignment') continue;
    // Hidden content is not the student's problem; it should not even be listed.
    if (content.visible_effective === false) continue;

    let reason: AttentionReason | null = null;
    if (!content.submitted) {
      reason = 'not-submitted';
    } else if ((content.unreviewed_count ?? 0) > 0) {
      reason = 'awaiting-review';
    } else if (content.result && (content.result.result ?? 0) < 1) {
      // result.result is a 0..1 fraction of the tests that passed.
      reason = 'failing';
    }
    if (!reason) continue;

    items.push({
      content,
      reason,
      courseTitle: courseTitles.get(content.course_id) ?? 'Course',
    });
  }

  return items.sort(
    (a, b) =>
      REASON[a.reason].rank - REASON[b.reason].rank ||
      a.courseTitle.localeCompare(b.courseTitle) ||
      a.content.path.localeCompare(b.content.path),
  );
}

export default function NeedsAttention({ items, limit = 8 }: { items: AttentionItem[]; limit?: number }) {
  const shown = items.slice(0, limit);

  return (
    <Panel padding="none">
      <div className="divide-y divide-rule-soft">
        {shown.map(({ content, reason, courseTitle }) => (
          <Link
            key={content.id}
            href={`/courses/${content.course_id}/student/assignments/${content.id}`}
            className="flex items-center gap-3 px-4 py-3 hover:bg-canvas transition-colors"
          >
            <span
              className="shrink-0 h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: content.color || '#cbd5e1' }}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-fg truncate">{displayName(content)}</div>
              <div className="text-xs text-muted truncate">{courseTitle}</div>
            </div>
            <Badge tone={REASON[reason].tone} className="shrink-0">
              {REASON[reason].label}
            </Badge>
          </Link>
        ))}
      </div>
      {items.length > shown.length && (
        <p className="px-4 py-2.5 text-xs text-muted border-t border-rule-soft">
          and {items.length - shown.length} more
        </p>
      )}
    </Panel>
  );
}

'use client';

import Link from 'next/link';
import Badge from '@/src/components/Badge';
import Panel from '@/src/components/ui/Panel';
import type { Tone } from '@/src/components/ui/tones';
import { displayName } from '@/src/utils/displayName';
import type { CourseContentStudentList } from 'types/generated';

/**
 * What a tutor has asked a student to act on, across every course.
 *
 * Deliberately narrow. The first version also listed everything not yet
 * submitted and everything not passing its tests, which on a real account is
 * most of the semester — a list that long is not a call to action, it is the
 * course tree again. What belongs here is only work a human has looked at and
 * sent back.
 *
 * `status` is the grading status of the latest grade on the latest *submitted*
 * artifact (view_mappers.course_member_course_content_result_mapper), so both
 * states below can only be reached by a tutor grading. Test results and
 * un-started work are not represented here at all — that is the point.
 */
export type AttentionReason = 'correction_necessary' | 'improvement_possible';

const REASON: Record<AttentionReason, { label: string; tone: Tone; rank: number }> = {
  correction_necessary: { label: 'Correction necessary', tone: 'error', rank: 0 },
  improvement_possible: { label: 'Improvement possible', tone: 'warning', rank: 1 },
};

/**
 * `improvement_possible` is wired up but off by default: it is advisory, not a
 * request, so it would dilute a list whose whole job is "a tutor is waiting on
 * you". To show it, pass `reasons` at the call site or add it here.
 */
export const DEFAULT_REASONS: AttentionReason[] = ['correction_necessary'];

export interface AttentionItem {
  content: CourseContentStudentList;
  reason: AttentionReason;
  courseTitle: string;
}

function isAttentionReason(status: string | null | undefined): status is AttentionReason {
  return status === 'correction_necessary' || status === 'improvement_possible';
}

/**
 * Assignments a tutor has sent back, worst first.
 *
 * Assignments only — a unit's status is aggregated from its descendants
 * (view_base._aggregate_unit_statuses), so including units would list the same
 * piece of work twice, once under its own name and once under its unit's.
 */
export function selectNeedsAttention(
  contents: CourseContentStudentList[],
  courseTitles: Map<string, string>,
  reasons: AttentionReason[] = DEFAULT_REASONS,
): AttentionItem[] {
  const wanted = new Set<AttentionReason>(reasons);
  const items: AttentionItem[] = [];

  for (const content of contents) {
    if (content.course_content_kind_id !== 'assignment') continue;
    // Hidden content is not the student's problem; it should not even be listed.
    if (content.visible_effective === false) continue;

    const status = content.status;
    if (!isAttentionReason(status) || !wanted.has(status)) continue;

    items.push({
      content,
      reason: status,
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
            {content.unread_message_count ? (
              <Badge tone="info" className="shrink-0" title="Unread feedback on this assignment">
                {content.unread_message_count} new
              </Badge>
            ) : null}
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

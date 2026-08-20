'use client';

import type { CourseMemberGradingNode } from 'types/generated';
import { useContentTree, type ContentTreeRow } from '@/src/hooks/useContentTree';
import Panel from '@/src/components/ui/Panel';

interface ContentTreeProps {
  nodes: CourseMemberGradingNode[];
}

function statusColor(status: string | null | undefined): string {
  switch (status) {
    case 'corrected': return 'bg-green-500';
    case 'correction_necessary': return 'bg-red-500';
    case 'improvement_possible': return 'bg-amber-500';
    default: return 'bg-gray-300';
  }
}

function statusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'corrected': return 'Corrected';
    case 'correction_necessary': return 'Correction needed';
    case 'improvement_possible': return 'Improvement possible';
    case 'not_reviewed': return 'Not reviewed';
    default: return '-';
  }
}

/**
 * Grading keeps <tr> rows — it is a table with six numeric columns — so it takes
 * the structure from useContentTree and renders it itself, rather than the
 * <TreeRow> the two assignment trees share. What matters is that all three now
 * agree on nesting order, indent and expand behaviour.
 */
function TreeNodeRow({ row }: { row: ContentTreeRow<CourseMemberGradingNode> }) {
  const { item, depth, label, expanded, hasChildren, toggle } = row;
  // The grading endpoint returns every node; nothing is synthesised here.
  if (!item) return null;
  const node = item;
  const isAssignment = node.submittable === true;
  const indent = depth * 20;
  // Hidden from students, here or by an ancestor (issue #338).
  const hidden = node.visible_effective === false;

  const grade = isAssignment
    ? (node.grading != null ? Math.round(node.grading * 100) : null)
    : (node.average_grading != null ? Math.round(node.average_grading * 100) : null);

  const resultGrade = node.latest_result_grade != null
    ? Math.round(node.latest_result_grade * 100)
    : null;

  return (
    <>
      <tr className="hover:bg-canvas border-b border-rule-soft">
        {/* Title */}
        <td className="py-2 pr-2" style={{ paddingLeft: `${indent + 8}px` }}>
          <div className="flex items-center gap-1.5">
            {hasChildren ? (
              <button
                onClick={toggle}
                aria-expanded={expanded}
                aria-label={expanded ? `Collapse ${label}` : `Expand ${label}`}
                className="w-5 h-5 flex items-center justify-center text-subtle hover:text-muted flex-shrink-0"
              >
                <svg className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ) : (
              <span className="w-5" />
            )}
            {node.course_content_type_color && (
              <span
                className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${hidden ? 'opacity-40' : ''}`}
                style={{ backgroundColor: node.course_content_type_color }}
              />
            )}
            <span
              className={`text-sm truncate ${
                hidden
                  ? 'text-subtle'
                  : isAssignment
                    ? 'text-body'
                    : 'font-medium text-fg'
              }`}
            >
              {label}
            </span>
            {/* Marked, not excluded: the counts on this row deliberately still
                include hidden content, because grading is staff-only and staff
                should see the real denominator (issue #338). */}
            {hidden && (
              <span
                className="shrink-0 px-1.5 py-0.5 text-[11px] font-medium bg-sunken text-muted rounded"
                title="Students cannot currently see this. It is still counted below."
              >
                invisible
              </span>
            )}
          </div>
        </td>

        {/* Progress */}
        <td className="py-2 px-2 w-28">
          {!isAssignment && (
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-1.5 bg-sunken rounded-full overflow-hidden">
                <div
                  className="h-1.5 rounded-full bg-blue-500"
                  style={{ width: `${Math.min(node.progress_percentage, 100)}%` }}
                />
              </div>
              <span className="text-xs text-muted w-8 text-right">{Math.round(node.progress_percentage)}%</span>
            </div>
          )}
        </td>

        {/* Tests */}
        <td className="py-2 px-2 text-xs text-muted text-center w-16">
          {isAssignment && node.max_test_runs != null
            ? `${node.test_runs_count ?? 0}/${node.max_test_runs}`
            : '-'}
        </td>

        {/* Submissions */}
        <td className="py-2 px-2 text-xs text-muted text-center w-16">
          {isAssignment && node.max_submissions != null
            ? `${node.submissions_count ?? 0}/${node.max_submissions}`
            : '-'}
        </td>

        {/* Result */}
        <td className="py-2 px-2 text-xs text-center w-16">
          {resultGrade != null ? (
            <span className="text-body">{resultGrade}%</span>
          ) : '-'}
        </td>

        {/* Grade */}
        <td className="py-2 px-2 text-xs text-center w-16">
          {grade != null ? (
            <span className="font-medium text-fg">{grade}%</span>
          ) : '-'}
        </td>

        {/* Status */}
        <td className="py-2 px-2 w-20">
          {isAssignment && node.status ? (
            <div className="flex items-center gap-1.5" title={statusLabel(node.status)}>
              <span className={`inline-block w-2 h-2 rounded-full ${statusColor(node.status)}`} />
              <span className="text-xs text-muted truncate">{statusLabel(node.status)}</span>
            </div>
          ) : null}
        </td>
      </tr>
    </>
  );
}

export default function ContentTree({ nodes }: ContentTreeProps) {
  // Units open, their contents visible: a lecturer reading one student's report
  // wants the whole picture, not a tree to click open.
  const { rows } = useContentTree(nodes, {});

  if (rows.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted">
        No course content available.
      </div>
    );
  }

  return (
    <Panel padding="none" className="overflow-hidden">
      <div className="px-5 py-3 border-b border-rule">
        <h3 className="text-sm font-semibold text-fg">Course content progress</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-canvas border-b border-rule text-xs font-medium text-muted">
              <th className="text-left py-2 px-2 pl-3">Content</th>
              <th className="text-left py-2 px-2 w-28">Progress</th>
              <th className="text-center py-2 px-2 w-16">Tests</th>
              <th className="text-center py-2 px-2 w-16">Subs</th>
              <th className="text-center py-2 px-2 w-16">Result</th>
              <th className="text-center py-2 px-2 w-16">Grade</th>
              <th className="text-left py-2 px-2 w-20">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <TreeNodeRow key={row.key} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

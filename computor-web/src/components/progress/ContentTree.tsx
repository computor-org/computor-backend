'use client';

import { useState } from 'react';
import type { CourseMemberGradingNode } from 'types/generated';

interface ContentTreeProps {
  nodes: CourseMemberGradingNode[];
}

interface TreeNode extends CourseMemberGradingNode {
  children: TreeNode[];
  depth: number;
}

function buildTree(flatNodes: CourseMemberGradingNode[]): TreeNode[] {
  // Sort by position, then path
  const sorted = [...flatNodes].sort((a, b) => {
    const posA = a.position ?? 0;
    const posB = b.position ?? 0;
    if (posA !== posB) return posA - posB;
    return a.path.localeCompare(b.path);
  });

  const nodeMap = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  for (const node of sorted) {
    const treeNode: TreeNode = { ...node, children: [], depth: node.path.split('.').length - 1 };
    nodeMap.set(node.path, treeNode);

    const parentPath = node.path.includes('.') ? node.path.substring(0, node.path.lastIndexOf('.')) : null;
    if (parentPath && nodeMap.has(parentPath)) {
      nodeMap.get(parentPath)!.children.push(treeNode);
    } else {
      roots.push(treeNode);
    }
  }

  return roots;
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

function TreeNodeRow({ node, defaultExpanded }: { node: TreeNode; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const hasChildren = node.children.length > 0;
  const isAssignment = node.submittable === true;
  const indent = node.depth * 20;

  const grade = isAssignment
    ? (node.grading != null ? Math.round(node.grading * 100) : null)
    : (node.average_grading != null ? Math.round(node.average_grading * 100) : null);

  const resultGrade = node.latest_result_grade != null
    ? Math.round(node.latest_result_grade * 100)
    : null;

  return (
    <>
      <tr className="hover:bg-gray-50 border-b border-gray-100">
        {/* Title */}
        <td className="py-2 pr-2" style={{ paddingLeft: `${indent + 8}px` }}>
          <div className="flex items-center gap-1.5">
            {hasChildren ? (
              <button
                onClick={() => setExpanded(!expanded)}
                className="w-5 h-5 flex items-center justify-center text-gray-400 hover:text-gray-600 flex-shrink-0"
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
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: node.course_content_type_color }}
              />
            )}
            <span className={`text-sm truncate ${isAssignment ? 'text-gray-700' : 'font-medium text-gray-900'}`}>
              {node.title || node.path.split('.').pop()}
            </span>
          </div>
        </td>

        {/* Progress */}
        <td className="py-2 px-2 w-28">
          {!isAssignment && (
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-1.5 rounded-full bg-blue-500"
                  style={{ width: `${Math.min(node.progress_percentage, 100)}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-8 text-right">{Math.round(node.progress_percentage)}%</span>
            </div>
          )}
        </td>

        {/* Tests */}
        <td className="py-2 px-2 text-xs text-gray-500 text-center w-16">
          {isAssignment && node.max_test_runs != null
            ? `${node.test_runs_count ?? 0}/${node.max_test_runs}`
            : '-'}
        </td>

        {/* Submissions */}
        <td className="py-2 px-2 text-xs text-gray-500 text-center w-16">
          {isAssignment && node.max_submissions != null
            ? `${node.submissions_count ?? 0}/${node.max_submissions}`
            : '-'}
        </td>

        {/* Result */}
        <td className="py-2 px-2 text-xs text-center w-16">
          {resultGrade != null ? (
            <span className="text-gray-700">{resultGrade}%</span>
          ) : '-'}
        </td>

        {/* Grade */}
        <td className="py-2 px-2 text-xs text-center w-16">
          {grade != null ? (
            <span className="font-medium text-gray-900">{grade}%</span>
          ) : '-'}
        </td>

        {/* Status */}
        <td className="py-2 px-2 w-20">
          {isAssignment && node.status ? (
            <div className="flex items-center gap-1.5" title={statusLabel(node.status)}>
              <span className={`inline-block w-2 h-2 rounded-full ${statusColor(node.status)}`} />
              <span className="text-xs text-gray-600 truncate">{statusLabel(node.status)}</span>
            </div>
          ) : null}
        </td>
      </tr>

      {expanded && node.children.map(child => (
        <TreeNodeRow key={child.path} node={child} defaultExpanded={child.depth < 2} />
      ))}
    </>
  );
}

export default function ContentTree({ nodes }: ContentTreeProps) {
  const tree = buildTree(nodes);

  if (tree.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        No course content available.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">Course Content Progress</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500">
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
            {tree.map(node => (
              <TreeNodeRow key={node.path} node={node} defaultExpanded={node.depth < 2} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

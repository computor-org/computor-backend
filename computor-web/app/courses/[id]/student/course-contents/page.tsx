'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiFetch } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseContentStudentList } from 'types/generated';

interface TreeNode {
  label: string;
  path: string;
  fullPath: string;
  children: TreeNode[];
  content?: CourseContentStudentList;
  isLeaf: boolean;
}

export default function StudentCourseContentsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const params = useParams();
  const courseId = params.id as string;
  const [courseContents, setCourseContents] = useState<CourseContentStudentList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Don't fetch until authentication is confirmed
    if (authLoading || !isAuthenticated) {
      return;
    }

    async function fetchCourseContents() {
      try {
        const response = await apiFetch(
          `${process.env.NEXT_PUBLIC_API_URL}/students/course-contents?course_id=${courseId}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch course contents');
        }

        const data = await response.json();
        setCourseContents(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchCourseContents();
  }, [courseId, authLoading, isAuthenticated]);

  // Build tree structure from Ltree paths
  const buildTree = (contents: CourseContentStudentList[]): TreeNode[] => {
    const root: TreeNode[] = [];
    const nodeMap = new Map<string, TreeNode>();

    // First pass: Build the tree structure from Ltree paths
    contents.forEach((content) => {
      const pathParts = content.path.split('.');
      let currentPath = '';

      pathParts.forEach((part, index) => {
        const previousPath = currentPath;
        currentPath = currentPath ? `${currentPath}.${part}` : part;
        const isLeaf = index === pathParts.length - 1;

        if (!nodeMap.has(currentPath)) {
          const node: TreeNode = {
            label: part,
            path: part,
            fullPath: currentPath,
            children: [],
            content: isLeaf ? content : undefined,
            isLeaf,
          };

          nodeMap.set(currentPath, node);

          if (previousPath && nodeMap.has(previousPath)) {
            nodeMap.get(previousPath)!.children.push(node);
          } else {
            root.push(node);
          }
        } else if (isLeaf) {
          // Update leaf node with content
          const node = nodeMap.get(currentPath)!;
          node.content = content;
          node.isLeaf = true;
        }
      });
    });

    // Second pass: Sort children by position at each level
    const sortChildren = (nodes: TreeNode[]) => {
      nodes.sort((a, b) => {
        const posA = a.content?.position ?? 0;
        const posB = b.content?.position ?? 0;
        return posA - posB;
      });

      nodes.forEach(node => {
        if (node.children.length > 0) {
          sortChildren(node.children);
        }
      });
    };

    sortChildren(root);

    return root;
  };

  const toggleNode = (path: string) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const renderTree = (nodes: TreeNode[], level: number = 0): React.ReactNode => {
    return nodes.map((node) => {
      const isExpanded = expandedNodes.has(node.fullPath);
      const hasChildren = node.children.length > 0;
      const paddingLeft = level * 24;
      const contentKind = node.content?.course_content_kind_id;
      const isUnit = contentKind === 'unit' || !node.isLeaf;
      const isAssignment = contentKind === 'assignment';

      return (
        <div key={node.fullPath}>
          {/* Node */}
          <div
            className={`flex items-center py-2 px-4 hover:bg-gray-50 cursor-pointer border-b border-gray-100 ${
              node.isLeaf ? '' : 'font-medium'
            }`}
            style={{ paddingLeft: `${paddingLeft + 16}px` }}
            onClick={() => hasChildren && toggleNode(node.fullPath)}
          >
            {/* Expand/Collapse Icon */}
            {hasChildren && (
              <svg
                className={`h-4 w-4 mr-2 text-gray-500 transition-transform ${
                  isExpanded ? 'rotate-90' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}

            {/* Content Kind Icon with Color */}
            {isUnit ? (
              // Circle for units
              <span
                className="w-4 h-4 rounded-full mr-2 flex-shrink-0"
                style={{ backgroundColor: node.content?.color || '#6B7280' }}
              ></span>
            ) : isAssignment ? (
              // Rounded square for assignments
              <span
                className="w-4 h-4 rounded-sm mr-2 flex-shrink-0"
                style={{ backgroundColor: node.content?.color || '#3B82F6' }}
              ></span>
            ) : (
              // Default folder icon for non-leaf nodes without content
              <svg className="h-5 w-5 mr-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            )}

            {/* Label */}
            <span className="flex-1">
              {node.content?.title || node.label}
            </span>

            {/* Content Info - Different for units vs assignments */}
            {node.content && (
              <div className="flex items-center space-x-4 ml-4">
                {isUnit ? (
                  // Unit Info
                  <>
                    <span className="text-sm text-gray-500">
                      {node.children.filter(c => c.content?.course_content_kind_id === 'assignment').length} assignments
                    </span>
                    <Link
                      href={`/courses/${courseId}/student/course-contents/${node.content.id}`}
                      className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View
                    </Link>
                  </>
                ) : isAssignment ? (
                  // Assignment Info
                  <>
                    {/* Submission Status */}
                    {node.content.submitted ? (
                      <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded">
                        Submitted
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-700 rounded">
                        Not Submitted
                      </span>
                    )}

                    {/* Result */}
                    {node.content.result ? (
                      <span className={`text-sm font-medium ${
                        (node.content.result.result || 0) >= 50 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {(node.content.result.result || 0).toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">No results</span>
                    )}

                    {/* Test Runs */}
                    <span className="text-sm text-gray-500">
                      {node.content.result_count} test{node.content.result_count !== 1 ? 's' : ''}
                    </span>

                    {/* Submissions */}
                    <span className="text-sm text-gray-500">
                      {node.content.submission_count} submission{node.content.submission_count !== 1 ? 's' : ''}
                    </span>

                    {/* View Button */}
                    <Link
                      href={`/courses/${courseId}/student/course-contents/${node.content.id}`}
                      className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View
                    </Link>
                  </>
                ) : null}
              </div>
            )}
          </div>

          {/* Children */}
          {hasChildren && isExpanded && (
            <div>{renderTree(node.children, level + 1)}</div>
          )}
        </div>
      );
    });
  };

  const tree = buildTree(courseContents);

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Course Contents</h1>
            <p className="mt-2 text-gray-600">
              {courseContents.filter(c => c.course_content_kind_id === 'unit').length} units · {' '}
              {courseContents.filter(c => c.course_content_kind_id === 'assignment').length} assignments
            </p>
          </div>
        </div>

        {/* Tree View */}
        {tree.length > 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {renderTree(tree)}
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No assignments yet</h3>
            <p className="mt-2 text-sm text-gray-500">
              Assignments will appear here once they are published by your instructor.
            </p>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

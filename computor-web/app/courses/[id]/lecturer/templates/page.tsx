'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { downloadBlob, filenameFromContentDisposition } from '@/src/utils/file';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import type { CourseGet } from 'types/generated';

type Layout = 'flat' | 'hierarchical';

const LAYOUTS: {
  id: Layout;
  title: string;
  desc: string;
  detail: string;
  icon: string;
}[] = [
  {
    id: 'flat',
    title: 'Flat',
    desc: 'The student-template repository exactly as it is in git.',
    detail: 'One top-level directory per assignment, named by its example identifier.',
    icon: 'M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2',
  },
  {
    id: 'hierarchical',
    title: 'Hierarchical',
    desc: 'Directories follow the course structure instead of the example identifiers.',
    detail:
      'Units become parent directories and each assignment’s title names the directory holding its files. Files that belong to no released assignment are left out.',
    icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
  },
];

export default function LecturerTemplatesPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  // Mirrors the backend gate on GET /courses/{id}/template.
  const canDownload = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const { data: course, loading, error } = useResource(async () => {
    const res = await apiFetch(`${API_BASE_URL}/courses/${courseId}`);
    if (!res.ok) throw new Error('Failed to load course');
    return (await res.json()) as CourseGet;
  }, [courseId]);

  const [downloading, setDownloading] = useState<Layout | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function download(layout: Layout) {
    setDownloading(layout);
    setFailure(null);
    try {
      const res = await apiFetch(
        `${API_BASE_URL}/courses/${courseId}/template?hierarchical=${layout === 'hierarchical'}`,
      );
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(
          err?.message ||
            err?.detail ||
            (res.status === 429
              ? 'Too many template downloads. Please wait a minute and try again.'
              : `Download failed (${res.status})`),
        );
      }
      const blob = await res.blob();
      const fallback = `${course?.path ?? 'course'}-template${layout === 'hierarchical' ? '-hierarchical' : ''}.zip`;
      downloadBlob(blob, filenameFromContentDisposition(res.headers.get('Content-Disposition')) ?? fallback);
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setDownloading(null);
    }
  }

  if (!authLoading && isAuthenticated && !canDownload) {
    return (
      <Forbidden
        message="You need lecturer access (or higher) on this course to download its template."
        backLink={`/courses/${courseId}`}
        backText="Back to course"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: course?.title || course?.path || 'Course', href: `/courses/${courseId}` },
            { label: 'Lecturer View', href: `/courses/${courseId}/lecturer` },
            { label: 'Templates' },
          ]}
          title="Templates"
          subtitle={course ? <span className="text-sm text-gray-500 font-mono">{course.path}</span> : undefined}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea className="space-y-6">
            <p className="text-sm text-gray-500">
              Download the released student template as a ZIP. Both layouts contain the same files — only the
              directory structure differs. Newly assigned examples appear here once they are released.
            </p>

            {failure && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">{failure}</div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {LAYOUTS.map((l) => (
                <div key={l.id} className="p-5 bg-white border border-gray-200 rounded-lg flex flex-col gap-3">
                  <div className="flex items-start gap-4">
                    <svg className="h-8 w-8 text-blue-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={l.icon} />
                    </svg>
                    <div>
                      <h3 className="font-semibold text-gray-900">{l.title}</h3>
                      <p className="text-sm text-gray-500 mt-0.5">{l.desc}</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500">{l.detail}</p>
                  <button
                    type="button"
                    onClick={() => download(l.id)}
                    disabled={downloading !== null}
                    className="self-start mt-auto px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {downloading === l.id ? 'Preparing…' : 'Download ZIP'}
                  </button>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { downloadBlob, filenameFromContentDisposition } from '@/src/utils/file';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import type { CourseGet } from 'types/generated';

type Layout = 'flat' | 'hierarchical';

const ICONS: Record<Layout, string> = {
  flat: 'M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2',
  hierarchical: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
};

const LAYOUT_IDS: Layout[] = ['flat', 'hierarchical'];

const COPY = {
  de: {
    templates: 'Vorlagen',
    loadFailed: 'Kurs konnte nicht geladen werden',
    tooMany: 'Zu viele Vorlagen-Downloads. Bitte warte eine Minute und versuche es erneut.',
    downloadFailedStatus: (status: number) => `Download fehlgeschlagen (${status})`,
    downloadFailed: 'Download fehlgeschlagen',
    forbidden: 'Zum Herunterladen der Vorlage brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    backToCourse: 'Zurück zum Kurs',
    intro: 'Lade die freigegebene Studierendenvorlage als ZIP herunter. Beide Strukturen enthalten dieselben Dateien, nur die Verzeichnisstruktur unterscheidet sich. Neu zugewiesene Beispiele erscheinen hier, sobald sie freigegeben sind.',
    preparing: 'Wird vorbereitet …',
    download: 'ZIP herunterladen',
    layouts: {
      flat: {
        title: 'Flach',
        desc: 'Das Studierenden-Vorlagen-Repository genau so, wie es in Git liegt.',
        detail: 'Ein Verzeichnis pro Aufgabe auf oberster Ebene, benannt nach der Beispiel-Kennung.',
      },
      hierarchical: {
        title: 'Hierarchisch',
        desc: 'Die Verzeichnisse folgen der Kursstruktur statt den Beispiel-Kennungen.',
        detail: 'Einheiten werden zu übergeordneten Verzeichnissen, und der Titel jeder Aufgabe benennt das Verzeichnis mit ihren Dateien. Dateien, die zu keiner freigegebenen Aufgabe gehören, werden weggelassen.',
      },
    },
  },
  en: {
    templates: 'Templates',
    loadFailed: 'Failed to load course',
    tooMany: 'Too many template downloads. Please wait a minute and try again.',
    downloadFailedStatus: (status: number) => `Download failed (${status})`,
    downloadFailed: 'Download failed',
    forbidden: 'You need lecturer access (or higher) on this course to download its template.',
    backToCourse: 'Back to course',
    intro: 'Download the released student template as a ZIP. Both layouts contain the same files — only the directory structure differs. Newly assigned examples appear here once they are released.',
    preparing: 'Preparing…',
    download: 'Download ZIP',
    layouts: {
      flat: {
        title: 'Flat',
        desc: 'The student-template repository exactly as it is in git.',
        detail: 'One top-level directory per assignment, named by its example identifier.',
      },
      hierarchical: {
        title: 'Hierarchical',
        desc: 'Directories follow the course structure instead of the example identifiers.',
        detail:
          'Units become parent directories and each assignment’s title names the directory holding its files. Files that belong to no released assignment are left out.',
      },
    },
  },
};

export default function LecturerTemplatesPage() {
  const courseId = useParams().id as string;
  const t = COPY[useUiLanguage()];
  const crumbs = useCourseCrumbs(courseId, t.templates);
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  // Mirrors the backend gate on GET /courses/{id}/template.
  const canDownload = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const { data: course, loading, error } = useResource(async () => {
    const res = await apiFetch(`${API_BASE_URL}/courses/${courseId}`);
    if (!res.ok) throw new Error(t.loadFailed);
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
              ? t.tooMany
              : t.downloadFailedStatus(res.status)),
        );
      }
      const blob = await res.blob();
      const fallback = `${course?.path ?? 'course'}-template${layout === 'hierarchical' ? '-hierarchical' : ''}.zip`;
      downloadBlob(blob, filenameFromContentDisposition(res.headers.get('Content-Disposition')) ?? fallback);
    } catch (e) {
      setFailure(e instanceof Error ? e.message : t.downloadFailed);
    } finally {
      setDownloading(null);
    }
  }

  if (!authLoading && isAuthenticated && !canDownload) {
    return (
      <Forbidden
        message={t.forbidden}
        backLink={`/courses/${courseId}`}
        backText={t.backToCourse}
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={t.templates}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            <p className="text-sm text-muted">
              {t.intro}
            </p>

            {failure && (
              <div className="p-3 bg-danger-wash border border-danger-line rounded text-sm text-danger-text">{failure}</div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {LAYOUT_IDS.map((id) => {
                const l = t.layouts[id];
                return (
                <div key={id} className="p-5 bg-surface border border-rule rounded-lg flex flex-col gap-3">
                  <div className="flex items-start gap-4">
                    <svg className="h-8 w-8 text-accent-text shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICONS[id]} />
                    </svg>
                    <div>
                      <h3 className="font-semibold text-fg">{l.title}</h3>
                      <p className="text-sm text-muted mt-0.5">{l.desc}</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted">{l.detail}</p>
                  <button
                    type="button"
                    onClick={() => download(id)}
                    disabled={downloading !== null}
                    className="self-start mt-auto px-3 py-1.5 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
                  >
                    {downloading === id ? t.preparing : t.download}
                  </button>
                </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

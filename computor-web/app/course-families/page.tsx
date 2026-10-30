'use client';

import Link from 'next/link';
import { useResource } from '@/src/hooks/useResource';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import { displayName } from '@/src/utils/displayName';
import { localized } from '@/src/utils/localizedText';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();
const coursesClient = new CoursesClient();

const COPY = {
  de: {
    crumb: 'Kursfamilien',
    subtitle: 'Eine Kursfamilie fasst zusammengehörige Kurse innerhalb einer Organisation zusammen.',
    newFamily: 'Neue Kursfamilie',
    loading: 'Wird geladen …',
    empty: 'Noch keine Kursfamilien.',
    untitledOrg: 'Organisation ohne Titel',
    unknownOrg: 'Unbekannte Organisation',
    untitledFamily: 'Kursfamilie ohne Titel',
    courses: (n: number) => `${n} ${n === 1 ? 'Kurs' : 'Kurse'}`,
  },
  en: {
    crumb: 'Course families',
    subtitle: 'A course family groups related courses within an organization.',
    newFamily: 'New Course Family',
    loading: 'Loading…',
    empty: 'No course families yet.',
    untitledOrg: 'Untitled Organization',
    unknownOrg: 'Unknown organization',
    untitledFamily: 'Untitled Course Family',
    courses: (n: number) => `${n} ${n === 1 ? 'course' : 'courses'}`,
  },
};

export default function CourseFamiliesPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const { canCreateCourseFamily } = usePermissions();

  const { data, loading, error } = useResource(async () => {
    const [families, orgs, courses] = await Promise.all([
      courseFamiliesClient.listCourseFamiliesCourseFamiliesGet({}),
      organizationsClient.listOrganizationsOrganizationsGet({}),
      coursesClient.listCoursesCoursesGet({}),
    ]);
    const courseCounts: Record<string, number> = {};
    for (const c of courses) {
      if (c.course_family_id) courseCounts[c.course_family_id] = (courseCounts[c.course_family_id] ?? 0) + 1;
    }
    return { families, orgs, courseCounts };
  }, []);

  const families = (data?.families ?? []).map((family) => localized(family, language));
  const orgs = data?.orgs ?? [];
  const courseCounts = data?.courseCounts ?? {};
  const orgLabel = (id: string) => {
    const o = orgs.find((x) => x.id === id);
    return o ? displayName(o, t.untitledOrg) : t.unknownOrg;
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.crumb }]}
          title={t.crumb}
          subtitle={t.subtitle}
          actions={
            canCreateCourseFamily() ? (
              <Link href="/course-families/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
                {t.newFamily}
              </Link>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : families.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">{t.empty}</div>
        ) : (
          <ScrollArea spacing="rows">
            {families.map((f) => (
              <Link key={f.id} href={`/course-families/${f.id}`} className="block bg-surface border border-rule rounded-lg p-4 hover:border-accent-line hover:shadow-sm transition-all">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-fg">{displayName(f, t.untitledFamily)}</div>
                  <span className="shrink-0 text-xs text-muted">
                    {t.courses(courseCounts[f.id] ?? 0)}
                  </span>
                </div>
                <div className="text-xs text-muted">{orgLabel(f.organization_id)}</div>
              </Link>
            ))}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

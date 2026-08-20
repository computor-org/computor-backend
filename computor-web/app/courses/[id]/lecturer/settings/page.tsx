'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import SectionCard, { SectionHint } from '@/src/components/SectionCard';
import Button from '@/src/components/ui/Button';
import PublicCourseField from '@/src/components/courses/PublicCourseField';
import { displayName } from '@/src/utils/displayName';
import type { CourseGet } from 'types/generated';

const coursesClient = new CoursesClient();

/**
 * Course settings owned by course staff rather than by the org hierarchy.
 *
 * Distinct from /courses/[id]/edit, which is gated on canManageHierarchy
 * (admin / _organization_manager) and covers the course's identity and git
 * binding. Self-registration is a decision the course's own maintainers make,
 * so it lives here in the lecturer view (issue #213).
 */
export default function LecturerCourseSettingsPage() {
  const courseId = useParams().id as string;
  const notify = useNotify();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { courseHasAtLeast } = usePermissions();

  // The page itself is lecturer-and-above (it sits in the lecturer view);
  // flipping `public` mirrors the backend guard at _maintainer.
  const canView = courseHasAtLeast(courseId, '_lecturer');
  const canSetPublic = courseHasAtLeast(courseId, '_maintainer');

  const { data: course, loading, error } = useResource(
    () => coursesClient.getCoursesCoursesIdGet({ id: courseId }),
    [courseId],
    { enabled: canView },
  );

  const [isPublic, setIsPublic] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (course) setIsPublic((course as CourseGet).public ?? false);
  }, [course]);

  const dirty = course ? isPublic !== ((course as CourseGet).public ?? false) : false;

  async function save() {
    setSaving(true);
    try {
      await coursesClient.updateCoursesCoursesIdPatch({ id: courseId, body: { public: isPublic } });
      notify(
        isPublic
          ? 'This course is now listed in the catalog for self-registration.'
          : 'This course is no longer listed for self-registration.',
        'success',
      );
    } catch (e) {
      // Most likely the backend's _maintainer guard, which the disabled
      // control should already have prevented — surface it rather than
      // silently reverting.
      notify(e instanceof Error ? e.message : 'Could not save the setting.', 'error');
      setIsPublic((course as CourseGet | null)?.public ?? false);
    } finally {
      setSaving(false);
    }
  }

  if (!authLoading && isAuthenticated && !canView) {
    return (
      <Forbidden
        message="You need lecturer access (or higher) on this course to see its settings."
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
            { label: displayName(course, 'Course'), href: `/courses/${courseId}` },
            { label: 'Settings' },
          ]}
          title="Course settings"
          subtitle="Settings the course's own staff control."
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            <div className="max-w-3xl space-y-6">
              <SectionCard
                title="Self-registration"
                note={
                  canSetPublic
                    ? undefined
                    : 'Only a course maintainer or owner can change this. Listing a course advertises it to every account on this deployment, so it is deliberately held above the lecturer role.'
                }
              >
                <PublicCourseField
                  value={isPublic}
                  onChange={setIsPublic}
                  disabled={!canSetPublic}
                />
                {isPublic && (
                  <SectionHint>
                    New students land in this course&apos;s first group. If the course has no groups
                    yet, one named “default” is created for them.
                  </SectionHint>
                )}
                {canSetPublic && (
                  <div className="flex items-center gap-3">
                    <Button onClick={save} disabled={!dirty} loading={saving} loadingLabel="Saving…">
                      Save
                    </Button>
                  </div>
                )}
              </SectionCard>
            </div>
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

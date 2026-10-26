'use client';

import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import { ButtonLink } from '@/src/components/ui/Button';
import { CoderClient } from '@/src/clients/CoderClient';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import { displayName } from '@/src/utils/displayName';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const coderClient = new CoderClient();

const COPY = {
  de: {
    intro:
      'Welche Arbeitsumgebungs-Vorlagen jeder Kurs seinen Mitgliedern anbietet. Mitglieder eines Kurses mit mindestens einer Vorlage können diese Arbeitsumgebungen von der Kursseite aus starten, eine globale Rolle für Arbeitsumgebungen ist dafür nicht nötig. Mit der Bereitstellung durch Lehrende können die Lehrenden des Kurses zusätzlich (temporäre) Arbeitsumgebungen für ihre Studierenden anlegen.',
    loading: 'Kurse werden geladen …',
    course: 'Kurs',
    templates: 'Vorlagen',
    provisioning: 'Bereitstellung durch Lehrende',
    actions: 'Aktionen',
    untitled: 'Kurs ohne Titel',
    none: 'Keine',
    enabled: 'Aktiv',
    off: 'Aus',
    configure: 'Konfigurieren',
    empty: 'Keine Kurse.',
  },
  en: {
    intro:
      "Which workspace templates each course offers its members. Members of a course with at least one template can launch those workspaces from the course page — no global workspace role needed. Lecturer provisioning additionally lets the course's lecturers create (throwaway) workspaces for their students.",
    loading: 'Loading courses…',
    course: 'Course',
    templates: 'Templates',
    provisioning: 'Lecturer provisioning',
    actions: 'Actions',
    untitled: 'Untitled Course',
    none: 'None',
    enabled: 'Enabled',
    off: 'Off',
    configure: 'Configure',
    empty: 'No courses.',
  },
};

/** All courses with their allowed workspace templates, linking to the editor. */
export default function WorkspaceCoursesPanel() {
  const t = COPY[useUiLanguage()];
  const { data, loading, error } = useResource(() => coderClient.listAdminCourses(), []);
  const courses = data?.courses ?? [];

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <p className="shrink-0 text-sm text-muted">
        {t.intro}
      </p>

      {loading ? (
        <ListLoading>{t.loading}</ListLoading>
      ) : (
        <ScrollPanel>
          <Table>
            <Thead>
              <tr>
                <Th>{t.course}</Th>
                <Th>{t.templates}</Th>
                <Th>{t.provisioning}</Th>
                <Th className="text-right">{t.actions}</Th>
              </tr>
            </Thead>
            <Tbody>
              {courses.map((course) => (
                <Tr key={course.course_id} className="hover:bg-canvas">
                  <Td>
                    <div className="text-sm font-medium text-fg">
                      {displayName(course, t.untitled)}
                    </div>
                  </Td>
                  <Td>
                    {course.template_names.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {course.template_names.map((name) => (
                          <span
                            key={name}
                            className="inline-flex items-center rounded bg-sunken px-2 py-0.5 text-xs font-mono text-body"
                          >
                            {name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-subtle">{t.none}</span>
                    )}
                  </Td>
                  <Td>
                    {course.lecturer_provision_enabled ? (
                      <span className="inline-flex items-center rounded bg-success-wash px-2 py-0.5 text-xs font-medium text-success-text">
                        {t.enabled}
                      </span>
                    ) : (
                      <span className="text-sm text-subtle">{t.off}</span>
                    )}
                  </Td>
                  <Td>
                    <div className="flex justify-end">
                      <ButtonLink
                        href={`/workspaces/admin/courses/${course.course_id}`}
                        size="xs"
                        variant="secondary"
                      >
                        {t.configure}
                      </ButtonLink>
                    </div>
                  </Td>
                </Tr>
              ))}
              {courses.length === 0 && (
                <Tr>
                  <Td colSpan={4} className="py-8 text-center text-sm text-muted">
                    {t.empty}
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}
    </>
  );
}

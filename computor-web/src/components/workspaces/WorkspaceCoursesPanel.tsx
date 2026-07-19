'use client';

import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import { ButtonLink } from '@/src/components/ui/Button';
import { CoderClient } from '@/src/clients/CoderClient';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';

const coderClient = new CoderClient();

/** All courses with their allowed workspace templates, linking to the editor. */
export default function WorkspaceCoursesPanel() {
  const { data, loading, error } = useResource(() => coderClient.listAdminCourses(), []);
  const courses = data?.courses ?? [];

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <p className="shrink-0 text-sm text-gray-500">
        Which workspace templates each course offers its members. Members of a course with at
        least one template can launch those workspaces from the course page — no global
        workspace role needed. Lecturer provisioning additionally lets the course&apos;s
        lecturers create (throwaway) workspaces for their students.
      </p>

      {loading ? (
        <ListLoading>Loading courses…</ListLoading>
      ) : (
        <ScrollPanel className="h-[36rem] min-h-[36rem] max-h-[36rem]">
          <Table>
            <Thead>
              <tr>
                <Th>Course</Th>
                <Th>Templates</Th>
                <Th>Lecturer provisioning</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {courses.map((course) => (
                <Tr key={course.course_id} className="hover:bg-gray-50">
                  <Td>
                    <div className="text-sm font-medium text-gray-900">
                      {course.title || course.path || course.course_id}
                    </div>
                    {course.path && <div className="text-xs text-gray-500">{course.path}</div>}
                  </Td>
                  <Td>
                    {course.template_names.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {course.template_names.map((name) => (
                          <span
                            key={name}
                            className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-700"
                          >
                            {name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">None</span>
                    )}
                  </Td>
                  <Td>
                    {course.lecturer_provision_enabled ? (
                      <span className="inline-flex items-center rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        Enabled
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">Off</span>
                    )}
                  </Td>
                  <Td>
                    <div className="flex justify-end">
                      <ButtonLink
                        href={`/workspaces/admin/courses/${course.course_id}`}
                        size="xs"
                        variant="secondary"
                      >
                        Configure
                      </ButtonLink>
                    </div>
                  </Td>
                </Tr>
              ))}
              {courses.length === 0 && (
                <Tr>
                  <Td colSpan={4} className="py-8 text-center text-sm text-gray-500">
                    No courses.
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

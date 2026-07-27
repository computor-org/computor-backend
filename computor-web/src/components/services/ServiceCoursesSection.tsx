'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { inputCls } from '@/src/components/ui/tokens';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { COURSE_ROLES, COURSE_ROLE_LABEL } from '@/src/utils/courseRoles';
import type { CourseList, CourseMemberList } from 'types/generated';

const courseMembersClient = new CourseMembersClient();
const coursesClient = new CoursesClient();

/**
 * Course memberships for a service account.
 *
 * This is how an AI-agent service gets course-scoped authority: enrolling it
 * as a CourseMember gives it that course role's claims through the normal
 * membership path, independent of its token scopes.
 *
 * No repository is provisioned — `_should_skip_service_account` skips the
 * post-create hooks for service users unless their ServiceType sets
 * `requires_workspace`, which the seeded `agent` type does not.
 */
export default function ServiceCoursesSection({ userId }: { userId: string }) {
  const [members, setMembers] = useState<CourseMemberList[]>([]);
  const [courses, setCourses] = useState<CourseList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [courseId, setCourseId] = useState('');
  const [roleId, setRoleId] = useState<string>('_tutor');
  const [saving, setSaving] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState<CourseMemberList | null>(null);

  const load = useCallback(async () => {
    try {
      const [memberList, courseList] = await Promise.all([
        courseMembersClient.listCourseMembersCourseMembersGet({ userId, limit: 100 }),
        coursesClient.listCoursesCoursesGet({ limit: 200 }).catch(() => [] as CourseList[]),
      ]);
      setMembers(memberList);
      setCourses(courseList);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load course memberships');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const enrolledCourseIds = useMemo(
    () => new Set(members.map((m) => m.course_id)),
    [members],
  );
  const available = courses.filter((c) => !enrolledCourseIds.has(c.id));
  const courseLabel = (id: string) => {
    const course = courses.find((c) => c.id === id);
    return course?.title || course?.path || id;
  };

  async function enrol() {
    setSaving(true);
    setError(null);
    try {
      await courseMembersClient.createCourseMembersCourseMembersPost({
        body: { user_id: userId, course_id: courseId, course_role_id: roleId },
      });
      setCourseId('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not enrol the service');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-900">Course memberships</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Enrolling this service in a course grants it that course role&apos;s permissions — the way an
          agent gets access to a specific course. No git repository is provisioned for it.
        </p>
      </div>

      <div className="p-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void enrol();
          }}
          className="flex flex-wrap items-end gap-3 mb-5"
        >
          <div className="flex-1 min-w-[14rem]">
            <label className="block text-xs font-medium text-gray-700 mb-1">Course</label>
            <select className={inputCls} value={courseId} onChange={(e) => setCourseId(e.target.value)}>
              <option value="">Select a course…</option>
              {available.map((c) => (
                <option key={c.id} value={c.id}>{c.title || c.path}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Role</label>
            <select className={inputCls} value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              {COURSE_ROLES.map((r) => (
                <option key={r} value={r}>{COURSE_ROLE_LABEL[r] ?? r}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={saving || !courseId}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Adding…' : 'Add to course'}
          </button>
        </form>

        {loading ? (
          <div className="text-sm text-gray-500">Loading…</div>
        ) : members.length === 0 ? (
          <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-lg p-6 text-center">
            Not enrolled in any course.
          </div>
        ) : (
          <div className="border border-gray-200 rounded-lg divide-y">
            {members.map((m) => (
              <div key={m.id} className="flex items-center justify-between px-4 py-3 gap-4">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{courseLabel(m.course_id)}</div>
                  <div className="text-xs text-gray-500">{COURSE_ROLE_LABEL[m.course_role_id] ?? m.course_role_id}</div>
                </div>
                <button
                  onClick={() => setConfirmRemove(m)}
                  className="text-sm text-red-600 hover:underline whitespace-nowrap"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {confirmRemove && (
        <ConfirmDialog
          open
          title="Remove from course"
          message={`This service will lose its ${COURSE_ROLE_LABEL[confirmRemove.course_role_id] ?? confirmRemove.course_role_id} access to ${courseLabel(confirmRemove.course_id)}.`}
          confirmLabel="Remove"
          variant="danger"
          onConfirm={async () => {
            await courseMembersClient.deleteCourseMembersCourseMembersIdDelete({ id: confirmRemove.id });
            setConfirmRemove(null);
            await load();
          }}
          onCancel={() => setConfirmRemove(null)}
        />
      )}
    </div>
  );
}

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { inputCls } from '@/src/components/ui/tokens';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { COURSE_ROLES, COURSE_ROLE_LABEL } from '@/src/utils/courseRoles';
import type { CourseList, CourseMemberList } from 'types/generated';
import { displayName } from '@/src/utils/displayName';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const courseMembersClient = new CourseMembersClient();
const coursesClient = new CoursesClient();

const COPY = {
  de: {
    loadFailed: 'Kursmitgliedschaften konnten nicht geladen werden',
    unknownCourse: 'Unbekannter Kurs',
    enrolFailed: 'Der Dienst konnte nicht eingeschrieben werden',
    heading: 'Kursmitgliedschaften',
    intro:
      'Wird dieser Dienst in einen Kurs eingeschrieben, erhält er die Berechtigungen der gewählten Kursrolle – so bekommt ein Agent Zugriff auf einen bestimmten Kurs. Für ihn wird kein Git-Repository angelegt.',
    course: 'Kurs',
    selectCourse: 'Kurs auswählen …',
    untitledCourse: 'Unbenannter Kurs',
    role: 'Rolle',
    adding: 'Wird hinzugefügt …',
    add: 'Zum Kurs hinzufügen',
    loading: 'Wird geladen …',
    empty: 'In keinem Kurs eingeschrieben.',
    remove: 'Entfernen',
    removeTitle: 'Aus Kurs entfernen',
    removeMessage: (role: string, course: string) =>
      `Dieser Dienst verliert seinen Zugriff als ${role} auf ${course}.`,
  },
  en: {
    loadFailed: 'Could not load course memberships',
    unknownCourse: 'Unknown course',
    enrolFailed: 'Could not enrol the service',
    heading: 'Course memberships',
    intro:
      "Enrolling this service in a course grants it that course role's permissions — the way an agent gets access to a specific course. No git repository is provisioned for it.",
    course: 'Course',
    selectCourse: 'Select a course…',
    untitledCourse: 'Untitled Course',
    role: 'Role',
    adding: 'Adding…',
    add: 'Add to course',
    loading: 'Loading…',
    empty: 'Not enrolled in any course.',
    remove: 'Remove',
    removeTitle: 'Remove from course',
    removeMessage: (role: string, course: string) =>
      `This service will lose its ${role} access to ${course}.`,
  },
} as const;

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
  const t = COPY[useUiLanguage()];
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
      setError(e instanceof Error ? e.message : t.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [userId, t]);

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
    return displayName(course, t.unknownCourse);
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
      setError(e instanceof Error ? e.message : t.enrolFailed);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-surface border border-rule rounded-lg">
      <div className="px-6 py-4 border-b border-rule-soft">
        <h2 className="text-base font-semibold text-fg">{t.heading}</h2>
        <p className="text-sm text-muted mt-0.5">
          {t.intro}
        </p>
      </div>

      <div className="p-6">
        {error && (
          <div className="mb-4 rounded-lg border border-danger-line bg-danger-wash px-3 py-2 text-sm text-danger-text">{error}</div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void enrol();
          }}
          className="flex flex-wrap items-end gap-3 mb-5"
        >
          <div className="flex-1 min-w-[14rem]">
            <label className="block text-xs font-medium text-body mb-1">{t.course}</label>
            <select className={inputCls} value={courseId} onChange={(e) => setCourseId(e.target.value)}>
              <option value="">{t.selectCourse}</option>
              {available.map((c) => (
                <option key={c.id} value={c.id}>{displayName(c, t.untitledCourse)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-body mb-1">{t.role}</label>
            <select className={inputCls} value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              {COURSE_ROLES.map((r) => (
                <option key={r} value={r}>{COURSE_ROLE_LABEL[r] ?? r}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={saving || !courseId}
            className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? t.adding : t.add}
          </button>
        </form>

        {loading ? (
          <div className="text-sm text-muted">{t.loading}</div>
        ) : members.length === 0 ? (
          <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">
            {t.empty}
          </div>
        ) : (
          <div className="border border-rule rounded-lg divide-y divide-rule">
            {members.map((m) => (
              <div key={m.id} className="flex items-center justify-between px-4 py-3 gap-4">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-fg truncate">{courseLabel(m.course_id)}</div>
                  <div className="text-xs text-muted">{COURSE_ROLE_LABEL[m.course_role_id] ?? m.course_role_id}</div>
                </div>
                <button
                  onClick={() => setConfirmRemove(m)}
                  className="text-sm text-danger-text hover:underline whitespace-nowrap"
                >
                  {t.remove}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {confirmRemove && (
        <ConfirmDialog
          open
          title={t.removeTitle}
          message={t.removeMessage(COURSE_ROLE_LABEL[confirmRemove.course_role_id] ?? confirmRemove.course_role_id, courseLabel(confirmRemove.course_id))}
          confirmLabel={t.remove}
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

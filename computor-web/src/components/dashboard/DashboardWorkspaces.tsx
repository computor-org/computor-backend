'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { useRouter } from 'next/navigation';
import Panel from '@/src/components/ui/Panel';
import Button from '@/src/components/ui/Button';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';
import WorkspaceStatusBadge, { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import { workspaceVersionLabel } from '@/src/components/workspaces/versionDate';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { lastWorkspaceCourse, reserveWorkspaceLaunch, focusRunningWorkspace, workspaceLaunchUrl } from '@/src/utils/workspaceLaunch';
import type { CoderWorkspace } from '@/src/types/workspaces';

const COPY = {
  de: {
    open: 'Öffnen',
    failed: 'Die Arbeitsumgebung konnte nicht geöffnet werden. Versuch es noch einmal.',
    startAndOpen: 'Starten und öffnen',
    retry: 'Erneut starten',
    chooseCourse: 'Kurs auswählen',
    course: (title: string) => `Kurs: ${title}`,
    lastCourse: (title: string) => `Zuletzt geöffnet in ${title}`,
  },
  en: {
    open: 'Open',
    failed: 'The workspace could not be opened. Please retry.',
    startAndOpen: 'Start and open',
    retry: 'Start again',
    chooseCourse: 'Choose a course',
    course: (title: string) => `Course: ${title}`,
    lastCourse: (title: string) => `Last opened in ${title}`,
  },
};

/**
 * The learner's workspaces on the dashboard, in every state.
 *
 * A returning learner usually finds the workspace stopped, because it stops
 * after an hour without use, so listing only running ones hid exactly the
 * workspace they came back for. Each row has one labelled action that goes
 * through the launch page, which starts a stopped workspace and waits for it.
 * It reopens the course the workspace was last opened for (remembered by the
 * server, else by this browser), when that course is still one of the user's.
 */
export default function DashboardWorkspaces({
  workspaces,
  courseTitles,
  courseTemplates,
}: {
  workspaces: CoderWorkspace[];
  courseTitles: Map<string, string>;
  courseTemplates: { courseId: string; templates: string[] }[];
}) {
  const router = useRouter();
  const { user } = useAuth();
  const notify = useNotify();
  const reservationRef = useRef<ReturnType<typeof reserveWorkspaceLaunch> | null>(null);
  useEffect(() => () => { reservationRef.current?.cancel(); }, [user?.id]);
  const [selectedCourses, setSelectedCourses] = useState<Record<string, string>>({});
  const language = useUiLanguage();
  const t = COPY[language];

  return (
    <Panel padding="none">
      <ul className="divide-y divide-rule-soft">
        {workspaces.map((ws) => {
          const category = categorizeStatus(ws.latest_build_status, ws.latest_build_transition);
          const owner = ws.owner_name ?? '';
          const candidates = courseTemplates.filter((c) => c.templates.includes(ws.template_name ?? ''));
          const rememberedCourse = [ws.last_course_id, owner ? lastWorkspaceCourse(owner, ws.name) : undefined]
            .find((id): id is string => !!id && courseTitles.has(id));
          const courseId = rememberedCourse ?? selectedCourses[ws.id] ?? (candidates.length === 1 ? candidates[0].courseId : undefined);
          const version = workspaceVersionLabel(ws.template_version_created_at, language);
          // A workspace that is stopping is not opened but started again once
          // it has stopped, which is what the launch page does.
          const label =
            category === 'failed'
              ? t.retry
              : ws.latest_build_transition === 'stop' || category === 'stopped'
                ? t.startAndOpen
                : t.open;

          // Synchronous on purpose: the tab has to open inside the click, or
          // popup blockers eat it.
          const launch = async () => {
            if (!user?.id) return;
            const reservation = reserveWorkspaceLaunch(user.id, ws.template_name ?? ws.name, ws.name, owner);
            reservationRef.current = reservation;
            try {
              const outcome = await focusRunningWorkspace(reservation, ws, courseId, undefined, language);
              if (outcome === 'handled') return;
              if (!reservation.current()) return;
              const url = workspaceLaunchUrl(owner, ws.name, courseId);
              if (outcome === 'lifecycle' && reservation.tab) reservation.tab.location.replace(url);
              else { if (!reservation.tab) window.name = reservation.key; router.push(url); }
            } catch {
              reservation.closeFresh();
              if (reservation.current()) notify(t.failed, 'error');
            }
          };

          return (
            <li key={ws.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
              <TemplateIcon template={{ name: ws.template_name ?? ws.name }} size="sm" />
              {/* basis-40: on a phone the actions wrap below instead of squeezing the text. */}
              <div className="min-w-0 flex-1 basis-40">
                <div className="text-sm font-medium text-fg truncate">
                  {ws.template_display_name || ws.template_name || ws.name}
                </div>
                {courseId && (
                  <div className="text-xs text-muted">{(rememberedCourse ? t.lastCourse : t.course)(courseTitles.get(courseId)!)}</div>
                )}
                {version && <div className="text-xs text-muted">{version}</div>}
              </div>
              {!rememberedCourse && candidates.length > 1 && (
                <select
                  aria-label={t.chooseCourse}
                  className="min-w-0 max-w-full rounded-md border border-rule-soft bg-surface px-2 py-1 text-sm text-fg"
                  value={selectedCourses[ws.id] ?? ''}
                  onChange={(event) => setSelectedCourses((current) => ({ ...current, [ws.id]: event.target.value }))}
                >
                  <option value="">{t.chooseCourse}</option>
                  {candidates.map((course) => <option key={course.courseId} value={course.courseId}>{courseTitles.get(course.courseId)}</option>)}
                </select>
              )}
              <div className="flex shrink-0 items-center gap-2 ml-auto">
                <WorkspaceStatusBadge status={ws.latest_build_status} transition={ws.latest_build_transition} />
                <Button size="sm" onClick={launch} disabled={!owner || (candidates.length > 1 && !courseId)}>
                  {label}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

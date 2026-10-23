'use client';

import { useRouter } from 'next/navigation';
import Panel from '@/src/components/ui/Panel';
import Button from '@/src/components/ui/Button';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';
import WorkspaceStatusBadge, { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import { workspaceVersionLabel } from '@/src/components/workspaces/versionDate';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { lastWorkspaceCourse, openLaunchTab, workspaceLaunchUrl } from '@/src/utils/workspaceLaunch';
import type { CoderWorkspace } from '@/src/types/workspaces';

const COPY = {
  de: {
    open: 'Öffnen',
    startAndOpen: 'Starten und öffnen',
    retry: 'Erneut starten',
    lastCourse: (title: string) => `Zuletzt geöffnet in ${title}`,
  },
  en: {
    open: 'Open',
    startAndOpen: 'Start and open',
    retry: 'Start again',
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
 * It reopens the course this browser last opened the workspace for, when that
 * course is still one of the user's.
 */
export default function DashboardWorkspaces({
  workspaces,
  courseTitles,
}: {
  workspaces: CoderWorkspace[];
  courseTitles: Map<string, string>;
}) {
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];

  return (
    <Panel padding="none">
      <ul className="divide-y divide-rule-soft">
        {workspaces.map((ws) => {
          const category = categorizeStatus(ws.latest_build_status, ws.latest_build_transition);
          const owner = ws.owner_name ?? '';
          const remembered = owner ? lastWorkspaceCourse(owner, ws.name) : undefined;
          const courseId = remembered && courseTitles.has(remembered) ? remembered : undefined;
          const version = workspaceVersionLabel(ws.template_version_created_at, language);
          const label =
            category === 'running' || category === 'pending'
              ? t.open
              : category === 'failed'
                ? t.retry
                : t.startAndOpen;

          // Synchronous on purpose: the tab has to open inside the click, or
          // popup blockers eat it.
          const launch = () => {
            if (!openLaunchTab(owner, ws.name, courseId)) {
              router.push(workspaceLaunchUrl(owner, ws.name, courseId));
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
                  <div className="text-xs text-muted">{t.lastCourse(courseTitles.get(courseId)!)}</div>
                )}
                {version && <div className="text-xs text-muted">{version}</div>}
              </div>
              <div className="flex shrink-0 items-center gap-2 ml-auto">
                <WorkspaceStatusBadge status={ws.latest_build_status} transition={ws.latest_build_transition} />
                <Button size="sm" onClick={launch} disabled={!owner}>
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

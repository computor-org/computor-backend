import { CoderClient } from '@/src/clients/CoderClient';
import type { CoderWorkspace } from '@/src/types/workspaces';

/**
 * The workspace launch page waits for a workspace to boot and then redirects
 * itself to it. Callers must open it from inside a click (see openLaunchTab) —
 * a window.open() after an await is no longer tied to the user gesture and
 * popup blockers eat it.
 */
export function workspaceLaunchUrl(owner: string, name: string, courseId?: string, courseContentId?: string): string {
  const url = `/workspaces/launch?owner=${encodeURIComponent(owner)}&name=${encodeURIComponent(name)}`;
  const courseUrl = courseId ? `${url}&courseId=${encodeURIComponent(courseId)}` : url;
  return courseContentId ? `${courseUrl}&courseContentId=${encodeURIComponent(courseContentId)}` : courseUrl;
}

/**
 * Where to park a tab opened before the workspace exists (creation has to open
 * the tab inside the click, but only the provision response knows the name).
 * Shows the launch spinner immediately instead of a blank page; the opener
 * replaces the URL with workspaceLaunchUrl() — or closes the tab — once
 * provisioning returns.
 */
export const workspaceCreatingUrl = '/workspaces/launch?creating=1';

/**
 * Open the launch page for a workspace in a new tab. Returns false when the
 * popup was blocked, so the caller can fall back to launching in this tab.
 * Call this synchronously from the click handler.
 */
export function openLaunchTab(owner: string, name: string, courseId?: string, courseContentId?: string): boolean {
  return window.open(workspaceLaunchUrl(owner, name, courseId, courseContentId), '_blank') !== null;
}

/**
 * The name a workspace provisioned without one gets — a mirror of the
 * backend's derive_workspace_name(). Display and matching only: the server
 * decides, and self-provisioners always get this name (it forces
 * workspace_name to null), which is what caps them at one per template.
 */
export function derivedWorkspaceName(template: string): string {
  return template.replace(/-workspace$/, '').replace(/[^a-z0-9-]/g, '') || 'workspace';
}

const LAST_COURSE_KEY = 'computor.workspaceLastCourse';

function readLastCourses(): Record<string, string> {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(LAST_COURSE_KEY) ?? '{}');
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

/**
 * Remember the course a workspace was last opened for, so the dashboard can
 * reopen it in the same course. A per-browser convenience only: the server's
 * launch context expires within minutes, and losing this entry just means the
 * dashboard opens the workspace without picking a course.
 */
export function rememberWorkspaceCourse(owner: string, name: string, courseId: string): void {
  try {
    const courses = readLastCourses();
    courses[`${owner}/${name}`] = courseId;
    window.localStorage.setItem(LAST_COURSE_KEY, JSON.stringify(courses));
  } catch {
    // Storage blocked or full: nothing to remember, nothing breaks.
  }
}

/** The course this browser last opened the workspace for, if any. */
export function lastWorkspaceCourse(owner: string, name: string): string | undefined {
  const courseId = readLastCourses()[`${owner}/${name}`];
  return typeof courseId === 'string' ? courseId : undefined;
}

// A portal document shares cold workspace resolution and orders context writes.
// The browser name survives portal navigation; no editor document is replaced
// merely to send a new course or exercise request.
const launchIntents = new Map<string, number>();
const wantedLaunches = new Set<string>();
const waitingTabs = new Map<string, Window>();
const workspaceResolutions = new Map<string, Promise<CoderWorkspace>>();
const contextWrites = new Map<string, Promise<unknown>>();
const launchClient = new CoderClient();

export function reserveWorkspaceLaunch(userId: string, template: string, name = derivedWorkspaceName(template), owner = '', sameTab = false) {
  const key = `computor-workspace:${encodeURIComponent(userId)}:${encodeURIComponent(template)}${name === derivedWorkspaceName(template) ? '' : `:${encodeURIComponent(owner)}/${encodeURIComponent(name)}`}`;
  const intent = (launchIntents.get(key) ?? 0) + 1;
  launchIntents.set(key, intent);
  wantedLaunches.add(key);
  let tab = window.open('', key);
  let active = true;
  const current = () => active && launchIntents.get(key) === intent;
  const waiting = () => {
    try { return !!tab && (tab.location.href === 'about:blank' || (tab.location.origin === window.location.origin && tab.location.pathname === '/workspaces/launch')); }
    catch { return false; }
  };
  let fresh = false;
  try { fresh = tab?.location.href === 'about:blank'; } catch { /* Retain an unverified window. */ }
  if (fresh && tab && sameTab) { tab.close(); tab = null; fresh = false; }
  else if (fresh && tab) { waitingTabs.set(key, tab); tab.location.replace(workspaceCreatingUrl); }
  else if (tab && waitingTabs.get(key) === tab && waiting()) fresh = true;
  else waitingTabs.delete(key);
  return {
    key, tab, fresh,
    current,
    active: () => active,
    wanted: () => wantedLaunches.has(key),
    cancel() {
      const latest = current();
      active = false;
      if (latest) { wantedLaunches.delete(key); launchIntents.set(key, intent + 1); }
    },
    closeFresh() { if (fresh && tab && current() && waiting()) { tab.close(); waitingTabs.delete(key); } },
    resolveWorkspace(resolve: () => Promise<CoderWorkspace>) {
      let pending = workspaceResolutions.get(key);
      if (!pending) {
        pending = resolve().finally(() => { if (workspaceResolutions.get(key) === pending) workspaceResolutions.delete(key); });
        workspaceResolutions.set(key, pending);
      }
      return pending;
    },
  };
}

/** Verify a retained editor against fresh server authority before focus-only reuse. */
export async function focusRunningWorkspace(
  reservation: ReturnType<typeof reserveWorkspaceLaunch>, workspace: CoderWorkspace,
  courseId?: string, courseContentId?: string, uiLanguage?: 'de' | 'en',
): Promise<'handled' | 'lifecycle' | 'unverified'> {
  if (!reservation.tab || reservation.fresh) return 'lifecycle';
  if (!reservation.current()) return 'handled';
  const details = await launchClient.getWorkspaceDetails({ username: workspace.owner_name!, workspaceName: workspace.name });
  if (!reservation.current()) return 'handled';
  const url = details.code_server_url || details.access_url;
  let verified = false;
  try {
    if (url && details.workspace.id === workspace.id &&
        details.workspace.owner_name === workspace.owner_name && details.workspace.name === workspace.name) {
      const expected = new URL(url, window.location.origin);
      const actual = new URL(reservation.tab.location.href);
      const prefix = expected.pathname.replace(/\/$/, '') + '/';
      verified = expected.origin === window.location.origin && actual.origin === expected.origin &&
        (actual.pathname === expected.pathname || actual.pathname.startsWith(prefix));
    }
  } catch { /* Cross-origin or inaccessible contexts use the ordinary safe fallback. */ }
  if (!verified) return 'unverified';
  if (details.status !== 'running') return 'lifecycle';
  const previous = contextWrites.get(reservation.key) ?? Promise.resolve();
  const write = previous.catch(() => undefined).then(async () => {
    if (!reservation.current()) return;
    if (courseId) {
      const context = await launchClient.setWorkspaceLaunchContext({
        username: workspace.owner_name!, workspaceName: workspace.name, courseId, courseContentId, uiLanguage,
      });
      if (context.course_id !== courseId || (courseContentId && context.course_content_id !== courseContentId)) {
        throw new Error('Workspace selection was not accepted.');
      }
      rememberWorkspaceCourse(workspace.owner_name!, workspace.name, courseId);
    }
    if (reservation.current()) reservation.tab?.focus();
  });
  contextWrites.set(reservation.key, write);
  try { await write; } finally { if (contextWrites.get(reservation.key) === write) contextWrites.delete(reservation.key); }
  return 'handled';
}

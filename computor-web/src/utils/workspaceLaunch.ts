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

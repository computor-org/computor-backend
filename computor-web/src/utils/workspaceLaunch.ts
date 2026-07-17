/**
 * The workspace launch page waits for a workspace to boot and then redirects
 * itself to it. Callers must open it from inside a click (see openLaunchTab) —
 * a window.open() after an await is no longer tied to the user gesture and
 * popup blockers eat it.
 */
export function workspaceLaunchUrl(owner: string, name: string): string {
  return `/workspaces/launch?owner=${encodeURIComponent(owner)}&name=${encodeURIComponent(name)}`;
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
export function openLaunchTab(owner: string, name: string): boolean {
  return window.open(workspaceLaunchUrl(owner, name), '_blank') !== null;
}

// The name to show for a workspace. One created with the default name is named
// after its template slug ("vscode"), which reads as an identifier; it is shown
// by the template's display name instead. A name the user chose stays.

/** Mirrors derive_workspace_name (computor_backend/coder/naming.py). */
export function defaultWorkspaceName(templateName: string): string {
  let base = templateName.toLowerCase();
  if (base.endsWith('-workspace')) base = base.slice(0, -'-workspace'.length);
  return base.replace(/[^a-z0-9-]/g, '').slice(0, 32).replace(/^-+|-+$/g, '') || 'workspace';
}

export function workspaceLabel(workspace: {
  name: string;
  template_name?: string | null;
  template_display_name?: string | null;
}): string {
  const { name, template_name: template, template_display_name: display } = workspace;
  return template && display && name === defaultWorkspaceName(template) ? display : name;
}

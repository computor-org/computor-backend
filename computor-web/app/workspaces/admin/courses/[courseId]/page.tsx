'use client';

import { Suspense, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import { CourseWorkspacesClient } from '@/src/clients/CourseWorkspacesClient';
import { CoderClient } from '@/src/clients/CoderClient';
import type { CourseWorkspaceTemplatePolicy } from '@/src/types/workspaces';

const courseWorkspacesClient = new CourseWorkspacesClient();
const coderClient = new CoderClient();

/** A course can only restrict, so a policy checkbox is off when either the
 *  template's ceiling denies it or this course does. */
function policyChecked(ceiling: boolean, courseValue: boolean | null | undefined): boolean {
  return ceiling && courseValue !== false;
}

function CourseWorkspaceConfigContent() {
  const params = useParams<{ courseId: string }>();
  const courseId = params.courseId;
  const notify = useNotify();
  const [draft, setDraft] = useState<{
    selected: string[];
    lecturerProvision: boolean;
    policies: Record<string, CourseWorkspaceTemplatePolicy>;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, reload } = useResource(
    () => courseWorkspacesClient.getSettings({ courseId }),
    [courseId],
  );

  // The per-template ceilings. The course settings response only carries them
  // for already-associated templates, so a template checked in this session
  // would have no ceiling to render — the settings list covers every template.
  const { data: templateSettings } = useResource(() => coderClient.listTemplateSettings(), []);

  const ceilings = useMemo(() => {
    const map = new Map<string, { root: boolean; internet: boolean }>();
    for (const row of templateSettings?.settings ?? []) {
      map.set(row.template_name, { root: row.allow_root, internet: row.allow_internet });
    }
    return map;
  }, [templateSettings]);

  /** Templates with no settings row fall back to the .tf variable defaults. */
  function ceilingFor(name: string) {
    return ceilings.get(name) ?? { root: false, internet: true };
  }

  const stored = useMemo(
    () => ({
      selected: (data?.templates ?? []).map((t) => t.template_name),
      lecturerProvision: data?.lecturer_provision_enabled ?? false,
      policies: Object.fromEntries(
        (data?.templates ?? []).map((t) => [
          t.template_name,
          { allow_root: t.allow_root ?? null, allow_internet: t.allow_internet ?? null },
        ]),
      ) as Record<string, CourseWorkspaceTemplatePolicy>,
    }),
    [data],
  );
  // Overlay pattern: fetched state stays derived, local edits live in `draft`.
  const form = draft ?? stored;

  // Picker source: globally enabled templates, plus any currently associated
  // template that is disabled or missing (kept selectable so the list stays
  // saveable; retained names skip server-side validation).
  const pickerItems = useMemo(() => {
    const available = data?.available ?? [];
    const byName = new Map(available.map((t) => [t.name, {
      name: t.name,
      display_name: t.display_name,
      description: t.description,
      icon: t.icon,
      globallyDisabled: false,
    }]));
    for (const item of data?.templates ?? []) {
      if (!byName.has(item.template_name)) {
        byName.set(item.template_name, {
          name: item.template_name,
          display_name: item.display_name ?? null,
          description: item.description ?? null,
          icon: item.icon ?? null,
          globallyDisabled: !item.enabled,
        });
      }
    }
    return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [data]);

  function toggle(name: string) {
    const selected = form.selected.includes(name)
      ? form.selected.filter((n) => n !== name)
      : [...form.selected, name];
    setDraft({ ...form, selected });
  }

  /** Unchecking means "deny for this course"; checking means "no restriction"
   *  (null) rather than true — a course never grants, so storing true would
   *  just be a lie that survives the template's ceiling changing later. */
  function setPolicy(name: string, key: keyof CourseWorkspaceTemplatePolicy, allowed: boolean) {
    setDraft({
      ...form,
      policies: {
        ...form.policies,
        [name]: { ...form.policies[name], [key]: allowed ? null : false },
      },
    });
  }

  async function save() {
    setSaving(true);
    try {
      await courseWorkspacesClient.updateSettings({
        courseId,
        body: {
          template_names: form.selected,
          lecturer_provision_enabled: form.lecturerProvision,
          template_policies: Object.fromEntries(
            form.selected.map((name) => [name, form.policies[name] ?? {}]),
          ),
        },
      });
      notify('Course workspace configuration saved', 'success');
      setDraft(null);
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to save configuration', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspaces' },
          { label: 'Administration', href: '/workspaces/admin?tab=courses' },
          { label: 'Course workspaces' },
        ]}
        title="Course workspace configuration"
        subtitle="Templates this course offers its members, and whether lecturers may provision workspaces for students"
      />

      <ErrorBanner>{error}</ErrorBanner>

      {loading ? (
        <ListLoading>Loading configuration…</ListLoading>
      ) : (
        <ScrollArea>
          <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-fg">Allowed templates</h2>
              <p className="text-sm text-muted mt-1">
                Members of this course can launch the checked templates from the course page —
                no global workspace role needed. Globally disabled templates stay associated
                but are hidden from students until re-enabled.
              </p>
            </div>

            {pickerItems.length === 0 ? (
              <p className="text-sm text-muted">
                No templates available — Coder may be unreachable or still initializing.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {pickerItems.map((item) => {
                  const checked = form.selected.includes(item.name);
                  return (
                    <button
                      key={item.name}
                      type="button"
                      role="checkbox"
                      aria-checked={checked}
                      onClick={() => toggle(item.name)}
                      className={`flex items-start gap-3 rounded-lg border p-4 text-left transition-colors ${
                        checked
                          ? 'border-blue-600 ring-1 ring-blue-600 bg-blue-50/50'
                          : 'border-rule bg-surface hover:border-rule-strong'
                      }`}
                    >
                      <TemplateIcon template={{ icon: item.icon, name: item.name }} />
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-fg">
                          {item.display_name || item.name}
                        </span>
                        <span className="mt-0.5 block text-xs text-muted">{item.name}</span>
                        {item.description && (
                          <span className="mt-0.5 block text-xs text-muted">{item.description}</span>
                        )}
                        {item.globallyDisabled && (
                          <span className="mt-1 inline-flex items-center rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                            Globally disabled
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {form.selected.length > 0 && (
            <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-fg">Root &amp; internet policy</h2>
                <p className="text-sm text-muted mt-1">
                  What members of this course get when they launch each template. A course can
                  only take access away — a control is locked when the template itself already
                  denies it. Applies to newly provisioned workspaces; existing ones keep their
                  policy until they are rebuilt.
                </p>
              </div>

              <div className="space-y-3">
                {[...form.selected].sort((a, b) => a.localeCompare(b)).map((name) => {
                  const ceiling = ceilingFor(name);
                  const policy = form.policies[name] ?? {};
                  return (
                    <div key={name} className="rounded-lg border border-rule p-3">
                      <p className="text-sm font-medium text-fg">{name}</p>
                      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-2">
                        {([
                          ['allow_root', 'Root (sudo)', ceiling.root, policy.allow_root],
                          ['allow_internet', 'Internet', ceiling.internet, policy.allow_internet],
                        ] as const).map(([key, label, allowedByTemplate, courseValue]) => (
                          <label
                            key={key}
                            className={`flex items-center gap-2 text-sm ${
                              allowedByTemplate ? 'text-body' : 'text-subtle'
                            }`}
                            title={
                              allowedByTemplate
                                ? undefined
                                : 'The template denies this; a course cannot grant it.'
                            }
                          >
                            <input
                              type="checkbox"
                              disabled={!allowedByTemplate}
                              checked={policyChecked(allowedByTemplate, courseValue)}
                              onChange={(event) => setPolicy(name, key, event.target.checked)}
                            />
                            {label}
                            {!allowedByTemplate && (
                              <span className="text-xs">(off for this template)</span>
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="bg-surface rounded-lg border border-rule p-5 space-y-3">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={form.lecturerProvision}
                onChange={(event) => setDraft({ ...form, lecturerProvision: event.target.checked })}
                className="mt-0.5"
              />
              <span>
                <span className="block text-sm font-medium text-fg">
                  Lecturer provisioning
                </span>
                <span className="block text-xs text-muted">
                  Course lecturers may bulk-provision workspaces for their students — including
                  throwaway workspaces with a scratch home volume that is deleted with the
                  workspace. Students can open and start these, but not provision new ones.
                </span>
              </span>
            </label>
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={save} loading={saving} loadingLabel="Saving…">
              Save configuration
            </Button>
            {draft && (
              <Button variant="ghost" onClick={() => setDraft(null)} disabled={saving}>
                Discard changes
              </Button>
            )}
          </div>
        </ScrollArea>
      )}
    </ListPageLayout>
  );
}

export default function CourseWorkspaceConfigPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isWorkspaceMaintainer } = usePermissions();

  if (!authLoading && isAuthenticated && !isWorkspaceMaintainer) {
    return (
      <Forbidden
        message="Course workspace configuration requires the workspace maintainer role."
        backLink="/workspaces"
        backText="Back to workspaces"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <Suspense>
        <CourseWorkspaceConfigContent />
      </Suspense>
    </AuthenticatedLayout>
  );
}

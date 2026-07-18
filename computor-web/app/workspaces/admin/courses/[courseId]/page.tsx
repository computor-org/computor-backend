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

const courseWorkspacesClient = new CourseWorkspacesClient();

function CourseWorkspaceConfigContent() {
  const params = useParams<{ courseId: string }>();
  const courseId = params.courseId;
  const notify = useNotify();
  const [draft, setDraft] = useState<{ selected: string[]; lecturerProvision: boolean } | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, reload } = useResource(
    () => courseWorkspacesClient.getSettings({ courseId }),
    [courseId],
  );

  const stored = useMemo(
    () => ({
      selected: (data?.templates ?? []).map((t) => t.template_name),
      lecturerProvision: data?.lecturer_provision_enabled ?? false,
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

  async function save() {
    setSaving(true);
    try {
      await courseWorkspacesClient.updateSettings({
        courseId,
        body: {
          template_names: form.selected,
          lecturer_provision_enabled: form.lecturerProvision,
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
        <ScrollArea className="space-y-6 pr-1">
          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Allowed templates</h2>
              <p className="text-sm text-gray-500 mt-1">
                Members of this course can launch the checked templates from the course page —
                no global workspace role needed. Globally disabled templates stay associated
                but are hidden from students until re-enabled.
              </p>
            </div>

            {pickerItems.length === 0 ? (
              <p className="text-sm text-gray-500">
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
                          : 'border-gray-200 bg-white hover:border-gray-300'
                      }`}
                    >
                      <TemplateIcon template={{ icon: item.icon, name: item.name }} />
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-gray-900">
                          {item.display_name || item.name}
                        </span>
                        <span className="mt-0.5 block text-xs text-gray-500">{item.name}</span>
                        {item.description && (
                          <span className="mt-0.5 block text-xs text-gray-500">{item.description}</span>
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

          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-3">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={form.lecturerProvision}
                onChange={(event) => setDraft({ ...form, lecturerProvision: event.target.checked })}
                className="mt-0.5"
              />
              <span>
                <span className="block text-sm font-medium text-gray-900">
                  Lecturer provisioning
                </span>
                <span className="block text-xs text-gray-500">
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

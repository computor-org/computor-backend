'use client';

import { Suspense, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls, readOnlyInputCls } from '@/src/components/ui/tokens';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';
import { CoderClient } from '@/src/clients/CoderClient';
import type { TemplateCatalogEntry } from '@/src/types/workspaces';

const coderClient = new CoderClient();

// Mirrors templates_fs.TEMPLATE_KEY_RE / TEMPLATE_KEY_MAX_LEN so the form can
// explain a bad key before submitting; the server remains the gate.
const KEY_RE = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;
const KEY_MAX_LEN = 22;

function keyProblem(key: string): string | null {
  if (!key) return null;
  if (key.length > KEY_MAX_LEN) return `At most ${KEY_MAX_LEN} characters.`;
  if (!KEY_RE.test(key)) return 'Lowercase letters, digits and inner hyphens only.';
  if (key.endsWith('-workspace')) return "Leave out '-workspace' — it is added automatically.";
  return null;
}

type SourceEntry = TemplateCatalogEntry & { dir_name: string };

/**
 * New template = a copy of an existing one. The user picks a source and a key;
 * the Coder name and image name are derived from the key (shown read-only),
 * and the display fields start out as the source's until edited.
 */
function CreateInner() {
  const router = useRouter();
  const notify = useNotify();
  const fromParam = useSearchParam('from');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isWorkspaceMaintainer } = usePermissions();

  const { data, loading, error: loadError } = useResource(
    () => coderClient.listTemplateCatalog(),
    [],
    { enabled: isWorkspaceMaintainer },
  );
  // Only a template with a directory here can be copied.
  const sources = useMemo<SourceEntry[]>(
    () => (data?.templates ?? []).filter((t): t is SourceEntry => Boolean(t.dir_name)),
    [data],
  );

  // Overlay pattern (no effects): the pick wins, else ?from=, else the first.
  const [sourceChoice, setSourceChoice] = useState<string | null>(null);
  const source =
    sources.find((t) => t.dir_name === (sourceChoice ?? fromParam)) ?? sources[0] ?? null;

  const [key, setKey] = useState('');
  // null = "follow the source"; a string once the user has typed.
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [description, setDescription] = useState<string | null>(null);
  const [icon, setIcon] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const displayNameValue =
    displayName ?? (source ? `${source.display_name || source.name} (copy)` : '');
  const descriptionValue = description ?? source?.description ?? '';
  const iconValue = icon ?? source?.icon ?? '';
  const problem = keyProblem(key);
  const coderName = key ? `${key}-workspace` : '';
  const imageName = key ? `computor-workspace-${key}` : '';
  const canSubmit =
    source !== null && key.length > 0 && problem === null && displayNameValue.trim().length > 0;

  async function save() {
    if (!source) return;
    setSaving(true);
    setError(null);
    try {
      const created = await coderClient.cloneTemplate({
        body: {
          source: source.dir_name,
          key,
          display_name: displayNameValue.trim(),
          description: descriptionValue.trim() || null,
          icon: iconValue.trim() || null,
        },
      });
      notify('Template created. Deploy it from the Templates tab to build its image.', 'success');
      router.push(
        `/workspaces/admin/templates/${encodeURIComponent(created.template_name)}?tab=details`,
      );
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !isWorkspaceMaintainer) {
    return (
      <Forbidden
        message="Template administration requires the workspace maintainer role."
        backLink="/workspaces"
        backText="Back to workspaces"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspaces' },
          { label: 'Administration', href: '/workspaces/admin?tab=templates' },
          { label: 'New template' },
        ]}
        title="New workspace template"
        description="Copies an existing template — Terraform, Dockerfile, payload and limits — into an independent template you can edit and deploy. It lives only in this deployment's templates directory and is never overwritten by the repository sync."
        error={error ?? loadError}
        submitting={saving}
        disabled={!canSubmit || loading}
        submitLabel="Create template"
        onCancel={() => router.push('/workspaces/admin?tab=templates')}
        onSubmit={save}
      >
        <Field
          label="Copy from"
          required
          hint="The template whose files, Dockerfile and settings the new one starts from."
        >
          <select
            value={source?.dir_name ?? ''}
            onChange={(e) => setSourceChoice(e.target.value)}
            className={inputCls}
            disabled={loading || sources.length === 0}
          >
            {sources.length === 0 && (
              <option value="">
                {loading ? 'Loading templates…' : 'No template directories available'}
              </option>
            )}
            {sources.map((t) => (
              <option key={t.dir_name} value={t.dir_name}>
                {t.display_name || t.name} ({t.dir_name})
              </option>
            ))}
          </select>
        </Field>

        <Field
          label="Key"
          required
          hint={
            problem ??
            `Directory name of the new template: up to ${KEY_MAX_LEN} lowercase letters, digits and inner hyphens, e.g. python-ds. The Coder name and image name are derived from it.`
          }
        >
          <input
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="python-ds"
            className={`${inputCls} font-mono`}
            spellCheck={false}
            autoComplete="off"
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Directory">
            <input
              value={key || '—'}
              readOnly
              tabIndex={-1}
              className={`${readOnlyInputCls} font-mono`}
            />
          </Field>
          <Field label="Coder template name">
            <input
              value={coderName || '—'}
              readOnly
              tabIndex={-1}
              className={`${readOnlyInputCls} font-mono`}
            />
          </Field>
          <Field label="Image">
            <input
              value={imageName || '—'}
              readOnly
              tabIndex={-1}
              className={`${readOnlyInputCls} font-mono`}
            />
          </Field>
        </div>

        <Field label="Display name" required hint="What users see on the workspace cards.">
          <input
            value={displayNameValue}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={64}
            className={inputCls}
          />
        </Field>

        <Field label="Description">
          <textarea
            value={descriptionValue}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            maxLength={127}
            className={inputCls}
          />
        </Field>

        {/* Hand-rolled label: Field wires one control, and this row is a
            preview plus an input. Wrapper owns the width — inputCls is w-full. */}
        <div>
          <label htmlFor="tpl-icon" className="block text-xs font-medium text-body mb-1">
            Icon
          </label>
          <div className="flex items-center gap-3">
            <TemplateIcon template={{ icon: iconValue, name: coderName || 'workspace' }} size="sm" />
            <div className="flex-1 min-w-0">
              <input
                id="tpl-icon"
                value={iconValue}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="https://…/icon.svg"
                maxLength={255}
                className={inputCls}
                spellCheck={false}
              />
            </div>
          </div>
          <p className="mt-1 text-xs text-subtle">
            An https:// image URL, or one of Coder&apos;s built-in /icon/&lt;name&gt;.svg paths.
            Empty uses the default glyph.
          </p>
        </div>
      </FormPanel>
    </AuthenticatedLayout>
  );
}

export default function TemplateCreatePage() {
  return (
    <Suspense
      fallback={
        <AuthenticatedLayout>
          <PageLoading />
        </AuthenticatedLayout>
      }
    >
      <CreateInner />
    </Suspense>
  );
}

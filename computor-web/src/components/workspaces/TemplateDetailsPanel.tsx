'use client';

import { useState } from 'react';
import { ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { inputCls, readOnlyInputCls } from '@/src/components/ui/tokens';
import { CoderClient } from '@/src/clients/CoderClient';
import TemplateIcon from './TemplateIcon';

const coderClient = new CoderClient();

interface FormState {
  displayName: string;
  description: string;
  icon: string;
}

/**
 * Display name, description and icon — the template's manifest, not a DB row.
 * Saving writes template.json (what the next push reads) and patches the live
 * Coder template so the change shows without a rebuild. On a repo-managed
 * template that write detaches it from repo syncing, so it asks first.
 */
export default function TemplateDetailsPanel({
  templateName,
  onSaved,
}: {
  templateName: string;
  onSaved?: () => void;
}) {
  const notify = useNotify();
  const [draft, setDraft] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmSave, setConfirmSave] = useState(false);

  const { data, loading, error, reload } = useResource(
    () => coderClient.getTemplateMetadata({ templateName }),
    [templateName],
  );

  // Overlay pattern: `stored` is derived from the fetch, `draft` holds local
  // edits (no effect syncing server state into local state).
  const stored: FormState = {
    displayName: data?.display_name ?? '',
    description: data?.description ?? '',
    icon: data?.icon ?? '',
  };
  const form = draft ?? stored;
  const dirty =
    draft !== null &&
    (draft.displayName !== stored.displayName ||
      draft.description !== stored.description ||
      draft.icon !== stored.icon);

  function update(changes: Partial<FormState>) {
    setDraft({ ...form, ...changes });
  }

  async function save() {
    setSaving(true);
    try {
      const response = await coderClient.updateTemplateMetadata({
        templateName,
        body: {
          display_name: form.displayName.trim(),
          description: form.description.trim() || null,
          icon: form.icon.trim() || null,
        },
      });
      notify(response.message, response.coder_updated ? 'success' : 'info');
      setDraft(null);
      await reload();
      onSaved?.();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to save details', 'error');
    } finally {
      setSaving(false);
    }
  }

  function requestSave() {
    if (!form.displayName.trim()) {
      notify('Display name must not be empty.', 'error');
      return;
    }
    // A repo-managed template detaches from syncing on its first write; a
    // clone (never synced) or an already-customized one needs no warning.
    if (data && !data.customized && !data.cloned_from) setConfirmSave(true);
    else void save();
  }

  if (loading) return <ListLoading>Loading template details…</ListLoading>;

  const created = data?.created_at ? new Date(data.created_at) : null;
  const identityName = data?.template_name ?? templateName;

  return (
    // Same arrangement as the settings tab: the cards scroll, Save does not.
    <div className="flex h-full min-h-0 flex-col gap-4">
      <ErrorBanner>{error}</ErrorBanner>

      <div className="flex-1 min-h-0 overflow-y-auto scroll-slim scroll-gutter space-y-4">
        <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-fg">Identity</h2>
              <p className="text-sm text-muted mt-1">
                Fixed at creation. The Coder name is what workspaces, settings and course
                assignments are keyed by; the image is what a build produces.
              </p>
            </div>
            {data &&
              (data.cloned_from ? (
                <Badge tone="info" title="Created here; the repository sync never touches it">
                  cloned from {data.cloned_from}
                </Badge>
              ) : (
                <Badge tone={data.customized ? 'warning' : 'success'}>
                  {data.customized ? 'customized' : 'managed'}
                </Badge>
              ))}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="tpl-coder-name" className="block text-xs font-medium text-body mb-1">
                Coder template name
              </label>
              <input
                id="tpl-coder-name"
                value={identityName}
                readOnly
                tabIndex={-1}
                className={`${readOnlyInputCls} font-mono`}
              />
            </div>
            <div>
              <label htmlFor="tpl-dir" className="block text-xs font-medium text-body mb-1">
                Directory
              </label>
              <input
                id="tpl-dir"
                value={data?.dir_name ?? ''}
                readOnly
                tabIndex={-1}
                className={`${readOnlyInputCls} font-mono`}
              />
            </div>
            <div>
              <label htmlFor="tpl-image" className="block text-xs font-medium text-body mb-1">
                Image
              </label>
              <input
                id="tpl-image"
                value={data?.image_name ?? '—'}
                readOnly
                tabIndex={-1}
                className={`${readOnlyInputCls} font-mono`}
              />
            </div>
          </div>

          {data?.cloned_from && (
            <p className="text-xs text-muted">
              Created from <span className="font-mono">{data.cloned_from}</span>
              {created && !Number.isNaN(created.getTime()) && ` on ${created.toLocaleString()}`}.
              Lives only in this deployment&apos;s templates directory; the repository sync never
              touches it.
            </p>
          )}
        </div>

        <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-fg">Display</h2>
            <p className="text-sm text-muted mt-1">
              What users see on the workspace cards. Saved to the template&apos;s manifest and
              applied to Coder right away when the template is deployed — no rebuild needed.
            </p>
          </div>

          <div>
            <label htmlFor="tpl-display-name" className="block text-xs font-medium text-body mb-1">
              Display name
            </label>
            <input
              id="tpl-display-name"
              value={form.displayName}
              onChange={(event) => update({ displayName: event.target.value })}
              maxLength={64}
              className={inputCls}
            />
          </div>

          <div>
            <label htmlFor="tpl-description" className="block text-xs font-medium text-body mb-1">
              Description
            </label>
            <textarea
              id="tpl-description"
              value={form.description}
              onChange={(event) => update({ description: event.target.value })}
              rows={2}
              maxLength={127}
              className={inputCls}
            />
          </div>

          <div>
            <label htmlFor="tpl-icon" className="block text-xs font-medium text-body mb-1">
              Icon
            </label>
            {/* Wrapper owns the width: inputCls is w-full. */}
            <div className="flex items-center gap-3">
              <TemplateIcon template={{ icon: form.icon, name: identityName }} size="sm" />
              <div className="flex-1 min-w-0">
                <input
                  id="tpl-icon"
                  value={form.icon}
                  onChange={(event) => update({ icon: event.target.value })}
                  placeholder="https://…/icon.svg"
                  maxLength={255}
                  className={inputCls}
                  spellCheck={false}
                />
              </div>
            </div>
            <p className="text-xs text-muted mt-1">
              An https:// image URL, or one of Coder&apos;s built-in /icon/&lt;name&gt;.svg paths.
              Empty uses the default glyph.
            </p>
          </div>
        </div>
      </div>

      <div className="shrink-0 flex flex-wrap items-center gap-3 border-t border-rule pt-4">
        <Button onClick={requestSave} disabled={!dirty} loading={saving} loadingLabel="Saving…">
          Save details
        </Button>
        {draft && (
          <Button variant="ghost" onClick={() => setDraft(null)} disabled={saving}>
            Discard changes
          </Button>
        )}
      </div>

      {confirmSave && (
        <ConfirmDialog
          open={confirmSave}
          title="Customize this template?"
          message={
            'Saving marks the template as operator-customized: it will no longer be ' +
            'updated automatically from the repository on system restarts (until you ' +
            'restore it to managed). Continue?'
          }
          confirmLabel="Save & customize"
          onConfirm={() => {
            setConfirmSave(false);
            void save();
          }}
          onCancel={() => setConfirmSave(false)}
        />
      )}
    </div>
  );
}

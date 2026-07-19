'use client';

import { useState } from 'react';
import { ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { inputCls } from '@/src/components/ui/tokens';
import { CoderClient } from '@/src/clients/CoderClient';
import type { TemplateVariable } from '@/src/types/workspaces';

const coderClient = new CoderClient();

function defaultToString(variable: TemplateVariable): string {
  const value = variable.default;
  if (value == null) return '';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/** Guided editor: rewrites variable defaults in the template's .tf files. */
export default function TemplateVariablesPanel({ templateName }: { templateName: string }) {
  const notify = useNotify();
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const { data, loading, error, setData } = useResource(
    () => coderClient.getTemplateVariables({ templateName }),
    [templateName],
  );

  const variables = data?.variables ?? [];
  const dirty = variables.filter(
    (variable) =>
      edited[variable.name] !== undefined && edited[variable.name] !== defaultToString(variable),
  );

  async function save() {
    setSaving(true);
    try {
      const defaults = Object.fromEntries(
        dirty.map((variable) => [variable.name, edited[variable.name]]),
      );
      const response = await coderClient.updateTemplateVariables({ templateName, defaults });
      setData(response);
      setEdited({});
      notify('Variable defaults saved. Push the template to apply them.', 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to save variables', 'error');
    } finally {
      setSaving(false);
    }
  }

  function requestSave() {
    if (dirty.length === 0) return;
    // First edit of a managed template flips it to operator-customized —
    // make that consequence explicit before writing.
    if (data && !data.customized) setConfirmOpen(true);
    else void save();
  }

  if (loading) return <ListLoading>Loading variables…</ListLoading>;

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 bg-white rounded-lg border border-gray-200 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Terraform variables</h2>
            <p className="text-sm text-gray-500 mt-1">
              Defaults declared in the template&apos;s .tf files. Locked variables are supplied
              by the push pipeline or the settings tab — their file defaults never apply.
            </p>
          </div>
          {data && (
            <Badge color={data.customized ? 'yellow' : 'green'}>
              {data.customized ? 'customized' : 'managed'}
            </Badge>
          )}
        </div>

        <div className="space-y-3">
          {variables.map((variable) => {
            const locked = variable.managed || variable.sensitive;
            const value = edited[variable.name] ?? defaultToString(variable);
            const isDirty = dirty.some((item) => item.name === variable.name);
            return (
              <div
                key={variable.name}
                className="grid gap-2 sm:grid-cols-[minmax(14rem,1fr)_minmax(0,2fr)] sm:items-start border-b border-gray-100 pb-3 last:border-b-0 last:pb-0"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-gray-900">{variable.name}</span>
                    {isDirty && <span className="text-amber-600" title="Unsaved change">•</span>}
                    {variable.sensitive && <Badge color="red">sensitive</Badge>}
                    {variable.managed && (
                      <Badge color="gray">locked</Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {variable.type || 'untyped'} · {variable.file}
                  </p>
                </div>
                <div>
                  <input
                    value={locked ? defaultToString(variable) : value}
                    onChange={(event) =>
                      setEdited((previous) => ({ ...previous, [variable.name]: event.target.value }))
                    }
                    disabled={locked || saving}
                    placeholder={
                      variable.sensitive
                        ? '(masked)'
                        : variable.has_default
                          ? undefined
                          : '(no default — supplied at push)'
                    }
                    className={`${inputCls} font-mono ${locked ? 'bg-gray-50 text-gray-400' : ''}`}
                    aria-label={`Default for ${variable.name}`}
                    title={variable.managed_reason || undefined}
                  />
                  {variable.description && (
                    <p className="text-xs text-gray-500 mt-1">{variable.description}</p>
                  )}
                  {variable.managed_reason && (
                    <p className="text-xs text-gray-400 mt-1">Locked: {variable.managed_reason}.</p>
                  )}
                </div>
              </div>
            );
          })}
          {variables.length === 0 && (
            <p className="text-sm text-gray-500">No variables declared.</p>
          )}
        </div>
      </div>

      <div className="shrink-0 flex items-center gap-3">
        <Button onClick={requestSave} disabled={dirty.length === 0} loading={saving} loadingLabel="Saving…">
          Save {dirty.length > 0 ? `${dirty.length} change${dirty.length === 1 ? '' : 's'}` : 'changes'}
        </Button>
        {Object.keys(edited).length > 0 && (
          <Button variant="ghost" onClick={() => setEdited({})} disabled={saving}>
            Discard changes
          </Button>
        )}
        <span className="text-xs text-gray-500">
          Changes take effect after the next template push (Fleet tab).
        </span>
      </div>

      {confirmOpen && (
        <ConfirmDialog
          open={confirmOpen}
          title="Customize this template?"
          message={
            'Saving marks the template as operator-customized: it will no longer be ' +
            'updated automatically from the repository on system restarts (until you ' +
            'restore it to managed). Continue?'
          }
          confirmLabel="Save & customize"
          onConfirm={() => {
            setConfirmOpen(false);
            void save();
          }}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </>
  );
}

'use client';

import { useMemo, useState } from 'react';
import { ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import { CoderClient } from '@/src/clients/CoderClient';

const coderClient = new CoderClient();

interface VariableRow {
  name: string;
  value: string;
}

interface FormState {
  memoryMb: string;
  cpuShares: string;
  maxRunning: string;
  variables: VariableRow[];
}

/** '' → null, otherwise a non-negative integer (throws a user message). */
function parseLimit(label: string, raw: string): number | null {
  const text = raw.trim();
  if (!text) return null;
  const value = Number(text);
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative whole number.`);
  }
  return value;
}

/** DB-backed per-template limits, seat quota, and Terraform variable overrides. */
export default function TemplateSettingsPanel({ templateName }: { templateName: string }) {
  const notify = useNotify();
  const [draft, setDraft] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, reload } = useResource(
    () => coderClient.listTemplateSettings(),
    [templateName],
  );

  const stored = useMemo<FormState>(() => {
    const row = data?.settings.find((item) => item.template_name === templateName);
    return {
      memoryMb: row?.memory_mb ? String(row.memory_mb) : '',
      cpuShares: row?.cpu_shares ? String(row.cpu_shares) : '',
      maxRunning: row?.max_running_workspaces != null ? String(row.max_running_workspaces) : '',
      variables: Object.entries(row?.template_variables ?? {}).map(([name, value]) => ({ name, value })),
    };
  }, [data, templateName]);

  // Overlay pattern: `stored` is derived from the fetch, `draft` holds local
  // edits (avoids syncing server state into local state via effects).
  const form = draft ?? stored;

  function update(changes: Partial<FormState>) {
    setDraft({ ...form, ...changes });
  }

  async function save() {
    setSaving(true);
    try {
      const variables: Record<string, string> = {};
      for (const row of form.variables) {
        const name = row.name.trim();
        if (!name) continue;
        if (name in variables) throw new Error(`Duplicate variable name '${name}'.`);
        variables[name] = row.value;
      }
      await coderClient.updateTemplateSettings({
        templateName,
        body: {
          memory_mb: parseLimit('Memory cap', form.memoryMb),
          cpu_shares: parseLimit('CPU shares', form.cpuShares),
          max_running_workspaces: parseLimit('Max running workspaces', form.maxRunning),
          template_variables: variables,
        },
      });
      notify('Settings saved. Limits and overrides apply at the next template push; the seat quota applies immediately.', 'success');
      setDraft(null);
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <ListLoading>Loading settings…</ListLoading>;

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 bg-white rounded-lg border border-gray-200 p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Resource limits &amp; seats</h2>
          <p className="text-sm text-gray-500 mt-1">
            Container limits are pushed as Terraform variables with the next{' '}
            <span className="font-medium">Build &amp; push</span> and take effect as workspaces
            restart onto the new version. The seat quota is enforced immediately on
            provision/start — for everyone, admins included.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="tpl-memory" className="block text-xs font-medium text-gray-700 mb-1">
              Memory cap (MiB)
            </label>
            <input
              id="tpl-memory"
              value={form.memoryMb}
              onChange={(event) => update({ memoryMb: event.target.value })}
              placeholder="unlimited"
              inputMode="numeric"
              className={inputCls}
            />
            <p className="text-xs text-gray-500 mt-1">Empty or 0 = unlimited.</p>
          </div>
          <div>
            <label htmlFor="tpl-cpu" className="block text-xs font-medium text-gray-700 mb-1">
              CPU shares
            </label>
            <input
              id="tpl-cpu"
              value={form.cpuShares}
              onChange={(event) => update({ cpuShares: event.target.value })}
              placeholder="Docker default"
              inputMode="numeric"
              className={inputCls}
            />
            <p className="text-xs text-gray-500 mt-1">
              Relative weight (default 1024); empty or 0 keeps the Docker default.
            </p>
          </div>
          <div>
            <label htmlFor="tpl-seats" className="block text-xs font-medium text-gray-700 mb-1">
              Max running workspaces
            </label>
            <input
              id="tpl-seats"
              value={form.maxRunning}
              onChange={(event) => update({ maxRunning: event.target.value })}
              placeholder="unlimited"
              inputMode="numeric"
              className={inputCls}
            />
            <p className="text-xs text-gray-500 mt-1">
              Across all users (e.g. license seats); 0 freezes the template.
            </p>
          </div>
        </div>
      </div>

      <div className="shrink-0 bg-white rounded-lg border border-gray-200 p-5 space-y-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Terraform variable overrides</h2>
          <p className="text-sm text-gray-500 mt-1">
            Pushed as <code className="font-mono text-xs">--variable name=value</code> — they
            override the file defaults without customizing the template files. Only variables
            the template declares are applied.
          </p>
        </div>

        {form.variables.map((row, index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              value={row.name}
              onChange={(event) => {
                const variables = form.variables.slice();
                variables[index] = { ...row, name: event.target.value };
                update({ variables });
              }}
              placeholder="variable name (e.g. shm_size)"
              className={`${inputCls} w-64 font-mono`}
              aria-label={`Variable ${index + 1} name`}
            />
            <input
              value={row.value}
              onChange={(event) => {
                const variables = form.variables.slice();
                variables[index] = { ...row, value: event.target.value };
                update({ variables });
              }}
              placeholder="value"
              className={`${inputCls} flex-1 font-mono`}
              aria-label={`Variable ${index + 1} value`}
            />
            <Button
              size="xs"
              variant="dangerGhost"
              onClick={() => update({ variables: form.variables.filter((_, i) => i !== index) })}
            >
              Remove
            </Button>
          </div>
        ))}

        <Button
          size="xs"
          variant="ghost"
          onClick={() => update({ variables: [...form.variables, { name: '', value: '' }] })}
        >
          + Add variable
        </Button>
      </div>

      <div className="shrink-0 flex items-center gap-3">
        <Button onClick={save} loading={saving} loadingLabel="Saving…">
          Save settings
        </Button>
        {draft && (
          <Button variant="ghost" onClick={() => setDraft(null)} disabled={saving}>
            Discard changes
          </Button>
        )}
      </div>
    </>
  );
}

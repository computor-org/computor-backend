'use client';

import { useMemo, useState } from 'react';
import { ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import { CoderClient } from '@/src/clients/CoderClient';
import type { TemplateVariable } from '@/src/types/workspaces';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const coderClient = new CoderClient();

const COPY = {
  de: {
    notWhole: (label: string) => `${label} muss eine nicht negative ganze Zahl sein.`,
    duplicate: (name: string) => `Doppelter Variablenname „${name}“.`,
    memoryCap: 'Speicherlimit',
    cpuShares: 'CPU-Anteile',
    maxRunning: 'Max. laufende Arbeitsumgebungen',
    saved:
      'Einstellungen gespeichert. Limits und Überschreibungen gelten ab dem nächsten Push der Vorlage, das Platzkontingent gilt sofort.',
    saveFailed: 'Einstellungen konnten nicht gespeichert werden',
    loading: 'Einstellungen werden geladen …',
    limitsTitle: 'Ressourcenlimits & Plätze',
    limitsHint1: 'Container-Limits werden mit dem nächsten ',
    buildPush: 'Build & Push',
    limitsHint2:
      ' als Terraform-Variablen übertragen und wirken, sobald Arbeitsumgebungen auf der neuen Version neu starten. Das Platzkontingent wird beim Bereitstellen und Starten sofort durchgesetzt – für alle, auch für Administrierende.',
    enabled: 'Aktiviert',
    enabledHint:
      'Deaktivierte Vorlagen sind für Nutzende und Kurse ausgeblendet und lassen sich nicht bereitstellen; bestehende Arbeitsumgebungen laufen und starten weiter.',
    memoryLabel: 'Speicherlimit (MiB)',
    unlimited: 'unbegrenzt',
    memoryHint: 'Leer oder 0 = unbegrenzt.',
    cpuPlaceholder: 'Docker-Standard',
    cpuHint: 'Relatives Gewicht (Standard 1024); leer oder 0 behält den Docker-Standard.',
    seatsHint: 'Über alle Nutzenden hinweg (z. B. Lizenzplätze); 0 friert die Vorlage ein.',
    policyTitle: 'Root- & Internetrichtlinie',
    policyHint1:
      'Die Obergrenze für jede Arbeitsumgebung dieser Vorlage. Ein Kurs kann diese Rechte weiter einschränken, aber nie gewähren, was hier ausgeschaltet ist. Gilt mit dem nächsten ',
    policyHint2: ' und für jede Arbeitsumgebung beim nächsten Neustart.',
    rootTitle: 'Root-Zugriff (sudo)',
    rootOff1: 'Aus startet den Container mit ',
    rootOff2: ', sodass ',
    rootOff3: ' und ',
    rootOff4:
      ' vom Kernel abgelehnt werden, obwohl das Image sie enthält. Nutzende können dann keine Systempakete mehr installieren – auch nicht über ein ',
    rootOff5: '-Skript.',
    internetTitle: 'Internetzugang',
    internetHint:
      'Aus verlegt die Arbeitsumgebung in ein isoliertes Netzwerk ohne Route nach außen: Die Computor-API und Git bleiben erreichbar, alles Externe schlägt sofort fehl. Paketinstallationen über PyPI, npm oder apt funktionieren dann nicht mehr.',
    varsTitle: 'Überschreibungen von Terraform-Variablen',
    varsHint1: 'Werden als ',
    varsHint2:
      ' übertragen – sie überschreiben die Standardwerte der Vorlage, ohne ihre Dateien anzupassen. Leere Werte werden beim Push ignoriert.',
    varNamePlaceholder: 'Variablenname (z. B. shm_size)',
    varName: (n: number) => `Name der Variable ${n}`,
    valuePlaceholder: 'Wert',
    varValue: (n: number) => `Wert der Variable ${n}`,
    remove: 'Entfernen',
    noVars: 'Diese Vorlage deklariert keine überschreibbaren Variablen.',
    pick: 'Von der Vorlage deklariert – wähle eine aus, um ihren Standardwert zu überschreiben:',
    untyped: 'ohne Typ',
    defaultVal: (v: string) => ` · Standard: ${v}`,
    loadingVars: 'Deklarierte Variablen werden geladen …',
    varsLoadFailed:
      'Die deklarierten Variablen der Vorlage konnten nicht geladen werden – gib die Namen manuell ein.',
    addVar: '+ Variable hinzufügen',
    saving: 'Wird gespeichert …',
    save: 'Einstellungen speichern',
    discard: 'Änderungen verwerfen',
  },
  en: {
    notWhole: (label: string) => `${label} must be a non-negative whole number.`,
    duplicate: (name: string) => `Duplicate variable name '${name}'.`,
    memoryCap: 'Memory cap',
    cpuShares: 'CPU shares',
    maxRunning: 'Max running workspaces',
    saved:
      'Settings saved. Limits and overrides apply at the next template push; the seat quota applies immediately.',
    saveFailed: 'Failed to save settings',
    loading: 'Loading settings…',
    limitsTitle: 'Resource limits & seats',
    limitsHint1: 'Container limits are pushed as Terraform variables with the next ',
    buildPush: 'Build & push',
    limitsHint2:
      ' and take effect as workspaces restart onto the new version. The seat quota is enforced immediately on provision/start — for everyone, admins included.',
    enabled: 'Enabled',
    enabledHint:
      'Disabled templates are hidden from users and courses and cannot be provisioned; existing workspaces keep running and starting.',
    memoryLabel: 'Memory cap (MiB)',
    unlimited: 'unlimited',
    memoryHint: 'Empty or 0 = unlimited.',
    cpuPlaceholder: 'Docker default',
    cpuHint: 'Relative weight (default 1024); empty or 0 keeps the Docker default.',
    seatsHint: 'Across all users (e.g. license seats); 0 freezes the template.',
    policyTitle: 'Root & internet policy',
    policyHint1:
      'The ceiling for every workspace of this template. A course can restrict these further but can never grant what is switched off here. Applied with the next ',
    policyHint2: ', and to each workspace when it next restarts.',
    rootTitle: 'Root access (sudo)',
    rootOff1: 'Off runs the container with ',
    rootOff2: ', so ',
    rootOff3: ' and ',
    rootOff4:
      ' are refused by the kernel even though the image ships them. Users can no longer install system packages — including from a ',
    rootOff5: ' script.',
    internetTitle: 'Internet access',
    internetHint:
      'Off moves the workspace to an isolated network with no route out: the Computor API and git stay reachable, everything external fails immediately. Package installs from PyPI, npm or apt stop working.',
    varsTitle: 'Terraform variable overrides',
    varsHint1: 'Pushed as ',
    varsHint2:
      " — they override the template's defaults without customizing its files. Empty values are ignored at push.",
    varNamePlaceholder: 'variable name (e.g. shm_size)',
    varName: (n: number) => `Variable ${n} name`,
    valuePlaceholder: 'value',
    varValue: (n: number) => `Variable ${n} value`,
    remove: 'Remove',
    noVars: 'This template declares no overridable variables.',
    pick: 'Declared by the template — pick one to override its default:',
    untyped: 'untyped',
    defaultVal: (v: string) => ` · default: ${v}`,
    loadingVars: 'Loading declared variables…',
    varsLoadFailed:
      "Could not load the template's declared variables — enter names manually.",
    addVar: '+ Add variable',
    saving: 'Saving…',
    save: 'Save settings',
    discard: 'Discard changes',
  },
};

interface VariableRow {
  name: string;
  value: string;
}

interface FormState {
  enabled: boolean;
  memoryMb: string;
  cpuShares: string;
  maxRunning: string;
  allowRoot: boolean;
  allowInternet: boolean;
  variables: VariableRow[];
}

function defaultToString(variable: TemplateVariable): string {
  const value = variable.default;
  if (value == null) return '';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/** '' → null, otherwise a non-negative integer (throws a user message). */
function parseLimit(label: string, raw: string, message: (label: string) => string): number | null {
  const text = raw.trim();
  if (!text) return null;
  const value = Number(text);
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(message(label));
  }
  return value;
}

/** DB-backed per-template limits, seat quota, and Terraform variable overrides. */
export default function TemplateSettingsPanel({ templateName }: { templateName: string }) {
  const notify = useNotify();
  const language = useUiLanguage();
  const t = COPY[language];
  const [draft, setDraft] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, reload } = useResource(
    () => coderClient.listTemplateSettings(),
    [templateName],
  );

  // Declared template variables feed the override pick-list; the backend
  // already flags deployment-owned ones (push pipeline, env, infra wiring)
  // as managed, so only genuine capability knobs are offered.
  const {
    data: declaredData,
    loading: declaredLoading,
    error: declaredError,
  } = useResource(() => coderClient.getTemplateVariables({ templateName }), [templateName]);

  const stored = useMemo<FormState>(() => {
    const row = data?.settings.find((item) => item.template_name === templateName);
    return {
      enabled: row?.enabled ?? true,
      memoryMb: row?.memory_mb ? String(row.memory_mb) : '',
      cpuShares: row?.cpu_shares ? String(row.cpu_shares) : '',
      maxRunning: row?.max_running_workspaces != null ? String(row.max_running_workspaces) : '',
      // Defaults mirror the templates' own Terraform variable defaults, so a
      // template without a settings row shows what it actually does.
      allowRoot: row?.allow_root ?? false,
      allowInternet: row?.allow_internet ?? true,
      variables: Object.entries(row?.template_variables ?? {}).map(([name, value]) => ({ name, value })),
    };
  }, [data, templateName]);

  // Overlay pattern: `stored` is derived from the fetch, `draft` holds local
  // edits (avoids syncing server state into local state via effects).
  const form = draft ?? stored;

  const takenNames = new Set(form.variables.map((row) => row.name.trim()));
  const addable = (declaredData?.variables ?? []).filter(
    (variable) => !variable.managed && !variable.sensitive && !takenNames.has(variable.name),
  );

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
        if (name in variables) throw new Error(t.duplicate(name));
        variables[name] = row.value;
      }
      await coderClient.updateTemplateSettings({
        templateName,
        body: {
          enabled: form.enabled,
          memory_mb: parseLimit(t.memoryCap, form.memoryMb, t.notWhole),
          cpu_shares: parseLimit(t.cpuShares, form.cpuShares, t.notWhole),
          max_running_workspaces: parseLimit(t.maxRunning, form.maxRunning, t.notWhole),
          allow_root: form.allowRoot,
          allow_internet: form.allowInternet,
          template_variables: variables,
        },
      });
      notify(t.saved, 'success');
      setDraft(null);
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.saveFailed, 'error');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <ListLoading>{t.loading}</ListLoading>;

  return (
    // Fills the page: the settings cards scroll, "Save settings" does not. It
    // used to be the last child of a page-length scroll, so on a template with
    // several Terraform variables you had to scroll to the bottom to commit a
    // change you made at the top.
    <div className="flex h-full min-h-0 flex-col gap-4">
      <ErrorBanner>{error}</ErrorBanner>

      <div className="flex-1 min-h-0 overflow-y-auto scroll-slim scroll-gutter space-y-4">
      <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-fg">{t.limitsTitle}</h2>
          <p className="text-sm text-muted mt-1">
            {t.limitsHint1}
            <span className="font-medium">{t.buildPush}</span>
            {t.limitsHint2}
          </p>
        </div>

        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(event) => update({ enabled: event.target.checked })}
            className="mt-0.5"
          />
          <span>
            <span className="block text-sm font-medium text-fg">{t.enabled}</span>
            <span className="block text-xs text-muted">
              {t.enabledHint}
            </span>
          </span>
        </label>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="tpl-memory" className="block text-xs font-medium text-body mb-1">
              {t.memoryLabel}
            </label>
            <input
              id="tpl-memory"
              value={form.memoryMb}
              onChange={(event) => update({ memoryMb: event.target.value })}
              placeholder={t.unlimited}
              inputMode="numeric"
              className={inputCls}
            />
            <p className="text-xs text-muted mt-1">{t.memoryHint}</p>
          </div>
          <div>
            <label htmlFor="tpl-cpu" className="block text-xs font-medium text-body mb-1">
              {t.cpuShares}
            </label>
            <input
              id="tpl-cpu"
              value={form.cpuShares}
              onChange={(event) => update({ cpuShares: event.target.value })}
              placeholder={t.cpuPlaceholder}
              inputMode="numeric"
              className={inputCls}
            />
            <p className="text-xs text-muted mt-1">{t.cpuHint}</p>
          </div>
          <div>
            <label htmlFor="tpl-seats" className="block text-xs font-medium text-body mb-1">
              {t.maxRunning}
            </label>
            <input
              id="tpl-seats"
              value={form.maxRunning}
              onChange={(event) => update({ maxRunning: event.target.value })}
              placeholder={t.unlimited}
              inputMode="numeric"
              className={inputCls}
            />
            <p className="text-xs text-muted mt-1">{t.seatsHint}</p>
          </div>
        </div>
      </div>

      <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-fg">{t.policyTitle}</h2>
          <p className="text-sm text-muted mt-1">
            {t.policyHint1}
            <span className="font-medium">{t.buildPush}</span>
            {t.policyHint2}
          </p>
        </div>

        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={form.allowRoot}
            onChange={(event) => update({ allowRoot: event.target.checked })}
            className="mt-0.5"
          />
          <span>
            <span className="block text-sm font-medium text-fg">{t.rootTitle}</span>
            <span className="block text-xs text-muted">
              {t.rootOff1}<code className="font-mono">no-new-privileges</code>
              {t.rootOff2}<code className="font-mono">sudo</code>{t.rootOff3}<code className="font-mono">su</code>
              {t.rootOff4}<code className="font-mono">~/personalize</code>{t.rootOff5}
            </span>
          </span>
        </label>

        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={form.allowInternet}
            onChange={(event) => update({ allowInternet: event.target.checked })}
            className="mt-0.5"
          />
          <span>
            <span className="block text-sm font-medium text-fg">{t.internetTitle}</span>
            <span className="block text-xs text-muted">
              {t.internetHint}
            </span>
          </span>
        </label>
      </div>

      <div className="bg-surface rounded-lg border border-rule p-5 space-y-3">
        <div>
          <h2 className="text-lg font-semibold text-fg">{t.varsTitle}</h2>
          <p className="text-sm text-muted mt-1">
            {t.varsHint1}<code className="font-mono text-xs">--variable name=value</code>
            {t.varsHint2}
          </p>
        </div>

        {form.variables.map((row, index) => (
          <div key={index} className="flex items-center gap-2">
            {/* Wrappers own the widths: inputCls carries w-full, which would
                otherwise fight the sizing classes and crush the value input. */}
            <div className="w-64 shrink-0">
              <input
                value={row.name}
                onChange={(event) => {
                  const variables = form.variables.slice();
                  variables[index] = { ...row, name: event.target.value };
                  update({ variables });
                }}
                placeholder={t.varNamePlaceholder}
                className={`${inputCls} font-mono`}
                aria-label={t.varName(index + 1)}
              />
            </div>
            <div className="flex-1 min-w-0">
              <input
                value={row.value}
                onChange={(event) => {
                  const variables = form.variables.slice();
                  variables[index] = { ...row, value: event.target.value };
                  update({ variables });
                }}
                placeholder={t.valuePlaceholder}
                className={`${inputCls} font-mono`}
                aria-label={t.varValue(index + 1)}
              />
            </div>
            <Button
              size="xs"
              variant="dangerGhost"
              onClick={() => update({ variables: form.variables.filter((_, i) => i !== index) })}
            >
              {t.remove}
            </Button>
          </div>
        ))}

        {form.variables.length === 0 && addable.length === 0 && !declaredLoading && !declaredError && (
          <p className="text-sm text-muted">{t.noVars}</p>
        )}

        {addable.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-body">
              {t.pick}
            </p>
            {addable.map((variable) => (
              <button
                key={variable.name}
                type="button"
                onClick={() =>
                  update({
                    variables: [
                      ...form.variables,
                      { name: variable.name, value: defaultToString(variable) },
                    ],
                  })
                }
                className="w-full text-left rounded border border-rule px-3 py-2 hover:border-accent-line hover:bg-accent-wash"
              >
                <span className="text-sm font-mono text-fg">+ {variable.name}</span>
                <span className="text-xs text-muted ml-2">
                  {variable.type || t.untyped}
                  {variable.has_default && t.defaultVal(defaultToString(variable) || '""')}
                </span>
                {variable.description && (
                  <span className="block text-xs text-muted mt-0.5">{variable.description}</span>
                )}
              </button>
            ))}
          </div>
        )}

        {declaredLoading && (
          <p className="text-xs text-muted">{t.loadingVars}</p>
        )}

        {declaredError && (
          // Pick-list unavailable (e.g. templates dir not mounted) — fall back
          // to free-form entry so overrides stay manageable.
          <div className="space-y-2">
            <p className="text-xs text-muted">{t.varsLoadFailed}</p>
            <Button
              size="xs"
              variant="ghost"
              onClick={() => update({ variables: [...form.variables, { name: '', value: '' }] })}
            >
              {t.addVar}
            </Button>
          </div>
        )}
      </div>

      </div>

      <div className="shrink-0 flex flex-wrap items-center gap-3 border-t border-rule pt-4">
        <Button onClick={save} loading={saving} loadingLabel={t.saving}>
          {t.save}
        </Button>
        {draft && (
          <Button variant="ghost" onClick={() => setDraft(null)} disabled={saving}>
            {t.discard}
          </Button>
        )}
      </div>
    </div>
  );
}

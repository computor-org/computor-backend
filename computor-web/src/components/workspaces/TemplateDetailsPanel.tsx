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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';
import TemplateIcon from './TemplateIcon';

const coderClient = new CoderClient();

const COPY = {
  de: {
    saveFailed: 'Details konnten nicht gespeichert werden',
    nameEmpty: 'Der Anzeigename darf nicht leer sein.',
    loading: 'Vorlagendetails werden geladen …',
    identity: 'Identität',
    identityHint:
      'Wird bei der Erstellung festgelegt. Der Coder-Name ist der Schlüssel für Arbeitsumgebungen, Einstellungen und Kurszuweisungen, das Image ist das Ergebnis eines Builds.',
    clonedTitle: 'Hier erstellt; die Synchronisierung mit dem Repository fasst sie nie an',
    clonedFrom: (name: string) => `geklont von ${name}`,
    customized: 'angepasst',
    managed: 'verwaltet',
    coderName: 'Name der Coder-Vorlage',
    directory: 'Verzeichnis',
    image: 'Image',
    createdFrom: 'Erstellt aus',
    createdOn: (date: string) => ` am ${date}`,
    clonedNote:
      'Liegt nur im Vorlagenverzeichnis dieser Installation; die Synchronisierung mit dem Repository fasst sie nie an.',
    display: 'Anzeige',
    displayHint:
      'Das sehen Nutzende auf den Karten der Arbeitsumgebungen. Wird im Manifest der Vorlage gespeichert und sofort auf Coder angewendet, sobald die Vorlage bereitgestellt ist – ein Rebuild ist nicht nötig.',
    displayName: 'Anzeigename',
    description: 'Beschreibung',
    icon: 'Symbol',
    iconHint:
      'Eine https://-Bild-URL oder einer der eingebauten Coder-Pfade /icon/<name>.svg. Leer verwendet das Standardsymbol.',
    saving: 'Wird gespeichert …',
    save: 'Details speichern',
    discard: 'Änderungen verwerfen',
    confirmTitle: 'Diese Vorlage anpassen?',
    confirmMessage:
      'Durch das Speichern gilt die Vorlage als vom Betrieb angepasst: Sie wird bei Neustarts des Systems nicht mehr automatisch aus dem Repository aktualisiert (bis du sie wieder auf „verwaltet“ zurücksetzt). Fortfahren?',
    confirmLabel: 'Speichern & anpassen',
  },
  en: {
    saveFailed: 'Failed to save details',
    nameEmpty: 'Display name must not be empty.',
    loading: 'Loading template details…',
    identity: 'Identity',
    identityHint:
      'Fixed at creation. The Coder name is what workspaces, settings and course assignments are keyed by; the image is what a build produces.',
    clonedTitle: 'Created here; the repository sync never touches it',
    clonedFrom: (name: string) => `cloned from ${name}`,
    customized: 'customized',
    managed: 'managed',
    coderName: 'Coder template name',
    directory: 'Directory',
    image: 'Image',
    createdFrom: 'Created from',
    createdOn: (date: string) => ` on ${date}`,
    clonedNote:
      "Lives only in this deployment's templates directory; the repository sync never touches it.",
    display: 'Display',
    displayHint:
      "What users see on the workspace cards. Saved to the template's manifest and applied to Coder right away when the template is deployed — no rebuild needed.",
    displayName: 'Display name',
    description: 'Description',
    icon: 'Icon',
    iconHint:
      "An https:// image URL, or one of Coder's built-in /icon/<name>.svg paths. Empty uses the default glyph.",
    saving: 'Saving…',
    save: 'Save details',
    discard: 'Discard changes',
    confirmTitle: 'Customize this template?',
    confirmMessage:
      'Saving marks the template as operator-customized: it will no longer be updated automatically from the repository on system restarts (until you restore it to managed). Continue?',
    confirmLabel: 'Save & customize',
  },
};

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
  const language = useUiLanguage();
  const t = COPY[language];
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
      notify(e instanceof Error ? e.message : t.saveFailed, 'error');
    } finally {
      setSaving(false);
    }
  }

  function requestSave() {
    if (!form.displayName.trim()) {
      notify(t.nameEmpty, 'error');
      return;
    }
    // A repo-managed template detaches from syncing on its first write; a
    // clone (never synced) or an already-customized one needs no warning.
    if (data && !data.customized && !data.cloned_from) setConfirmSave(true);
    else void save();
  }

  if (loading) return <ListLoading>{t.loading}</ListLoading>;

  const created = data?.created_at ? formatDateTime(data.created_at, language, '') : '';
  const identityName = data?.template_name ?? templateName;

  return (
    // Same arrangement as the settings tab: the cards scroll, Save does not.
    <div className="flex h-full min-h-0 flex-col gap-4">
      <ErrorBanner>{error}</ErrorBanner>

      <div className="flex-1 min-h-0 overflow-y-auto scroll-slim scroll-gutter space-y-4">
        <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-fg">{t.identity}</h2>
              <p className="text-sm text-muted mt-1">{t.identityHint}</p>
            </div>
            {data &&
              (data.cloned_from ? (
                <Badge tone="info" title={t.clonedTitle}>
                  {t.clonedFrom(data.cloned_from)}
                </Badge>
              ) : (
                <Badge tone={data.customized ? 'warning' : 'success'}>
                  {data.customized ? t.customized : t.managed}
                </Badge>
              ))}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="tpl-coder-name" className="block text-xs font-medium text-body mb-1">
                {t.coderName}
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
                {t.directory}
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
                {t.image}
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
              {t.createdFrom} <span className="font-mono">{data.cloned_from}</span>
              {created && t.createdOn(created)}. {t.clonedNote}
            </p>
          )}
        </div>

        <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-fg">{t.display}</h2>
            <p className="text-sm text-muted mt-1">{t.displayHint}</p>
          </div>

          <div>
            <label htmlFor="tpl-display-name" className="block text-xs font-medium text-body mb-1">
              {t.displayName}
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
              {t.description}
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
              {t.icon}
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
              {t.iconHint}
            </p>
          </div>
        </div>
      </div>

      <div className="shrink-0 flex flex-wrap items-center gap-3 border-t border-rule pt-4">
        <Button onClick={requestSave} disabled={!dirty} loading={saving} loadingLabel={t.saving}>
          {t.save}
        </Button>
        {draft && (
          <Button variant="ghost" onClick={() => setDraft(null)} disabled={saving}>
            {t.discard}
          </Button>
        )}
      </div>

      {confirmSave && (
        <ConfirmDialog
          open={confirmSave}
          title={t.confirmTitle}
          message={t.confirmMessage}
          confirmLabel={t.confirmLabel}
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

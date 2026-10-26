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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const coderClient = new CoderClient();

const COPY = {
  de: {
    saveFailed: 'Datei konnte nicht gespeichert werden',
    restoreFailed: 'Verwalteter Zustand konnte nicht wiederhergestellt werden',
    loading: 'Vorlagendateien werden geladen …',
    title: 'Vorlagendateien',
    hint: 'Direkte Bearbeitung der bereitgestellten Terraform-Dateien. Gespeicherte .tf-Dateien werden auf Syntaxfehler geprüft; maßgeblich bleibt der terraform plan beim nächsten Push der Vorlage.',
    clonedTitle: 'Hier erstellt; die Synchronisierung mit dem Repository fasst sie nie an',
    clonedFrom: (name: string) => `geklont von ${name}`,
    customized: 'angepasst',
    managed: 'verwaltet',
    restoreManaged: 'Verwalteten Zustand wiederherstellen',
    noFiles: 'Keine bearbeitbaren Dateien.',
    contentOf: (name: string) => `Inhalt von ${name}`,
    saving: 'Wird gespeichert …',
    save: (name: string | null) => `${name ?? 'Datei'} speichern`,
    discard: 'Änderungen verwerfen',
    effect: 'Änderungen wirken nach dem nächsten Push der Vorlage (Tab „Flotte“).',
    confirmTitle: 'Diese Vorlage anpassen?',
    confirmMessage:
      'Durch das Speichern gilt die Vorlage als vom Betrieb angepasst: Sie wird bei Neustarts des Systems nicht mehr automatisch aus dem Repository aktualisiert (bis du sie wieder auf „verwaltet“ zurücksetzt). Fortfahren?',
    confirmLabel: 'Speichern & anpassen',
    restoreTitle: 'Verwalteten Zustand wiederherstellen?',
    restoreMessage:
      'Die Repository-Vorgaben ersetzen beim nächsten Systemstart ALLE angepassten Dateien dieser Vorlage – deine Anpassungen gehen dann verloren. Fortfahren?',
  },
  en: {
    saveFailed: 'Failed to save file',
    restoreFailed: 'Failed to restore managed state',
    loading: 'Loading template files…',
    title: 'Template files',
    hint: 'Raw editing of the deployed Terraform files. Saved .tf files are syntax-checked; the real gate stays the terraform plan run by the next template push.',
    clonedTitle: 'Created here; the repository sync never touches it',
    clonedFrom: (name: string) => `cloned from ${name}`,
    customized: 'customized',
    managed: 'managed',
    restoreManaged: 'Restore managed',
    noFiles: 'No editable files.',
    contentOf: (name: string) => `Content of ${name}`,
    saving: 'Saving…',
    save: (name: string | null) => `Save ${name ?? 'file'}`,
    discard: 'Discard changes',
    effect: 'Changes take effect after the next template push (Fleet tab).',
    confirmTitle: 'Customize this template?',
    confirmMessage:
      'Saving marks the template as operator-customized: it will no longer be updated automatically from the repository on system restarts (until you restore it to managed). Continue?',
    confirmLabel: 'Save & customize',
    restoreTitle: 'Restore managed state?',
    restoreMessage:
      'The repository defaults will replace ALL customized files of this template on the next system startup — your customizations will be lost then. Continue?',
  },
};

/** Raw editor over the deployed template directory's files. */
export default function TemplateFilesPanel({ templateName }: { templateName: string }) {
  const notify = useNotify();
  const language = useUiLanguage();
  const t = COPY[language];
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [confirmSave, setConfirmSave] = useState(false);
  const [confirmRestore, setConfirmRestore] = useState(false);

  const { data, loading, error, reload } = useResource(
    () => coderClient.getTemplateFiles({ templateName }),
    [templateName],
  );

  const files = data?.files ?? [];
  const active = activeFile ?? files[0]?.name ?? null;
  const currentFile = files.find((file) => file.name === active) ?? null;
  const currentContent =
    (active !== null ? drafts[active] : undefined) ?? currentFile?.content ?? '';
  const isDirty = (name: string) =>
    drafts[name] !== undefined && drafts[name] !== files.find((f) => f.name === name)?.content;

  async function saveActive() {
    if (!active) return;
    setSaving(true);
    try {
      const response = await coderClient.updateTemplateFile({
        templateName,
        fileName: active,
        content: currentContent,
      });
      notify(response.message, 'success');
      setDrafts((previous) => {
        const next = { ...previous };
        delete next[active];
        return next;
      });
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.saveFailed, 'error');
    } finally {
      setSaving(false);
    }
  }

  function requestSave() {
    if (!active || !isDirty(active)) return;
    if (data && !data.customized) setConfirmSave(true);
    else void saveActive();
  }

  async function restoreManaged() {
    try {
      const response = await coderClient.restoreTemplateManaged({ templateName });
      notify(response.message, 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.restoreFailed, 'error');
    }
  }

  if (loading) return <ListLoading>{t.loading}</ListLoading>;

  return (
    <>
      {/*
        Fills the page rather than growing past it. The editor is the only
        part that scrolls: with a fixed `rows` the card grew to the file's
        length, so a 60-line Dockerfile pushed Save several hundred pixels
        below the fold and you had to scroll the whole page to reach the
        button for the file you were already looking at.
      */}
      <div className="flex h-full min-h-0 flex-col gap-4">
        <ErrorBanner>{error}</ErrorBanner>

        <div className="flex-1 min-h-0 flex flex-col gap-4 bg-surface rounded-lg border border-rule p-5">
          <div className="shrink-0 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-fg">{t.title}</h2>
              <p className="text-sm text-muted mt-1">{t.hint}</p>
            </div>
            <div className="flex items-center gap-2">
              {data && (
                data.cloned_from ? (
                  <Badge tone="info" title={t.clonedTitle}>
                    {t.clonedFrom(data.cloned_from)}
                  </Badge>
                ) : (
                  <Badge tone={data.customized ? 'warning' : 'success'}>
                    {data.customized ? t.customized : t.managed}
                  </Badge>
                )
              )}
              {/* A clone has no repo copy to restore to. */}
              {data?.customized && !data.cloned_from && (
                <Button size="xs" variant="ghost" onClick={() => setConfirmRestore(true)}>
                  {t.restoreManaged}
                </Button>
              )}
            </div>
          </div>

          <div className="shrink-0 flex flex-wrap gap-1.5">
            {files.map((file) => (
              <Button
                key={file.name}
                size="xs"
                variant={file.name === active ? 'secondary' : 'ghost'}
                onClick={() => setActiveFile(file.name)}
              >
                {file.name}
                {isDirty(file.name) && <span className="text-warn-text ml-1">•</span>}
              </Button>
            ))}
            {files.length === 0 && <p className="text-sm text-muted">{t.noFiles}</p>}
          </div>

          {currentFile && (
            <textarea
              value={currentContent}
              onChange={(event) =>
                setDrafts((previous) => ({ ...previous, [active as string]: event.target.value }))
              }
              spellCheck={false}
              // No `rows`: the height comes from the flex row, so the editor
              // ends exactly where the card does. min-h keeps it usable on a
              // very short window — then, and only then, the page scrolls again.
              className={`${inputCls} flex-1 min-h-48 resize-none font-mono text-xs leading-5 whitespace-pre`}
              aria-label={t.contentOf(currentFile.name)}
              disabled={saving}
            />
          )}

          <div className="shrink-0 flex flex-wrap items-center gap-3">
            <Button
              onClick={requestSave}
              disabled={!active || !isDirty(active)}
              loading={saving}
              loadingLabel={t.saving}
            >
              {t.save(active)}
            </Button>
            {active && isDirty(active) && (
              <Button
                variant="ghost"
                disabled={saving}
                onClick={() =>
                  setDrafts((previous) => {
                    const next = { ...previous };
                    delete next[active];
                    return next;
                  })
                }
              >
                {t.discard}
              </Button>
            )}
            <span className="text-xs text-muted">
              {t.effect}
            </span>
          </div>
        </div>
      </div>

      {confirmSave && (
        <ConfirmDialog
          open={confirmSave}
          title={t.confirmTitle}
          message={t.confirmMessage}
          confirmLabel={t.confirmLabel}
          onConfirm={() => {
            setConfirmSave(false);
            void saveActive();
          }}
          onCancel={() => setConfirmSave(false)}
        />
      )}

      {confirmRestore && (
        <ConfirmDialog
          open={confirmRestore}
          title={t.restoreTitle}
          variant="danger"
          message={t.restoreMessage}
          confirmLabel={t.restoreManaged}
          onConfirm={() => {
            setConfirmRestore(false);
            void restoreManaged();
          }}
          onCancel={() => setConfirmRestore(false)}
        />
      )}
    </>
  );
}

'use client';

import { useState } from 'react';
import { ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CoderClient } from '@/src/clients/CoderClient';
import type { WorkspaceVolume } from '@/src/types/workspaces';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
import { formatNumber } from '@/src/utils/locale';

const coderClient = new CoderClient();

const COPY = {
  de: {
    unknown: 'unbekannt',
    failedPrefix: 'Das Volume konnte nicht ',
    failedDelete: 'gelöscht werden',
    failedRepair: 'repariert werden',
    reading: 'Volumes werden gelesen …',
    heading: 'Volumes der Arbeitsumgebungen',
    home: 'Home',
    scratch: 'Scratch',
    intro1: 'Ein ',
    intro2: '-Volume enthält die Dateien einer Person und wird von allen ihren Arbeitsumgebungen gemeinsam genutzt. Das Löschen einer Arbeitsumgebung berührt es nie, deshalb muss der Speicher hier freigegeben werden. Ein ',
    intro3: '-Volume gehört zu einer einzelnen temporären Arbeitsumgebung und verschwindet mit ihr.',
    total: (size: string) => ` Insgesamt ${size}.`,
    unresolved:
      'Coder ist nicht erreichbar, daher konnten die Besitzer nicht ermittelt werden. Es wird nichts als verwaist markiert, denn ein fehlender Besitzer bedeutet hier nur, dass die Abfrage fehlgeschlagen ist.',
    volume: 'Volume',
    kind: 'Art',
    belongsTo: 'Gehört zu',
    size: 'Größe',
    state: 'Zustand',
    actions: 'Aktionen',
    inUse: 'In Benutzung',
    orphaned: 'Verwaist',
    orphanedTitle: 'Die Person oder Arbeitsumgebung, für die dieses Volume angelegt wurde, existiert nicht mehr.',
    repairTitle:
      'Gibt alle Dateien an den Benutzer der Arbeitsumgebung zurück. Nötig, wenn eine Arbeitsumgebung Dateien als root geschrieben hat und die Vorlage inzwischen keinen root-Zugriff mehr hat.',
    repair: 'Besitzer reparieren',
    delete: 'Löschen',
    inUseTitle: 'Ein Container verwendet dieses Volume. Stoppe zuerst die Arbeitsumgebung.',
    empty: 'Keine Volumes für Arbeitsumgebungen.',
    deleteTitle: 'Volume löschen',
    deleteHome: (who: string) =>
      `Dadurch werden alle Dateien von ${who} gelöscht, und zwar in allen ihren Arbeitsumgebungen, nicht nur in einer. Das lässt sich nicht rückgängig machen.`,
    deleteScratch: (who: string) =>
      `Dadurch wird das Scratch-Volume von ${who} gelöscht. Das lässt sich nicht rückgängig machen.`,
  },
  en: {
    unknown: 'unknown',
    failedPrefix: 'Failed to ',
    failedDelete: 'delete the volume',
    failedRepair: 'repair the volume',
    reading: 'Reading volumes…',
    heading: 'Workspace volumes',
    home: 'home',
    scratch: 'scratch',
    intro1: 'A ',
    intro2: " volume holds one user's files and is shared by all of their workspaces; deleting a workspace never touches it, which is why reclaiming one has to happen here. A ",
    intro3: ' volume belongs to a single throwaway workspace and goes away with it.',
    total: (size: string) => ` ${size} in total.`,
    unresolved:
      'Coder is unreachable, so owners could not be resolved. Nothing is marked as an orphan — a missing owner here would only mean the lookup failed.',
    volume: 'Volume',
    kind: 'Kind',
    belongsTo: 'Belongs to',
    size: 'Size',
    state: 'State',
    actions: 'Actions',
    inUse: 'In use',
    orphaned: 'Orphaned',
    orphanedTitle: 'The user or workspace this volume was created for no longer exists.',
    repairTitle:
      'Give every file back to the workspace user. Needed when a workspace wrote files as root and the template has since lost root access.',
    repair: 'Repair ownership',
    delete: 'Delete',
    inUseTitle: 'A container is using this volume — stop the workspace first.',
    empty: 'No workspace volumes.',
    deleteTitle: 'Delete volume',
    deleteHome: (who: string) =>
      `This deletes every file of ${who} — across all of their workspaces, not just one. It cannot be undone.`,
    deleteScratch: (who: string) =>
      `This deletes the scratch volume of ${who}. It cannot be undone.`,
  },
};

function formatSize(language: UiLanguage, bytes?: number | null): string {
  if (bytes == null) return COPY[language].unknown;
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${i === 0 ? String(bytes) : formatNumber(bytes / 1024 ** i, language, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ${units[i]}`;
}

/** Who a volume belongs to, or why we cannot say. */
function owner(volume: WorkspaceVolume): string {
  if (volume.kind === 'home') return volume.user_name || volume.user_id || '—';
  return volume.workspace_name || '—';
}

/**
 * Home and scratch volumes: what exists, how big it is, and the two things a
 * maintainer needs to do with them.
 *
 * These volumes are deliberately not Terraform-managed so deleting a workspace
 * can never destroy a home — which is also why nothing else in the platform
 * shows them.
 */
export default function WorkspaceVolumesPanel() {
  const language = useUiLanguage();
  const t = COPY[language];
  const notify = useNotify();
  const [busy, setBusy] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<WorkspaceVolume | null>(null);

  const { data, loading, error, reload } = useResource(() => coderClient.listVolumes(), []);

  async function run(action: 'delete' | 'repair', volume: WorkspaceVolume) {
    setBusy(volume.name);
    try {
      const result =
        action === 'delete'
          ? await coderClient.deleteVolume({ name: volume.name })
          : await coderClient.repairVolume({ name: volume.name });
      notify(result.message, 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error
          ? e.message
          : `${t.failedPrefix}${action === 'delete' ? t.failedDelete : t.failedRepair}`, 'error');
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <ListLoading>{t.reading}</ListLoading>;

  const volumes = data?.volumes ?? [];

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 bg-surface rounded-lg border border-rule p-5">
        <h2 className="text-lg font-semibold text-fg">{t.heading}</h2>
        <p className="text-sm text-muted mt-1">
          {t.intro1}<span className="font-medium">{t.home}</span>{t.intro2}
          <span className="font-medium">{t.scratch}</span>{t.intro3}
          {data ? t.total(formatSize(language, data.total_bytes)) : ''}
        </p>
        {data?.unresolved && (
          <p className="mt-2 text-sm text-warn-text">
            {t.unresolved}
          </p>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-auto bg-surface rounded-lg border border-rule">
        <table className="min-w-full text-sm">
          <thead className="bg-canvas text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-2">{t.volume}</th>
              <th className="px-4 py-2">{t.kind}</th>
              <th className="px-4 py-2">{t.belongsTo}</th>
              <th className="px-4 py-2 text-right">{t.size}</th>
              <th className="px-4 py-2">{t.state}</th>
              <th className="px-4 py-2 text-right">{t.actions}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule-soft">
            {volumes.map((volume) => (
              <tr key={volume.name} className={volume.orphaned ? 'bg-warn-wash/40' : undefined}>
                <td className="px-4 py-2 font-mono text-xs text-body">{volume.name}</td>
                <td className="px-4 py-2">{volume.kind}</td>
                <td className="px-4 py-2">{owner(volume)}</td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {formatSize(language, volume.size_bytes)}
                </td>
                <td className="px-4 py-2">
                  {volume.in_use && (
                    <span className="inline-flex items-center rounded bg-accent-wash px-2 py-0.5 text-xs font-medium text-accent-text">
                      {t.inUse}
                    </span>
                  )}
                  {volume.orphaned && (
                    <span
                      className="ml-1 inline-flex items-center rounded bg-warn-wash px-2 py-0.5 text-xs font-medium text-warn-text"
                      title={t.orphanedTitle}
                    >
                      {t.orphaned}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <div className="flex justify-end gap-2">
                    {volume.kind === 'home' && (
                      <Button
                        variant="ghost"
                        onClick={() => run('repair', volume)}
                        loading={busy === volume.name}
                        title={t.repairTitle}
                      >
                        {t.repair}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      onClick={() => setConfirming(volume)}
                      disabled={busy !== null || volume.in_use === true}
                      title={
                        volume.in_use
                          ? t.inUseTitle
                          : undefined
                      }
                    >
                      {t.delete}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {volumes.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-sm text-muted">
                  {t.empty}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {confirming && (
        <ConfirmDeleteDialog
          title={t.deleteTitle}
          message={
            confirming.kind === 'home'
              ? t.deleteHome(owner(confirming))
              : t.deleteScratch(owner(confirming))
          }
          confirmWord={confirming.name}
          onConfirm={async () => {
            await run('delete', confirming);
            setConfirming(null);
          }}
          onClose={() => setConfirming(null)}
        />
      )}
    </>
  );
}

'use client';

import Badge, { type BadgeColor } from '@/src/components/Badge';
import type { WorkspaceBuildStatus } from '@/src/types/workspaces';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';

type StatusCategory = 'running' | 'stopped' | 'pending' | 'failed' | 'unknown';

/**
 * Which lifecycle bucket a workspace is in.
 *
 * `latest_build_status` describes the latest BUILD, and a build's meaning
 * depends on its `transition`: a stopped workspace's last build succeeded — at
 * stopping. Without the transition, 'succeeded' and 'running' have to be read
 * optimistically (that is all the caller gave us); with it, a finished stop or
 * delete lands in 'stopped' instead of claiming the workspace is up. The
 * backend gates its running-workspace quota on the same pair.
 */
function categorizeStatus(
  status?: WorkspaceBuildStatus | string | null,
  transition?: string | null,
): StatusCategory {
  if (!status) return 'unknown';
  const s = status.toLowerCase();
  if (s === 'failed') return 'failed';
  if (s === 'running' || s === 'succeeded') {
    if (transition === 'stop') return 'stopped';
    if (transition === 'delete') return 'unknown';
    return 'running';
  }
  if (s === 'stopped' || s === 'canceled') return 'stopped';
  if (s === 'starting' || s === 'stopping' || s === 'pending' || s === 'canceling' || s === 'deleting') return 'pending';
  return 'unknown';
}

const categoryColor: Record<StatusCategory, BadgeColor> = {
  running: 'green',
  stopped: 'gray',
  pending: 'yellow',
  failed: 'red',
  unknown: 'gray',
};

const categoryDots: Record<StatusCategory, string> = {
  running: 'bg-success',
  stopped: 'bg-gray-400',
  pending: 'bg-yellow-500 animate-pulse',
  failed: 'bg-danger',
  unknown: 'bg-gray-400',
};

/**
 * What to call the state in the UI. The raw build status is provisioner
 * vocabulary ('succeeded' for a workspace that is merely stopped), so the badge
 * shows the lifecycle word a user recognises and keeps the raw value in the
 * tooltip for whoever is debugging.
 */
const COPY = {
  de: {
    buildStatus: 'Build-Status',
    categories: {
      running: 'läuft',
      stopped: 'gestoppt',
      pending: 'in Arbeit',
      failed: 'fehlgeschlagen',
      unknown: 'unbekannt',
    } as Record<StatusCategory, string>,
    inFlight: {
      starting: 'startet',
      stopping: 'wird gestoppt',
      pending: 'ausstehend',
      canceling: 'wird abgebrochen',
      deleting: 'wird gelöscht',
    } as Record<string, string>,
    // The raw build status for the tooltip. German pages show it in German;
    // English pages keep Coder's own word, which is already English.
    raw: {
      pending: 'ausstehend',
      starting: 'startet',
      running: 'läuft',
      stopping: 'wird gestoppt',
      stopped: 'gestoppt',
      failed: 'fehlgeschlagen',
      canceling: 'wird abgebrochen',
      canceled: 'abgebrochen',
      deleting: 'wird gelöscht',
      deleted: 'gelöscht',
      succeeded: 'erfolgreich',
    } as Record<string, string>,
  },
  en: {
    buildStatus: 'Build status',
    categories: {
      running: 'running',
      stopped: 'stopped',
      pending: 'working',
      failed: 'failed',
      unknown: 'unknown',
    } as Record<StatusCategory, string>,
    inFlight: {
      starting: 'starting',
      stopping: 'stopping',
      pending: 'pending',
      canceling: 'canceling',
      deleting: 'deleting',
    } as Record<string, string>,
    raw: {} as Record<string, string>,
  },
};

function statusLabel(
  status: string | null | undefined,
  transition: string | null | undefined,
  language: UiLanguage,
): string {
  const t = COPY[language];
  const s = (status || '').toLowerCase();
  // In-flight statuses already read well; they are the transition itself.
  const label = s in t.inFlight ? t.inFlight[s] : t.categories[categorizeStatus(status, transition)];
  // Only the first letter: CSS `capitalize` would turn "wird gestoppt" into
  // "Wird Gestoppt".
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** Live workspace status as a shared Badge pill with a state dot. */
export default function WorkspaceStatusBadge({
  status,
  transition,
  detail,
}: {
  status?: WorkspaceBuildStatus | string | null;
  /** The build's transition ('start' | 'stop' | 'delete') — pass it when known. */
  transition?: string | null;
  /** Extra tooltip line, e.g. the workspace's "Version vom …". */
  detail?: string | null;
}) {
  const language = useUiLanguage();
  const category = categorizeStatus(status, transition);
  const title = [status ? `${COPY[language].buildStatus}: ${COPY[language].raw[status.toLowerCase()] ?? status}` : null, detail]
    .filter(Boolean).join(' · ');
  return (
    <Badge color={categoryColor[category]} pill>
      <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${categoryDots[category]}`} />
      <span title={title || undefined}>
        {statusLabel(status, transition, language)}
      </span>
    </Badge>
  );
}

export { categorizeStatus };
export type { StatusCategory };

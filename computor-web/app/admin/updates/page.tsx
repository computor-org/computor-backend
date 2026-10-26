'use client';

import { useEffect, useRef, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { UpdateClient } from '@/src/clients/UpdateClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import type { SystemUpdateState, SystemUpdateStatusGet } from 'types/generated';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';

const updateClient = new UpdateClient();

/** After this long without API contact during a run, stop assuming "in progress". */
const IN_PROGRESS_GRACE_MS = 30 * 60 * 1000;

const shortCommit = (commit: string | null | undefined) =>
  commit ? commit.slice(0, 7) : '—';

/** The backend's fixed message when SYSTEM_REPO_URL is unset (api/update.py). */
const isRepoNotConfigured = (error: string) => error.includes('SYSTEM_REPO_URL is not configured');

const COPY = {
  de: {
    phases: {
      preflight: 'Vorabprüfungen laufen',
      checking: 'Daten werden vom Repository geholt',
      checking_out: 'Neue Version wird ausgecheckt',
      building: 'Images werden gebaut',
      entering_maintenance: 'Wartungsmodus wird aktiviert',
      starting: 'Dienste werden gestartet',
      health_check: 'Warten, bis die Dienste fehlerfrei laufen',
      finalizing: 'Abschluss',
      rolling_back: 'Rückkehr zur vorherigen Version',
    } as Record<string, string>,
    working: 'Es läuft',
    updateCompleted: 'Update erfolgreich abgeschlossen',
    updateRolledBack: 'Update fehlgeschlagen, die vorherige Version wurde wiederhergestellt',
    updateFailed: 'Update fehlgeschlagen',
    checkFailed: 'Update-Prüfung fehlgeschlagen',
    requested: 'Update angefordert, das System wechselt in Kürze in den Wartungsmodus',
    requestFailed: 'Update konnte nicht angefordert werden',
    scheduled: 'Update geplant',
    scheduleFailed: 'Update konnte nicht geplant werden',
    scheduleCancelled: 'Geplantes Update abgebrochen',
    cancelFailed: 'Geplantes Update konnte nicht abgebrochen werden',
    hashCopied: 'Commit-Hash kopiert',
    copyFailed: 'Kopieren in die Zwischenablage nicht möglich',
    denied: 'Zugriff verweigert',
    adminRequired: 'Für diese Seite sind Administratorrechte erforderlich.',
    disabledSelfUpdate: 'Selbst-Update ist deaktiviert. Setze UPDATE_ENABLED=true in der .env und starte neu, um es zu aktivieren.',
    disabledUpdater: 'Der Updater-Sidecar läuft nicht (Entwicklungsumgebung oder der Sidecar ist ausgefallen). Updates lassen sich nur in der Produktion auslösen.',
    disabledInProgress: 'Ein Update läuft bereits.',
    breadcrumb: 'Updates',
    title: 'System-Updates',
    subtitle: 'Vergleiche die laufende Version mit dem beobachteten Branch des Repositorys und führe Updates mit einem Klick aus.',
    downtimeTitle: 'Update läuft, das System startet neu',
    downtimeBody: 'Diese Seite wird automatisch fortgesetzt, sobald die API wieder erreichbar ist. Schließe diesen Tab nicht.',
    version: 'Version',
    updateAvailable: 'Update verfügbar',
    upToDate: 'Aktuell',
    runningCommit: 'Laufender Commit:',
    copyHash: 'Vollständigen Hash kopieren',
    runningBranch: 'Laufender Branch:',
    trackedRepo: 'Beobachtetes Repository',
    checking: 'Wird geprüft…',
    checkNow: 'Jetzt prüfen',
    repository: 'Repository:',
    notConfigured: 'SYSTEM_REPO_URL ist nicht konfiguriert',
    trackedBranch: 'Beobachteter Branch:',
    latestCommit: 'Neuester Commit:',
    checkedAt: (when: string) => `geprüft ${when}`,
    checkFailedLabel: 'Update-Prüfung fehlgeschlagen:',
    repoNotConfigured:
      'Es ist kein Update-Repository konfiguriert, deshalb lässt sich nicht prüfen, ob eine neue Version vorliegt. Trage SYSTEM_REPO_URL in der .env des Servers ein.',
    technicalDetail: 'Technische Details:',
    scheduledUpdate: 'Geplantes Update',
    missedBefore: 'Das für ',
    missedAfter: ' geplante Update wurde nicht ausgeführt:',
    earlierTime: 'einen früheren Zeitpunkt',
    dismiss: 'Ausblenden',
    scheduledBefore: 'Ein Update ist für ',
    scheduledAfter: ' geplant',
    scheduledBy: (name: string) => ` von ${name}`,
    scheduledTail: '. Das System wechselt in den Wartungsmodus und aktualisiert sich automatisch.',
    cancelling: 'Wird abgebrochen…',
    cancelSchedule: 'Planung abbrechen',
    dateTime: 'Datum und Uhrzeit',
    scheduling: 'Wird geplant…',
    scheduleUpdate: 'Update planen',
    scheduleExplain: 'Zum geplanten Zeitpunkt wechselt das System in den Wartungsmodus, aktualisiert auf den neuesten Commit des beobachteten Branches und kehrt automatisch zurück, falls das Update fehlschlägt. Benutzer erhalten vorher Countdown-Benachrichtigungen.',
    inProgress: 'Update läuft',
    lastUpdate: 'Letztes Update',
    success: 'Erfolgreich',
    failed: 'Fehlgeschlagen',
    rolledBack: 'Zurückgesetzt',
    running: 'Läuft',
    phase: 'Phase:',
    fromTo: 'Von → bis:',
    requestedBy: 'Angefordert von:',
    finished: 'Beendet:',
    updatedReload: 'Das System wurde aktualisiert. Lade die Seite neu, um die neue Frontend-Version zu laden.',
    reload: 'Seite neu laden',
    actions: 'Aktionen',
    requesting: 'Wird angefordert…',
    updateNow: 'Jetzt aktualisieren',
    alreadyUpToDate: 'Das System ist bereits aktuell.',
    updatesToBefore: 'Aktualisiert auf ',
    updatesToMid: ' auf Branch ',
    updatesToAfter: '.',
    howTitle: 'So funktioniert das Selbst-Update',
    downtime: 'Ausfallzeit:',
    downtimeText: ' Das Update baut zuerst die neuen Images und zeigt dann eine statische Wartungsseite an, während die Dienste neu starten. Rechne mit einigen Minuten Ausfall.',
    rollback: 'Rollback:',
    rollbackText: ' Läuft das System danach nicht fehlerfrei, kehrt der Updater automatisch zur vorherigen Version zurück.',
    migrations: 'Datenbankmigrationen',
    migrationsBefore: ' laufen beim Start automatisch und werden bei einem Rollback ',
    migrationsNot: 'nicht',
    migrationsAfter: ' rückgängig gemacht. Migrationen müssen daher für eine Version abwärtskompatibel bleiben.',
    configuration: 'Konfiguration:',
    configBefore: ' Das beobachtete Repository und der Branch stammen aus ',
    configIn: ' in der ',
    configAfter: '. Deine .env wird von einem Update nie verändert.',
    cancelTitle: 'Geplantes Update abbrechen',
    cancelMessage: 'Das ausstehende geplante Update wird entfernt, und das System aktualisiert sich nicht automatisch. Planung abbrechen?',
    cancelConfirm: 'Planung abbrechen',
    updateTitle: 'System aktualisieren',
    updateMessage: 'Das gesamte System, auch diese Seite, ist während des Updates einige Minuten offline. Besteht die neue Version die Integritätsprüfung nicht, wird die vorherige Version automatisch wiederhergestellt. Update starten?',
    updateConfirm: 'Jetzt aktualisieren',
  },
  en: {
    phases: {
      preflight: 'Running preflight checks',
      checking: 'Fetching from repository',
      checking_out: 'Checking out new version',
      building: 'Building images',
      entering_maintenance: 'Entering maintenance mode',
      starting: 'Starting services',
      health_check: 'Waiting for services to become healthy',
      finalizing: 'Finalizing',
      rolling_back: 'Rolling back to previous version',
    } as Record<string, string>,
    working: 'Working',
    updateCompleted: 'Update completed successfully',
    updateRolledBack: 'Update failed — rolled back to the previous version',
    updateFailed: 'Update failed',
    checkFailed: 'Update check failed',
    requested: 'Update requested — the system will go into maintenance shortly',
    requestFailed: 'Failed to request update',
    scheduled: 'Update scheduled',
    scheduleFailed: 'Failed to schedule update',
    scheduleCancelled: 'Scheduled update cancelled',
    cancelFailed: 'Failed to cancel scheduled update',
    hashCopied: 'Commit hash copied',
    copyFailed: 'Could not copy to clipboard',
    denied: 'Access Denied',
    adminRequired: 'Admin privileges are required to access this page.',
    disabledSelfUpdate: 'Self-update is disabled. Set UPDATE_ENABLED=true in .env and restart to enable it.',
    disabledUpdater: 'The updater sidecar is not running (development environment, or the sidecar is down). Updates can only be triggered in production.',
    disabledInProgress: 'An update is already in progress.',
    breadcrumb: 'Updates',
    title: 'System updates',
    subtitle: 'Compare the running version with the tracked repository branch and run one-click updates.',
    downtimeTitle: 'Update in progress — the system is restarting',
    downtimeBody: 'This page will resume automatically when the API is back. Do not close this tab.',
    version: 'Version',
    updateAvailable: 'Update available',
    upToDate: 'Up to date',
    runningCommit: 'Running commit:',
    copyHash: 'copy full hash',
    runningBranch: 'Running branch:',
    trackedRepo: 'Tracked Repository',
    checking: 'Checking…',
    checkNow: 'Check now',
    repository: 'Repository:',
    notConfigured: 'SYSTEM_REPO_URL not configured',
    trackedBranch: 'Tracked branch:',
    latestCommit: 'Latest commit:',
    checkedAt: (when: string) => `checked ${when}`,
    checkFailedLabel: 'Update check failed:',
    repoNotConfigured:
      'No update repository is configured, so the platform cannot check for a new version. Set SYSTEM_REPO_URL in the server .env.',
    technicalDetail: 'Technical detail:',
    scheduledUpdate: 'Scheduled Update',
    missedBefore: 'The update scheduled for ',
    missedAfter: ' did not run:',
    earlierTime: 'an earlier time',
    dismiss: 'Dismiss',
    scheduledBefore: 'An update is scheduled for ',
    scheduledAfter: '',
    scheduledBy: (name: string) => ` by ${name}`,
    scheduledTail: '. The system will go into maintenance and update itself automatically.',
    cancelling: 'Cancelling…',
    cancelSchedule: 'Cancel Schedule',
    dateTime: 'Date & Time',
    scheduling: 'Scheduling…',
    scheduleUpdate: 'Schedule Update',
    scheduleExplain: 'At the scheduled time the system enters maintenance, updates to the latest commit on the tracked branch, and rolls back automatically if the update fails. Users get countdown notifications beforehand.',
    inProgress: 'Update in Progress',
    lastUpdate: 'Last Update',
    success: 'Success',
    failed: 'Failed',
    rolledBack: 'Rolled back',
    running: 'Running',
    phase: 'Phase:',
    fromTo: 'From → to:',
    requestedBy: 'Requested by:',
    finished: 'Finished:',
    updatedReload: 'The system was updated. Reload to load the new frontend version.',
    reload: 'Reload page',
    actions: 'Actions',
    requesting: 'Requesting…',
    updateNow: 'Update now',
    alreadyUpToDate: 'The system is already up to date.',
    updatesToBefore: 'Updates to ',
    updatesToMid: ' on ',
    updatesToAfter: '.',
    howTitle: 'How Self-Update Works',
    downtime: 'Downtime:',
    downtimeText: ' the update builds the new images first, then serves a static maintenance page while services restart — expect a few minutes of downtime.',
    rollback: 'Rollback:',
    rollbackText: ' if the system does not come back healthy, the updater automatically rolls back to the previous version.',
    migrations: 'Database migrations',
    migrationsBefore: ' run automatically on startup and are ',
    migrationsNot: 'not',
    migrationsAfter: ' reverted by a rollback — migrations must stay backward-compatible for one version.',
    configuration: 'Configuration:',
    configBefore: ' the tracked repository and branch come from ',
    configIn: ' in ',
    configAfter: '; your .env is never modified by an update.',
    cancelTitle: 'Cancel Scheduled Update',
    cancelMessage: 'The pending scheduled update will be removed and the system will not update automatically. Cancel the schedule?',
    cancelConfirm: 'Cancel schedule',
    updateTitle: 'Update the system',
    updateMessage: 'The entire system — including this page — will go offline for several minutes while the update runs. If the new version fails its health check, the previous version is restored automatically. Start the update?',
    updateConfirm: 'Update now',
  },
};

export default function UpdatesPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const when = (value: string) => formatDateTime(value, language);
  const { isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const notify = useNotify();

  // Poll every 5s. During an update the API goes down: useResource keeps the
  // last data on error, and lastStatusRef lets us render an "in progress"
  // panel instead of a scary error banner until the API comes back.
  const { data: status, loading, error, reload } = useResource(
    () => updateClient.getStatus(),
    [],
    { refetchInterval: 5000 },
  );
  const lastStatusRef = useRef<SystemUpdateStatusGet | null>(null);
  const notifiedOutcomeRef = useRef<string | null>(null);
  if (status) lastStatusRef.current = status;

  const [checking, setChecking] = useState(false);
  const [showUpdateConfirm, setShowUpdateConfirm] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduling, setScheduling] = useState(false);
  const [showCancelScheduleConfirm, setShowCancelScheduleConfirm] = useState(false);
  const [cancellingSchedule, setCancellingSchedule] = useState(false);
  const [dismissedResult, setDismissedResult] = useState<string | null>(null);

  const lastStatus = lastStatusRef.current;
  const state: SystemUpdateState | undefined = (status ?? lastStatus)?.state;
  const runInProgress = state?.status === 'requested' || state?.status === 'running';

  // API unreachable while a run was in progress → expected downtime, not an error.
  const runStartedAt = state?.started_at || state?.requested_at;
  const withinGrace =
    !!runStartedAt && Date.now() - new Date(runStartedAt).getTime() < IN_PROGRESS_GRACE_MS;
  const showDowntimePanel = !!error && runInProgress && withinGrace;

  // When the API comes back with a terminal state, surface the outcome once.
  // (Effect, not render: notify() updates the notification context's state.)
  useEffect(() => {
    if (!status || error || !status.state || runInProgress) return;
    const s = status.state;
    const key = `${s.status}:${s.finished_at ?? ''}`;
    if (
      notifiedOutcomeRef.current !== null &&
      notifiedOutcomeRef.current !== key &&
      (s.status === 'success' || s.status === 'failed' || s.status === 'rolled_back')
    ) {
      notify(
        s.status === 'success'
          ? t.updateCompleted
          : s.status === 'rolled_back'
            ? t.updateRolledBack
            : t.updateFailed,
        s.status === 'success' ? 'success' : 'error',
      );
    }
    notifiedOutcomeRef.current = key;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, error, runInProgress]);

  const handleCheckNow = async () => {
    setChecking(true);
    try {
      await updateClient.checkNow();
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.checkFailed, 'error');
    } finally {
      setChecking(false);
    }
  };

  const handleTriggerUpdate = async () => {
    setShowUpdateConfirm(false);
    setTriggering(true);
    try {
      await updateClient.triggerUpdate();
      notify(t.requested, 'success');
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.requestFailed, 'error');
    } finally {
      setTriggering(false);
    }
  };

  const handleSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduleDate) return;
    setScheduling(true);
    try {
      await updateClient.scheduleUpdate(new Date(scheduleDate).toISOString());
      notify(t.scheduled, 'success');
      setScheduleDate('');
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.scheduleFailed, 'error');
    } finally {
      setScheduling(false);
    }
  };

  const handleCancelSchedule = async () => {
    setShowCancelScheduleConfirm(false);
    setCancellingSchedule(true);
    try {
      await updateClient.cancelSchedule();
      notify(t.scheduleCancelled, 'success');
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.cancelFailed, 'error');
    } finally {
      setCancellingSchedule(false);
    }
  };

  const handleCopyCommit = async (commit?: string) => {
    if (!commit) return;
    try {
      await navigator.clipboard.writeText(commit);
      notify(t.hashCopied, 'success');
    } catch {
      notify(t.copyFailed, 'error');
    }
  };

  // Access control
  if (!authLoading && !isAdmin) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-danger-wash border border-danger-line rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-danger-text">{t.denied}</h2>
            <p className="text-sm text-danger-text mt-2">{t.adminRequired}</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const view = status ?? lastStatus;
  const updateDisabledReason = !view
    ? null
    : !view.update_enabled
      ? t.disabledSelfUpdate
      : !view.updater_online
        ? t.disabledUpdater
        : runInProgress
          ? t.disabledInProgress
          : null;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.breadcrumb }]}
          title={t.title}
          subtitle={t.subtitle}
        />

        {/* API down during an update is expected — show progress, not an error */}
        {showDowntimePanel ? (
          <div className="bg-accent-wash border border-accent-line rounded-lg p-4 mb-4">
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 text-accent-text animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-accent-text">
                  {t.downtimeTitle}
                </p>
                <p className="text-sm text-accent-text">
                  {(state?.phase && t.phases[state.phase]) || t.working}… {t.downtimeBody}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <ErrorBanner>{error}</ErrorBanner>
        )}

        <ScrollArea>
          {/* Loading skeleton */}
          {loading && !view && (
            <div className="bg-surface rounded-lg border border-rule p-6 animate-pulse">
              <div className="h-6 bg-sunken rounded w-1/4 mb-4" />
              <div className="h-4 bg-sunken rounded w-1/2" />
            </div>
          )}

          {view && (
            <>
              {/* Version card */}
              <div className="bg-surface rounded-lg shadow border border-rule p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-fg">{t.version}</h2>
                  {view.update_available ? (
                    <Badge color="yellow" pill>{t.updateAvailable}</Badge>
                  ) : view.remote_commit ? (
                    <Badge color="green" pill>{t.upToDate}</Badge>
                  ) : null}
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted w-36">{t.runningCommit}</span>
                    <code className="text-sm font-mono text-fg">{shortCommit(view.running_commit)}</code>
                    {view.running_commit !== 'unknown' && (
                      <button
                        onClick={() => handleCopyCommit(view.running_commit)}
                        className="text-xs text-accent-text hover:text-accent-text"
                        title={view.running_commit}
                      >
                        {t.copyHash}
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted w-36">{t.runningBranch}</span>
                    <span className="text-sm text-fg">{view.running_branch}</span>
                  </div>
                </div>
              </div>

              {/* Remote card */}
              <div className="bg-surface rounded-lg shadow border border-rule p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-fg">{t.trackedRepo}</h2>
                  <button
                    onClick={handleCheckNow}
                    disabled={checking || !view.repo_url}
                    className="px-3 py-1.5 text-sm font-medium text-accent-text bg-accent-wash rounded-lg hover:bg-accent-wash disabled:opacity-50 transition-colors"
                  >
                    {checking ? t.checking : t.checkNow}
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted w-36">{t.repository}</span>
                    <span className="text-sm text-fg break-all">
                      {view.repo_url || <span className="text-subtle">{t.notConfigured}</span>}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted w-36">{t.trackedBranch}</span>
                    <span className="text-sm text-fg">{view.tracked_branch}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted w-36">{t.latestCommit}</span>
                    <code className="text-sm font-mono text-fg">{shortCommit(view.remote_commit)}</code>
                    {view.remote_checked_at && (
                      <span className="text-xs text-muted">
                        {t.checkedAt(when(view.remote_checked_at))}
                      </span>
                    )}
                  </div>
                  {view.remote_error && (
                    <div className="p-3 bg-danger-wash border border-danger-line rounded-lg">
                      <p className="text-sm text-danger-text">
                        <strong>{t.checkFailedLabel}</strong>{' '}
                        {isRepoNotConfigured(view.remote_error) ? t.repoNotConfigured : view.remote_error}
                      </p>
                      {isRepoNotConfigured(view.remote_error) && (
                        <p className="mt-1 text-xs text-muted">
                          {t.technicalDetail} <code>{view.remote_error}</code>
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Scheduled update */}
              <div className="bg-surface rounded-lg shadow border border-rule p-6">
                <h2 className="text-lg font-semibold text-fg mb-4">{t.scheduledUpdate}</h2>
                {view.last_schedule_result &&
                  ['missed', 'skipped_lock'].includes(view.last_schedule_result.outcome ?? '') &&
                  dismissedResult !== view.last_schedule_result.resolved_at && (
                    <div className="p-3 mb-4 bg-warn-wash border border-warn-line rounded-lg flex items-start justify-between gap-3">
                      <p className="text-sm text-warn-text">
                        <strong>
                          {t.missedBefore}
                          {view.last_schedule_result.scheduled_at
                            ? when(view.last_schedule_result.scheduled_at)
                            : t.earlierTime}
                          {t.missedAfter}
                        </strong>{' '}
                        {view.last_schedule_result.detail}
                      </p>
                      <button
                        onClick={() => setDismissedResult(view.last_schedule_result?.resolved_at ?? '')}
                        className="text-xs text-warn-text hover:text-warn-text shrink-0"
                      >
                        {t.dismiss}
                      </button>
                    </div>
                  )}
                {view.schedule ? (
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-muted">
                      {t.scheduledBefore}
                      <strong>{when(view.schedule.scheduled_at)}</strong>
                      {t.scheduledAfter}
                      {view.schedule.scheduled_by_name && t.scheduledBy(view.schedule.scheduled_by_name)}
                      {t.scheduledTail}
                    </p>
                    <button
                      onClick={() => setShowCancelScheduleConfirm(true)}
                      disabled={cancellingSchedule}
                      className="px-4 py-2 text-sm font-medium text-danger-text bg-danger-wash rounded-lg hover:bg-danger-wash disabled:opacity-50 transition-colors shrink-0"
                    >
                      {cancellingSchedule ? t.cancelling : t.cancelSchedule}
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleSchedule} className="space-y-3">
                    <div className="flex flex-wrap items-end gap-4">
                      <div className="flex-1 min-w-[200px] max-w-xs">
                        <label htmlFor="update-schedule-date" className="block text-sm font-medium text-body mb-1">
                          {t.dateTime}
                        </label>
                        <input
                          id="update-schedule-date"
                          type="datetime-local"
                          value={scheduleDate}
                          onChange={(e) => setScheduleDate(e.target.value)}
                          className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm"
                          required
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={!!updateDisabledReason || scheduling || !scheduleDate}
                        className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50 transition-colors"
                      >
                        {scheduling ? t.scheduling : t.scheduleUpdate}
                      </button>
                    </div>
                    <p className="text-sm text-muted">
                      {updateDisabledReason ?? t.scheduleExplain}
                    </p>
                  </form>
                )}
              </div>

              {/* Last update run */}
              {state && state.status !== 'idle' && (
                <div className="bg-surface rounded-lg shadow border border-rule p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-fg">
                      {runInProgress ? t.inProgress : t.lastUpdate}
                    </h2>
                    {state.status === 'success' && <Badge color="green" pill>{t.success}</Badge>}
                    {state.status === 'failed' && <Badge color="red" pill>{t.failed}</Badge>}
                    {state.status === 'rolled_back' && <Badge color="yellow" pill>{t.rolledBack}</Badge>}
                    {runInProgress && <Badge color="blue" pill>{t.running}</Badge>}
                  </div>
                  <div className="space-y-3">
                    {runInProgress && state.phase && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-muted w-36">{t.phase}</span>
                        <span className="text-sm text-fg">
                          {t.phases[state.phase] || state.phase}…
                        </span>
                      </div>
                    )}
                    {state.from_commit && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-muted w-36">{t.fromTo}</span>
                        <code className="text-sm font-mono text-fg">
                          {shortCommit(state.from_commit)} → {shortCommit(state.to_commit)}
                        </code>
                      </div>
                    )}
                    {state.requested_by && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-muted w-36">{t.requestedBy}</span>
                        <span className="text-sm text-fg">{state.requested_by_name || state.requested_by}</span>
                      </div>
                    )}
                    {state.finished_at && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-muted w-36">{t.finished}</span>
                        <span className="text-sm text-fg">{when(state.finished_at)}</span>
                      </div>
                    )}
                    {state.error && (
                      <div className="p-3 bg-danger-wash border border-danger-line rounded-lg">
                        <p className="text-sm text-danger-text whitespace-pre-wrap">{state.error}</p>
                      </div>
                    )}
                    {state.status === 'success' && (
                      <div className="p-3 bg-success-wash border border-success-line rounded-lg flex items-center justify-between gap-3">
                        <p className="text-sm text-success-text">
                          {t.updatedReload}
                        </p>
                        <button
                          onClick={() => window.location.reload()}
                          className="px-3 py-1.5 text-sm font-medium text-on-accent bg-success rounded-lg hover:bg-success-hover transition-colors shrink-0"
                        >
                          {t.reload}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="bg-surface rounded-lg shadow border border-rule p-6">
                <h2 className="text-lg font-semibold text-fg mb-4">{t.actions}</h2>
                <button
                  onClick={() => setShowUpdateConfirm(true)}
                  disabled={!!updateDisabledReason || triggering || !view.update_available}
                  className="px-4 py-2 text-sm font-medium text-on-accent bg-danger rounded-lg hover:bg-danger-hover disabled:opacity-50 transition-colors"
                >
                  {triggering ? t.requesting : t.updateNow}
                </button>
                {updateDisabledReason ? (
                  <p className="text-sm text-muted mt-2">{updateDisabledReason}</p>
                ) : !view.update_available ? (
                  <p className="text-sm text-muted mt-2">{t.alreadyUpToDate}</p>
                ) : (
                  <p className="text-sm text-muted mt-2">
                    {t.updatesToBefore}<code className="font-mono">{shortCommit(view.remote_commit)}</code>{t.updatesToMid}
                    <code className="font-mono">{view.tracked_branch}</code>{t.updatesToAfter}
                  </p>
                )}
              </div>

              {/* Info */}
              <div className="bg-canvas rounded-lg border border-rule p-6">
                <h2 className="text-sm font-semibold text-fg mb-3">{t.howTitle}</h2>
                <ul className="text-sm text-muted space-y-2">
                  <li>
                    <strong>{t.downtime}</strong>{t.downtimeText}
                  </li>
                  <li>
                    <strong>{t.rollback}</strong>{t.rollbackText}
                  </li>
                  <li>
                    <strong>{t.migrations}</strong>{t.migrationsBefore}<em>{t.migrationsNot}</em>{t.migrationsAfter}
                  </li>
                  <li>
                    <strong>{t.configuration}</strong>{t.configBefore}
                    <code className="px-1.5 py-0.5 bg-sunken rounded text-xs font-mono">SYSTEM_REPO_URL</code> /{' '}
                    <code className="px-1.5 py-0.5 bg-sunken rounded text-xs font-mono">SYSTEM_REPO_BRANCH</code>{t.configIn}
                    <code className="px-1.5 py-0.5 bg-sunken rounded text-xs font-mono">.env</code>{t.configAfter}
                  </li>
                </ul>
              </div>
            </>
          )}
        </ScrollArea>

        <ConfirmDialog
          open={showCancelScheduleConfirm}
          title={t.cancelTitle}
          message={t.cancelMessage}
          confirmLabel={t.cancelConfirm}
          variant="danger"
          onConfirm={handleCancelSchedule}
          onCancel={() => setShowCancelScheduleConfirm(false)}
        />

        <ConfirmDialog
          open={showUpdateConfirm}
          title={t.updateTitle}
          message={t.updateMessage}
          confirmLabel={t.updateConfirm}
          variant="danger"
          onConfirm={handleTriggerUpdate}
          onCancel={() => setShowUpdateConfirm(false)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

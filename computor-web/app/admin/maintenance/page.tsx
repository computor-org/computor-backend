'use client';

import { useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { MaintenanceClient } from '@/src/clients/MaintenanceClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';

const maintenanceClient = new MaintenanceClient();

const COPY = {
  de: {
    defaultActivateMessage: 'Das System wird gerade planmäßig gewartet.',
    defaultScheduleMessage: 'Eine Wartung ist geplant.',
    activated: 'Wartungsmodus aktiviert',
    activateFailed: 'Aktivierung fehlgeschlagen',
    deactivated: 'Wartungsmodus deaktiviert',
    deactivateFailed: 'Deaktivierung fehlgeschlagen',
    scheduled: 'Wartung geplant',
    scheduleFailed: 'Planung fehlgeschlagen',
    cancelled: 'Geplante Wartung abgebrochen',
    cancelFailed: 'Planung konnte nicht abgebrochen werden',
    denied: 'Zugriff verweigert',
    adminRequired: 'Für diese Seite sind Administratorrechte erforderlich.',
    breadcrumb: 'Wartung',
    title: 'Wartungsmodus',
    subtitle: 'Verwalte den Wartungszustand des Systems und plane künftige Wartungsfenster.',
    currentStatus: 'Aktueller Status',
    status: 'Status:',
    active: 'Aktiv',
    inactive: 'Inaktiv',
    message: 'Nachricht:',
    activatedAt: 'Aktiviert am:',
    activatedBy: 'Aktiviert von:',
    scheduledMaintenance: 'Geplante Wartung',
    plannedFor: (when: string) => `Geplant für: ${when}`,
    scheduledBy: (who: string) => `Geplant von: ${who}`,
    actions: 'Aktionen',
    activeNote: 'Der Wartungsmodus ist derzeit aktiv. Benutzer ohne Adminrechte können keine Schreibvorgänge ausführen.',
    deactivating: 'Wird deaktiviert…',
    deactivate: 'Wartung deaktivieren',
    maintenanceMessage: 'Wartungsnachricht',
    messagePlaceholder: 'Nachricht, die Benutzern während der Wartung angezeigt wird…',
    activating: 'Wird aktiviert…',
    activate: 'Wartung aktivieren',
    scheduleHeading: 'Wartung planen',
    scheduledFor: (when: string) => `Die Wartung ist für ${when} geplant.`,
    cancelling: 'Wird abgebrochen…',
    cancelSchedule: 'Planung abbrechen',
    dateTime: 'Datum und Uhrzeit',
    messageLabel: 'Nachricht',
    schedulePlaceholder: 'Nachricht zur Planung…',
    scheduling: 'Wird geplant…',
    howTitle: 'So funktioniert der Wartungsmodus',
    apiLevel: 'Wartung auf API-Ebene:',
    apiLevelText: ' Blockiert POST-, PUT-, PATCH- und DELETE-Anfragen von Benutzern ohne Adminrechte. GET-Anfragen bleiben für den schreibgeschützten Zugriff verfügbar.',
    adminAccess: 'Admin-Zugriff:',
    adminAccessText: ' Admins sind nicht betroffen und können weiterhin alle Endpunkte nutzen.',
    ws: 'WebSocket-Benachrichtigung:',
    wsText: ' Alle verbundenen Benutzer werden per WebSocket benachrichtigt, wenn die Wartung aktiviert, deaktiviert, geplant oder abgebrochen wird.',
    full: 'Vollständige Infrastrukturwartung:',
    fullBefore: ' Für vollständige Abschaltungen (Docker-Container stoppen) verwende das Skript ',
    fullAfter: ' auf dem Server. Es liefert über Traefik eine statische Wartungsseite aus.',
    activateTitle: 'Wartungsmodus aktivieren',
    activateConfirmMessage: 'Dadurch werden alle Schreibvorgänge für Benutzer ohne Adminrechte blockiert. Verbundene Benutzer werden per WebSocket benachrichtigt. Bist du sicher?',
    activateConfirm: 'Aktivieren',
    deactivateTitle: 'Wartungsmodus deaktivieren',
    deactivateConfirmMessage: 'Dadurch steht der volle Dienst wieder allen Benutzern zur Verfügung. Verbundene Benutzer werden benachrichtigt.',
    deactivateConfirm: 'Deaktivieren',
    cancelTitle: 'Geplante Wartung abbrechen',
    cancelConfirmMessage: 'Dadurch wird das geplante Wartungsfenster abgebrochen. Verbundene Benutzer werden benachrichtigt.',
  },
  en: {
    defaultActivateMessage: 'The system is undergoing scheduled maintenance.',
    defaultScheduleMessage: 'Scheduled maintenance is planned.',
    activated: 'Maintenance mode activated',
    activateFailed: 'Failed to activate',
    deactivated: 'Maintenance mode deactivated',
    deactivateFailed: 'Failed to deactivate',
    scheduled: 'Maintenance scheduled',
    scheduleFailed: 'Failed to schedule',
    cancelled: 'Scheduled maintenance cancelled',
    cancelFailed: 'Failed to cancel schedule',
    denied: 'Access Denied',
    adminRequired: 'Admin privileges are required to access this page.',
    breadcrumb: 'Maintenance',
    title: 'Maintenance mode',
    subtitle: 'Manage system maintenance state and schedule future maintenance windows.',
    currentStatus: 'Current Status',
    status: 'Status:',
    active: 'Active',
    inactive: 'Inactive',
    message: 'Message:',
    activatedAt: 'Activated at:',
    activatedBy: 'Activated by:',
    scheduledMaintenance: 'Scheduled Maintenance',
    plannedFor: (when: string) => `Planned for: ${when}`,
    scheduledBy: (who: string) => `Scheduled by: ${who}`,
    actions: 'Actions',
    activeNote: 'Maintenance mode is currently active. Non-admin users cannot perform write operations.',
    deactivating: 'Deactivating...',
    deactivate: 'Deactivate Maintenance',
    maintenanceMessage: 'Maintenance Message',
    messagePlaceholder: 'Message shown to users during maintenance...',
    activating: 'Activating...',
    activate: 'Activate Maintenance',
    scheduleHeading: 'Schedule Maintenance',
    scheduledFor: (when: string) => `Maintenance is scheduled for ${when}.`,
    cancelling: 'Cancelling...',
    cancelSchedule: 'Cancel Schedule',
    dateTime: 'Date & Time',
    messageLabel: 'Message',
    schedulePlaceholder: 'Schedule message...',
    scheduling: 'Scheduling...',
    howTitle: 'How Maintenance Mode Works',
    apiLevel: 'API-Level Maintenance:',
    apiLevelText: ' Blocks POST, PUT, PATCH, DELETE requests for non-admin users. GET requests remain available for read-only access.',
    adminAccess: 'Admin Access:',
    adminAccessText: ' Admin users are not affected and can continue using all endpoints.',
    ws: 'WebSocket Notification:',
    wsText: ' All connected users are notified via WebSocket when maintenance is activated, deactivated, scheduled, or cancelled.',
    full: 'Full Infrastructure Maintenance:',
    fullBefore: ' For complete shutdowns (stopping Docker containers), use the ',
    fullAfter: ' script on the server. This serves a static maintenance page via Traefik.',
    activateTitle: 'Activate Maintenance Mode',
    activateConfirmMessage: 'This will block all write operations for non-admin users. Connected users will be notified via WebSocket. Are you sure?',
    activateConfirm: 'Activate',
    deactivateTitle: 'Deactivate Maintenance Mode',
    deactivateConfirmMessage: 'This will restore full service for all users. Connected users will be notified.',
    deactivateConfirm: 'Deactivate',
    cancelTitle: 'Cancel Scheduled Maintenance',
    cancelConfirmMessage: 'This will cancel the scheduled maintenance window. Connected users will be notified.',
  },
};

export default function MaintenancePage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const when = (value: string) => formatDateTime(value, language);
  const { isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const notify = useNotify();

  // Poll the maintenance status every 10s in the background (silent — no loading
  // flash). Mutations below refresh it immediately via `fetchStatus`.
  const { data: status, loading, error, reload: fetchStatus } = useResource(
    () => maintenanceClient.getStatus(),
    [],
    { refetchInterval: 10000 },
  );

  // Activate form
  // null until edited, so the default follows the interface language.
  const [activateEdit, setActivateEdit] = useState<string | null>(null);
  const activateMessage = activateEdit ?? t.defaultActivateMessage;
  const [showActivateConfirm, setShowActivateConfirm] = useState(false);
  const [activating, setActivating] = useState(false);

  // Deactivate confirm
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  // Schedule form
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleEdit, setScheduleEdit] = useState<string | null>(null);
  const scheduleMessage = scheduleEdit ?? t.defaultScheduleMessage;
  const [scheduling, setScheduling] = useState(false);

  // Cancel schedule confirm
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const handleActivate = async () => {
    setShowActivateConfirm(false);
    setActivating(true);
    try {
      await maintenanceClient.activate(activateMessage);
      notify(t.activated, 'success');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.activateFailed, 'error');
    } finally {
      setActivating(false);
    }
  };

  const handleDeactivate = async () => {
    setShowDeactivateConfirm(false);
    setDeactivating(true);
    try {
      await maintenanceClient.deactivate();
      notify(t.deactivated, 'success');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.deactivateFailed, 'error');
    } finally {
      setDeactivating(false);
    }
  };

  const handleSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduleDate) return;

    setScheduling(true);
    try {
      const isoDate = new Date(scheduleDate).toISOString();
      await maintenanceClient.schedule(isoDate, scheduleMessage);
      notify(t.scheduled, 'success');
      setScheduleDate('');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.scheduleFailed, 'error');
    } finally {
      setScheduling(false);
    }
  };

  const handleCancelSchedule = async () => {
    setShowCancelConfirm(false);
    setCancelling(true);
    try {
      await maintenanceClient.cancelSchedule();
      notify(t.cancelled, 'success');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.cancelFailed, 'error');
    } finally {
      setCancelling(false);
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

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.breadcrumb }]}
          title={t.title}
          subtitle={t.subtitle}
        />

        {/* Error */}
        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
        {/* Loading */}
        {loading && (
          <div className="bg-surface rounded-lg border border-rule p-6 animate-pulse">
            <div className="h-6 bg-sunken rounded w-1/4 mb-4" />
            <div className="h-4 bg-sunken rounded w-1/2" />
          </div>
        )}

        {/* Status Card */}
        {!loading && status && (
          <div className="bg-surface rounded-lg shadow border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-4">{t.currentStatus}</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-muted">{t.status}</span>
                {status.active ? (
                  <Badge color="yellow" pill>{t.active}</Badge>
                ) : (
                  <Badge color="green" pill>{t.inactive}</Badge>
                )}
              </div>

              {status.active && (
                <>
                  <div className="flex items-start gap-3">
                    <span className="text-sm font-medium text-muted">{t.message}</span>
                    <span className="text-sm text-fg">{status.message}</span>
                  </div>
                  {status.activated_at && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-muted">{t.activatedAt}</span>
                      <span className="text-sm text-fg">{when(status.activated_at)}</span>
                    </div>
                  )}
                  {status.activated_by && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-muted">{t.activatedBy}</span>
                      <span className="text-sm text-fg">{status.activated_by_name || status.activated_by}</span>
                    </div>
                  )}
                </>
              )}

              {status.scheduled_at && (
                <div className="mt-4 p-3 bg-accent-wash border border-accent-line rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="h-4 w-4 text-accent-text" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-accent-text">{t.scheduledMaintenance}</span>
                  </div>
                  <p className="text-sm text-accent-text">
                    {t.plannedFor(when(status.scheduled_at))}
                  </p>
                  {status.scheduled_by && (
                    <p className="text-xs text-accent-text mt-1">{t.scheduledBy(status.scheduled_by_name || status.scheduled_by)}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        {!loading && status && (
          <div className="bg-surface rounded-lg shadow border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-4">{t.actions}</h2>
            <div className="space-y-6">
              {/* Activate / Deactivate */}
              {status.active ? (
                <div>
                  <p className="text-sm text-muted mb-3">
                    {t.activeNote}
                  </p>
                  <button
                    onClick={() => setShowDeactivateConfirm(true)}
                    disabled={deactivating}
                    className="px-4 py-2 text-sm font-medium text-on-accent bg-success rounded-lg hover:bg-success-hover disabled:opacity-50 transition-colors"
                  >
                    {deactivating ? t.deactivating : t.deactivate}
                  </button>
                </div>
              ) : (
                <div>
                  <label htmlFor="activate-message" className="block text-sm font-medium text-body mb-1">
                    {t.maintenanceMessage}
                  </label>
                  <textarea
                    id="activate-message"
                    value={activateMessage}
                    onChange={(e) => setActivateEdit(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm mb-3"
                    placeholder={t.messagePlaceholder}
                  />
                  <button
                    onClick={() => setShowActivateConfirm(true)}
                    disabled={activating}
                    className="px-4 py-2 text-sm font-medium text-on-accent bg-danger rounded-lg hover:bg-danger-hover disabled:opacity-50 transition-colors"
                  >
                    {activating ? t.activating : t.activate}
                  </button>
                </div>
              )}

              {/* Divider */}
              <hr className="border-rule" />

              {/* Schedule */}
              <div>
                <h3 className="text-sm font-semibold text-fg mb-3">{t.scheduleHeading}</h3>
                {status.scheduled_at ? (
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-muted">
                      {t.scheduledFor(when(status.scheduled_at))}
                    </p>
                    <button
                      onClick={() => setShowCancelConfirm(true)}
                      disabled={cancelling}
                      className="px-4 py-2 text-sm font-medium text-danger-text bg-danger-wash rounded-lg hover:bg-danger-wash disabled:opacity-50 transition-colors"
                    >
                      {cancelling ? t.cancelling : t.cancelSchedule}
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleSchedule} className="space-y-3">
                    <div className="flex flex-wrap gap-4">
                      <div className="flex-1 min-w-[200px]">
                        <label htmlFor="schedule-date" className="block text-sm font-medium text-body mb-1">
                          {t.dateTime}
                        </label>
                        <input
                          id="schedule-date"
                          type="datetime-local"
                          value={scheduleDate}
                          onChange={(e) => setScheduleDate(e.target.value)}
                          className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm"
                          required
                        />
                      </div>
                      <div className="flex-1 min-w-[200px]">
                        <label htmlFor="schedule-message" className="block text-sm font-medium text-body mb-1">
                          {t.messageLabel}
                        </label>
                        <input
                          id="schedule-message"
                          type="text"
                          value={scheduleMessage}
                          onChange={(e) => setScheduleEdit(e.target.value)}
                          className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm"
                          placeholder={t.schedulePlaceholder}
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={scheduling}
                      className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50 transition-colors"
                    >
                      {scheduling ? t.scheduling : t.scheduleHeading}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="bg-canvas rounded-lg border border-rule p-6">
          <h2 className="text-sm font-semibold text-fg mb-3">{t.howTitle}</h2>
          <ul className="text-sm text-muted space-y-2">
            <li>
              <strong>{t.apiLevel}</strong>{t.apiLevelText}
            </li>
            <li>
              <strong>{t.adminAccess}</strong>{t.adminAccessText}
            </li>
            <li>
              <strong>{t.ws}</strong>{t.wsText}
            </li>
            <li>
              <strong>{t.full}</strong>{t.fullBefore}<code className="px-1.5 py-0.5 bg-sunken rounded text-xs font-mono">./maintenance.sh</code>{t.fullAfter}
            </li>
          </ul>
        </div>
        </ScrollArea>

        {/* Confirm Dialogs */}
        <ConfirmDialog
          open={showActivateConfirm}
          title={t.activateTitle}
          message={t.activateConfirmMessage}
          confirmLabel={t.activateConfirm}
          variant="danger"
          onConfirm={handleActivate}
          onCancel={() => setShowActivateConfirm(false)}
        />

        <ConfirmDialog
          open={showDeactivateConfirm}
          title={t.deactivateTitle}
          message={t.deactivateConfirmMessage}
          confirmLabel={t.deactivateConfirm}
          variant="default"
          onConfirm={handleDeactivate}
          onCancel={() => setShowDeactivateConfirm(false)}
        />

        <ConfirmDialog
          open={showCancelConfirm}
          title={t.cancelTitle}
          message={t.cancelConfirmMessage}
          confirmLabel={t.cancelSchedule}
          variant="danger"
          onConfirm={handleCancelSchedule}
          onCancel={() => setShowCancelConfirm(false)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

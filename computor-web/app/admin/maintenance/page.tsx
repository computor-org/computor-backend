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

const maintenanceClient = new MaintenanceClient();

export default function MaintenancePage() {
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
  const [activateMessage, setActivateMessage] = useState('The system is undergoing scheduled maintenance.');
  const [showActivateConfirm, setShowActivateConfirm] = useState(false);
  const [activating, setActivating] = useState(false);

  // Deactivate confirm
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  // Schedule form
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleMessage, setScheduleMessage] = useState('Scheduled maintenance is planned.');
  const [scheduling, setScheduling] = useState(false);

  // Cancel schedule confirm
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const handleActivate = async () => {
    setShowActivateConfirm(false);
    setActivating(true);
    try {
      await maintenanceClient.activate(activateMessage);
      notify('Maintenance mode activated', 'success');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to activate', 'error');
    } finally {
      setActivating(false);
    }
  };

  const handleDeactivate = async () => {
    setShowDeactivateConfirm(false);
    setDeactivating(true);
    try {
      await maintenanceClient.deactivate();
      notify('Maintenance mode deactivated', 'success');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to deactivate', 'error');
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
      notify('Maintenance scheduled', 'success');
      setScheduleDate('');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to schedule', 'error');
    } finally {
      setScheduling(false);
    }
  };

  const handleCancelSchedule = async () => {
    setShowCancelConfirm(false);
    setCancelling(true);
    try {
      await maintenanceClient.cancelSchedule();
      notify('Scheduled maintenance cancelled', 'success');
      await fetchStatus();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to cancel schedule', 'error');
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
            <h2 className="text-lg font-semibold text-danger-text">Access Denied</h2>
            <p className="text-sm text-danger-text mt-2">Admin privileges are required to access this page.</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Maintenance' }]}
          title="Maintenance mode"
          subtitle="Manage system maintenance state and schedule future maintenance windows."
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
            <h2 className="text-lg font-semibold text-fg mb-4">Current Status</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-muted">Status:</span>
                {status.active ? (
                  <Badge color="yellow" pill>Active</Badge>
                ) : (
                  <Badge color="green" pill>Inactive</Badge>
                )}
              </div>

              {status.active && (
                <>
                  <div className="flex items-start gap-3">
                    <span className="text-sm font-medium text-muted">Message:</span>
                    <span className="text-sm text-fg">{status.message}</span>
                  </div>
                  {status.activated_at && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-muted">Activated at:</span>
                      <span className="text-sm text-fg">{new Date(status.activated_at).toLocaleString()}</span>
                    </div>
                  )}
                  {status.activated_by && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-muted">Activated by:</span>
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
                    <span className="text-sm font-medium text-accent-text">Scheduled Maintenance</span>
                  </div>
                  <p className="text-sm text-accent-text">
                    Planned for: {new Date(status.scheduled_at).toLocaleString()}
                  </p>
                  {status.scheduled_by && (
                    <p className="text-xs text-accent-text mt-1">Scheduled by: {status.scheduled_by_name || status.scheduled_by}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        {!loading && status && (
          <div className="bg-surface rounded-lg shadow border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-4">Actions</h2>
            <div className="space-y-6">
              {/* Activate / Deactivate */}
              {status.active ? (
                <div>
                  <p className="text-sm text-muted mb-3">
                    Maintenance mode is currently active. Non-admin users cannot perform write operations.
                  </p>
                  <button
                    onClick={() => setShowDeactivateConfirm(true)}
                    disabled={deactivating}
                    className="px-4 py-2 text-sm font-medium text-on-accent bg-success rounded-lg hover:bg-success-hover disabled:opacity-50 transition-colors"
                  >
                    {deactivating ? 'Deactivating...' : 'Deactivate Maintenance'}
                  </button>
                </div>
              ) : (
                <div>
                  <label htmlFor="activate-message" className="block text-sm font-medium text-body mb-1">
                    Maintenance Message
                  </label>
                  <textarea
                    id="activate-message"
                    value={activateMessage}
                    onChange={(e) => setActivateMessage(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm mb-3"
                    placeholder="Message shown to users during maintenance..."
                  />
                  <button
                    onClick={() => setShowActivateConfirm(true)}
                    disabled={activating}
                    className="px-4 py-2 text-sm font-medium text-on-accent bg-danger rounded-lg hover:bg-danger-hover disabled:opacity-50 transition-colors"
                  >
                    {activating ? 'Activating...' : 'Activate Maintenance'}
                  </button>
                </div>
              )}

              {/* Divider */}
              <hr className="border-rule" />

              {/* Schedule */}
              <div>
                <h3 className="text-sm font-semibold text-fg mb-3">Schedule Maintenance</h3>
                {status.scheduled_at ? (
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-muted">
                      Maintenance is scheduled for {new Date(status.scheduled_at).toLocaleString()}.
                    </p>
                    <button
                      onClick={() => setShowCancelConfirm(true)}
                      disabled={cancelling}
                      className="px-4 py-2 text-sm font-medium text-danger-text bg-danger-wash rounded-lg hover:bg-danger-wash disabled:opacity-50 transition-colors"
                    >
                      {cancelling ? 'Cancelling...' : 'Cancel Schedule'}
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleSchedule} className="space-y-3">
                    <div className="flex flex-wrap gap-4">
                      <div className="flex-1 min-w-[200px]">
                        <label htmlFor="schedule-date" className="block text-sm font-medium text-body mb-1">
                          Date & Time
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
                          Message
                        </label>
                        <input
                          id="schedule-message"
                          type="text"
                          value={scheduleMessage}
                          onChange={(e) => setScheduleMessage(e.target.value)}
                          className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm"
                          placeholder="Schedule message..."
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={scheduling}
                      className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50 transition-colors"
                    >
                      {scheduling ? 'Scheduling...' : 'Schedule Maintenance'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="bg-canvas rounded-lg border border-rule p-6">
          <h2 className="text-sm font-semibold text-fg mb-3">How Maintenance Mode Works</h2>
          <ul className="text-sm text-muted space-y-2">
            <li>
              <strong>API-Level Maintenance:</strong> Blocks POST, PUT, PATCH, DELETE requests for non-admin users. GET requests remain available for read-only access.
            </li>
            <li>
              <strong>Admin Access:</strong> Admin users are not affected and can continue using all endpoints.
            </li>
            <li>
              <strong>WebSocket Notification:</strong> All connected users are notified via WebSocket when maintenance is activated, deactivated, scheduled, or cancelled.
            </li>
            <li>
              <strong>Full Infrastructure Maintenance:</strong> For complete shutdowns (stopping Docker containers), use the <code className="px-1.5 py-0.5 bg-sunken rounded text-xs font-mono">./maintenance.sh</code> script on the server. This serves a static maintenance page via Traefik.
            </li>
          </ul>
        </div>
        </ScrollArea>

        {/* Confirm Dialogs */}
        <ConfirmDialog
          open={showActivateConfirm}
          title="Activate Maintenance Mode"
          message="This will block all write operations for non-admin users. Connected users will be notified via WebSocket. Are you sure?"
          confirmLabel="Activate"
          variant="danger"
          onConfirm={handleActivate}
          onCancel={() => setShowActivateConfirm(false)}
        />

        <ConfirmDialog
          open={showDeactivateConfirm}
          title="Deactivate Maintenance Mode"
          message="This will restore full service for all users. Connected users will be notified."
          confirmLabel="Deactivate"
          variant="default"
          onConfirm={handleDeactivate}
          onCancel={() => setShowDeactivateConfirm(false)}
        />

        <ConfirmDialog
          open={showCancelConfirm}
          title="Cancel Scheduled Maintenance"
          message="This will cancel the scheduled maintenance window. Connected users will be notified."
          confirmLabel="Cancel Schedule"
          variant="danger"
          onConfirm={handleCancelSchedule}
          onCancel={() => setShowCancelConfirm(false)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { MaintenanceClient, MaintenanceStatus } from '@/src/clients/MaintenanceClient';
import Notification from '@/src/components/workspaces/Notification';
import ConfirmDialog from '@/src/components/workspaces/ConfirmDialog';

const maintenanceClient = new MaintenanceClient();

export default function MaintenancePage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [status, setStatus] = useState<MaintenanceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

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

  const fetchStatus = useCallback(async () => {
    try {
      const data = await maintenanceClient.getStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch maintenance status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    fetchStatus();

    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [authLoading, isAuthenticated, fetchStatus]);

  const handleActivate = async () => {
    setShowActivateConfirm(false);
    setActivating(true);
    try {
      await maintenanceClient.activate(activateMessage);
      setNotification({ message: 'Maintenance mode activated', type: 'success' });
      await fetchStatus();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to activate', type: 'error' });
    } finally {
      setActivating(false);
    }
  };

  const handleDeactivate = async () => {
    setShowDeactivateConfirm(false);
    setDeactivating(true);
    try {
      await maintenanceClient.deactivate();
      setNotification({ message: 'Maintenance mode deactivated', type: 'success' });
      await fetchStatus();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to deactivate', type: 'error' });
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
      setNotification({ message: 'Maintenance scheduled', type: 'success' });
      setScheduleDate('');
      await fetchStatus();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to schedule', type: 'error' });
    } finally {
      setScheduling(false);
    }
  };

  const handleCancelSchedule = async () => {
    setShowCancelConfirm(false);
    setCancelling(true);
    try {
      await maintenanceClient.cancelSchedule();
      setNotification({ message: 'Scheduled maintenance cancelled', type: 'success' });
      await fetchStatus();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to cancel schedule', type: 'error' });
    } finally {
      setCancelling(false);
    }
  };

  // Access control
  if (!authLoading && user?.role !== 'admin') {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-red-800">Access Denied</h2>
            <p className="text-sm text-red-600 mt-2">Admin privileges are required to access this page.</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {notification && (
          <Notification message={notification.message} type={notification.type} onClose={() => setNotification(null)} />
        )}

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Maintenance Mode</h1>
          <p className="mt-2 text-gray-600">Manage system maintenance state and schedule future maintenance windows.</p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-4" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Status Card */}
        {!loading && status && (
          <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Status</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-600">Status:</span>
                {status.active ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Inactive
                  </span>
                )}
              </div>

              {status.active && (
                <>
                  <div className="flex items-start gap-3">
                    <span className="text-sm font-medium text-gray-600">Message:</span>
                    <span className="text-sm text-gray-900">{status.message}</span>
                  </div>
                  {status.activated_at && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-600">Activated at:</span>
                      <span className="text-sm text-gray-900">{new Date(status.activated_at).toLocaleString()}</span>
                    </div>
                  )}
                  {status.activated_by && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-600">Activated by:</span>
                      <span className="text-sm text-gray-900">{status.activated_by_name || status.activated_by}</span>
                    </div>
                  )}
                </>
              )}

              {status.scheduled_at && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-blue-800">Scheduled Maintenance</span>
                  </div>
                  <p className="text-sm text-blue-700">
                    Planned for: {new Date(status.scheduled_at).toLocaleString()}
                  </p>
                  {status.scheduled_by && (
                    <p className="text-xs text-blue-600 mt-1">Scheduled by: {status.scheduled_by_name || status.scheduled_by}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        {!loading && status && (
          <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
            <div className="space-y-6">
              {/* Activate / Deactivate */}
              {status.active ? (
                <div>
                  <p className="text-sm text-gray-600 mb-3">
                    Maintenance mode is currently active. Non-admin users cannot perform write operations.
                  </p>
                  <button
                    onClick={() => setShowDeactivateConfirm(true)}
                    disabled={deactivating}
                    className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {deactivating ? 'Deactivating...' : 'Deactivate Maintenance'}
                  </button>
                </div>
              ) : (
                <div>
                  <label htmlFor="activate-message" className="block text-sm font-medium text-gray-700 mb-1">
                    Maintenance Message
                  </label>
                  <textarea
                    id="activate-message"
                    value={activateMessage}
                    onChange={(e) => setActivateMessage(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm mb-3"
                    placeholder="Message shown to users during maintenance..."
                  />
                  <button
                    onClick={() => setShowActivateConfirm(true)}
                    disabled={activating}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    {activating ? 'Activating...' : 'Activate Maintenance'}
                  </button>
                </div>
              )}

              {/* Divider */}
              <hr className="border-gray-200" />

              {/* Schedule */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Schedule Maintenance</h3>
                {status.scheduled_at ? (
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-gray-600">
                      Maintenance is scheduled for {new Date(status.scheduled_at).toLocaleString()}.
                    </p>
                    <button
                      onClick={() => setShowCancelConfirm(true)}
                      disabled={cancelling}
                      className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 disabled:opacity-50 transition-colors"
                    >
                      {cancelling ? 'Cancelling...' : 'Cancel Schedule'}
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleSchedule} className="space-y-3">
                    <div className="flex flex-wrap gap-4">
                      <div className="flex-1 min-w-[200px]">
                        <label htmlFor="schedule-date" className="block text-sm font-medium text-gray-700 mb-1">
                          Date & Time
                        </label>
                        <input
                          id="schedule-date"
                          type="datetime-local"
                          value={scheduleDate}
                          onChange={(e) => setScheduleDate(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                          required
                        />
                      </div>
                      <div className="flex-1 min-w-[200px]">
                        <label htmlFor="schedule-message" className="block text-sm font-medium text-gray-700 mb-1">
                          Message
                        </label>
                        <input
                          id="schedule-message"
                          type="text"
                          value={scheduleMessage}
                          onChange={(e) => setScheduleMessage(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                          placeholder="Schedule message..."
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={scheduling}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
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
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">How Maintenance Mode Works</h2>
          <ul className="text-sm text-gray-600 space-y-2">
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
              <strong>Full Infrastructure Maintenance:</strong> For complete shutdowns (stopping Docker containers), use the <code className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-mono">./maintenance.sh</code> script on the server. This serves a static maintenance page via Traefik.
            </li>
          </ul>
        </div>

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
      </div>
    </AuthenticatedLayout>
  );
}

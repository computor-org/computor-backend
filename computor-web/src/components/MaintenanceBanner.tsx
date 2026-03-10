'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { MaintenanceClient, MaintenanceStatus } from '../clients/MaintenanceClient';

const maintenanceClient = new MaintenanceClient();

type UrgencyLevel = 'low' | 'medium' | 'high';

function getUrgency(minutesRemaining: number): UrgencyLevel {
  if (minutesRemaining <= 5) return 'high';
  if (minutesRemaining <= 10) return 'medium';
  return 'low';
}

const urgencyStyles: Record<UrgencyLevel, { bg: string; border: string; icon: string; text: string; dismiss: string }> = {
  low:    { bg: 'bg-blue-50',  border: 'border-blue-200',  icon: 'text-blue-600',  text: 'text-blue-800',  dismiss: 'text-blue-400 hover:text-blue-600' },
  medium: { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-600', text: 'text-amber-800', dismiss: 'text-amber-400 hover:text-amber-600' },
  high:   { bg: 'bg-red-50',   border: 'border-red-200',   icon: 'text-red-600',   text: 'text-red-800',   dismiss: '' },
};

function formatCountdown(minutes: number): string {
  if (minutes < 1) return 'less than 1 minute';
  if (minutes < 2) return '1 minute';
  return `${Math.floor(minutes)} minutes`;
}

export default function MaintenanceBanner() {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState<MaintenanceStatus | null>(null);
  const [scheduleDismissed, setScheduleDismissed] = useState(false);
  const [minutesRemaining, setMinutesRemaining] = useState<number | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await maintenanceClient.getStatus();
      setStatus(data);
      // Reset dismiss when schedule changes
      if (!data.scheduled_at) {
        setScheduleDismissed(false);
        setMinutesRemaining(null);
      }
    } catch {
      // Silently ignore — don't block UI if maintenance endpoint is unavailable
    }
  }, []);

  // Poll maintenance status every 30s
  useEffect(() => {
    if (!isAuthenticated) return;

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, fetchStatus]);

  // Update countdown every 10 seconds for smooth display
  useEffect(() => {
    if (!status?.scheduled_at) {
      setMinutesRemaining(null);
      return;
    }

    const updateCountdown = () => {
      const remaining = (new Date(status.scheduled_at!).getTime() - Date.now()) / 60000;
      setMinutesRemaining(remaining > 0 ? remaining : 0);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 10000);
    return () => clearInterval(interval);
  }, [status?.scheduled_at]);

  if (!status) return null;

  // Active maintenance — amber banner, not dismissible
  if (status.active) {
    return (
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-2">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-sm text-amber-800">
            <span className="font-medium">Maintenance Mode Active</span>
            {status.message && <> — {status.message}</>}
          </p>
        </div>
      </div>
    );
  }

  // Scheduled maintenance with countdown
  if (status.scheduled_at && minutesRemaining !== null) {
    const urgency = getUrgency(minutesRemaining);
    const styles = urgencyStyles[urgency];
    const canDismiss = urgency !== 'high';

    // Non-dismissible at high urgency — override previous dismiss
    if (scheduleDismissed && canDismiss) return null;

    return (
      <div className={`${styles.bg} border-b ${styles.border} px-4 py-2`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className={`h-4 w-4 ${styles.icon} shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className={`text-sm ${styles.text}`}>
              <span className="font-medium">Maintenance in {formatCountdown(minutesRemaining)}</span>
              {' '} — {new Date(status.scheduled_at).toLocaleString()}
            </p>
          </div>
          {canDismiss && !scheduleDismissed && (
            <button
              onClick={() => setScheduleDismissed(true)}
              className={`${styles.dismiss} p-1`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    );
  }

  return null;
}

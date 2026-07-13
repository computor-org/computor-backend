'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

type NotificationType = 'success' | 'error' | 'warning' | 'info';

interface NotificationProps {
  message: string;
  type: NotificationType;
  onClose: () => void;
  duration?: number;
}

// Exit-transition length; keep in sync with the `duration-300` class below.
const EXIT_MS = 300;

const typeStyles: Record<NotificationType, { bg: string; icon: string; text: string }> = {
  success: { bg: 'bg-green-50 border-green-200', icon: 'text-green-500', text: 'text-green-800' },
  error: { bg: 'bg-red-50 border-red-200', icon: 'text-red-500', text: 'text-red-800' },
  warning: { bg: 'bg-yellow-50 border-yellow-200', icon: 'text-yellow-500', text: 'text-yellow-800' },
  info: { bg: 'bg-blue-50 border-blue-200', icon: 'text-blue-500', text: 'text-blue-800' },
};

const typeIcons: Record<NotificationType, React.ReactElement> = {
  success: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  error: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  warning: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  info: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

/**
 * A single toast card. Position-agnostic — rendering and stacking is owned by
 * NotificationProvider; page code should call useNotify() rather than
 * rendering this directly.
 */
export default function Notification({ message, type, onClose, duration = 5000 }: NotificationProps) {
  // `visible` drives the enter transition; `leaving` drives the exit one.
  const [visible, setVisible] = useState(false);
  const [leaving, setLeaving] = useState(false);

  // Hold the latest onClose in a ref so the auto-dismiss timer below can run
  // once and NOT reset when the provider re-renders (adding another toast hands
  // every sibling a fresh onClose identity — depending on it would restart all
  // their timers, making them expire together instead of on their own clock).
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const exitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Start the exit transition, then actually unmount once it has played.
  const startLeave = useCallback(() => {
    setLeaving((already) => {
      if (already) return already; // guard double-trigger (timer + manual close)
      exitTimer.current = setTimeout(() => onCloseRef.current(), EXIT_MS);
      return true;
    });
  }, []);

  useEffect(() => {
    // Flip to visible on the next frame so the enter transition plays.
    const raf = requestAnimationFrame(() => setVisible(true));
    // Independent per-toast auto-dismiss; stable deps → never reset by siblings.
    const dismiss = setTimeout(startLeave, duration);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(dismiss);
      if (exitTimer.current) clearTimeout(exitTimer.current);
    };
  }, [duration, startLeave]);

  const styles = typeStyles[type];
  const shown = visible && !leaving;

  return (
    <div
      className={`max-w-sm border rounded-lg p-4 shadow-lg transition-all duration-300 ease-out ${styles.bg} ${
        shown ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className={styles.icon}>{typeIcons[type]}</span>
        <p className={`text-sm font-medium flex-1 ${styles.text}`}>{message}</p>
        <button onClick={startLeave} aria-label="Dismiss notification" className="text-gray-400 hover:text-gray-600">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

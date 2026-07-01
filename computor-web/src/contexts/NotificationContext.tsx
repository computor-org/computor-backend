'use client';

import { createContext, useCallback, useContext, useRef, useState, ReactNode } from 'react';
import Notification from '../components/Notification';

type NotificationType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: number;
  message: string;
  type: NotificationType;
}

type Notify = (message: string, type?: NotificationType) => void;

const NotificationContext = createContext<Notify | undefined>(undefined);

/**
 * App-wide toast provider. Call `useNotify()('Saved', 'success')` after a
 * mutation instead of hand-rolling inline message state per page — success
 * and error get distinct colors and auto-dismiss.
 */
export function NotificationProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const notify = useCallback<Notify>((message, type = 'info') => {
    const id = nextId.current++;
    setToasts((ts) => [...ts, { id, message, type }]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
  }, []);

  return (
    <NotificationContext.Provider value={notify}>
      {children}
      <div aria-live="polite" className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <Notification key={t.id} message={t.message} type={t.type} onClose={() => dismiss(t.id)} />
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotify(): Notify {
  const notify = useContext(NotificationContext);
  if (!notify) {
    throw new Error('useNotify must be used within a NotificationProvider');
  }
  return notify;
}

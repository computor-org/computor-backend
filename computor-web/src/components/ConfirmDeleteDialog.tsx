'use client';

import { useState } from 'react';

/**
 * Deliberate, type-to-confirm dialog for destructive deletes. The user must type
 * the entity's identifier to enable the button. `onConfirm` may throw — its error
 * (e.g. "delete its courses first") is shown inline and the dialog stays open, so
 * a blocked cascade is explained in context instead of silently failing.
 */
export default function ConfirmDeleteDialog({
  title,
  message,
  confirmWord,
  onConfirm,
  onClose,
}: {
  title: string;
  message: string;
  confirmWord: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ready = value.trim() === confirmWord && !busy;

  async function go() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      // On success the caller navigates away; leave the dialog as-is.
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-red-700">{title}</h2>
          <p className="text-sm text-gray-600">{message}</p>
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Type <span className="font-mono font-semibold text-gray-900">{confirmWord}</span> to confirm
            </label>
            <input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              autoFocus
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
        </div>
        <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
          <button onClick={onClose} disabled={busy} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={go}
            disabled={!ready}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            {busy ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import Modal from './Modal';
import Button from './ui/Button';

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
    <Modal title={title} titleClassName="text-lg font-semibold text-danger-text" onClose={onClose}>
      <div className="px-6 pb-6 pt-2 space-y-4">
        <p className="text-sm text-muted">{message}</p>
        {error && <div className="p-3 bg-danger-wash border border-danger-line rounded text-sm text-danger-text">{error}</div>}
        <div>
          <label htmlFor="confirm-delete-input" className="block text-xs font-medium text-body mb-1">
            Type <span className="font-mono font-semibold text-fg">{confirmWord}</span> to confirm
          </label>
          <input
            id="confirm-delete-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
            className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
        </div>
      </div>
      <div className="px-6 py-4 bg-canvas rounded-b-lg flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button variant="danger" onClick={go} disabled={!ready}>
          {busy ? 'Deleting…' : 'Delete'}
        </Button>
      </div>
    </Modal>
  );
}

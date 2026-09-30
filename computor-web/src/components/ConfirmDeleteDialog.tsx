'use client';

import { useState, type ReactNode } from 'react';
import Modal from './Modal';
import Button from './ui/Button';
import Notice from './ui/Notice';

/**
 * Deliberate, type-to-confirm dialog for destructive deletes. The user must type
 * the entity's identifier to enable the button. `onConfirm` may throw — its error
 * (e.g. "delete its courses first") is shown inline and the dialog stays open, so
 * a blocked cascade is explained in context instead of silently failing.
 *
 * `preview` (what the delete takes with it — see CascadeDeletePreview) sits
 * between the message and the input. `blockedReason` is the server's answer
 * from a dry run when the real call would be refused: it is shown as a
 * warning and the Delete button stays disabled no matter what is typed, so
 * the reader is told up front instead of after a failed attempt.
 */
export default function ConfirmDeleteDialog({
  title,
  message,
  confirmWord,
  preview,
  blockedReason,
  onConfirm,
  onClose,
}: {
  title: string;
  message: string;
  confirmWord: string;
  preview?: ReactNode;
  blockedReason?: string | null;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const blocked = Boolean(blockedReason);
  const ready = value.trim() === confirmWord && !busy && !blocked;

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
        {preview}
        {blocked && <Notice tone="warning">{blockedReason}</Notice>}
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
            disabled={blocked}
            className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent disabled:opacity-50"
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

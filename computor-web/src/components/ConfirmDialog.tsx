'use client';

import Modal from './Modal';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import Button from './ui/Button';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  /** True while the confirmed action runs, so it cannot be confirmed twice. */
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Simple yes/no confirmation. For irreversible deletes prefer
 * ConfirmDeleteDialog, which requires typing the entity name. */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  variant = 'default',
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const de = useUiLanguage() === 'de';
  if (!open) return null;

  return (
    <Modal title={title} onClose={onCancel}>
      <div className="px-6 pt-2 pb-6">
        <p className="text-sm text-muted mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel}>
            {cancelLabel ?? (de ? 'Abbrechen' : 'Cancel')}
          </Button>
          <Button variant={variant === 'danger' ? 'danger' : 'primary'} disabled={busy} onClick={onConfirm}>
            {confirmLabel ?? (de ? 'Bestätigen' : 'Confirm')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

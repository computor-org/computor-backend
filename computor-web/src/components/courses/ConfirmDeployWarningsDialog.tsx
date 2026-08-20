'use client';

import type { CourseDeployWarning } from '@/src/generated/types/common';
import Modal from '../Modal';
import Button from '../ui/Button';
import { warningText } from './DeploymentCheckReport';

/**
 * Deliberate "yes, create it anyway" gate for a deployment file that validated
 * with warnings. Warnings never block the backend — the course is created with
 * assignments that have no example or no testing service — so the only thing
 * standing between the user and a half-populated course is this dialog. It
 * therefore repeats every warning verbatim instead of summarising them.
 */
export default function ConfirmDeployWarningsDialog({
  warnings,
  courseLabel,
  submitting,
  onConfirm,
  onCancel,
}: {
  warnings: CourseDeployWarning[];
  /** Title or path of the course the file describes. */
  courseLabel: string;
  submitting?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const n = warnings.length;
  return (
    <Modal
      title={`Create this course despite ${n} ${n === 1 ? 'issue' : 'issues'}?`}
      titleClassName="text-lg font-semibold text-warn-text"
      onClose={submitting ? () => {} : onCancel}
      maxWidth="max-w-lg"
    >
      <div className="px-6 pt-2 pb-6 space-y-3">
        <p className="text-sm text-muted">
          <span className="font-medium text-fg">{courseLabel}</span> will be created, but{' '}
          {n === 1 ? 'this part is' : 'these parts are'} incomplete. Affected assignments end up
          without an example or without a testing service, so students can’t work on them until you
          fix that by hand.
        </p>
        <ul className="list-disc pl-5 space-y-1 max-h-64 overflow-y-auto text-sm text-warn-text">
          {warnings.map((w, i) => (
            <li key={i}>{warningText(w)}</li>
          ))}
        </ul>
        <p className="text-sm text-muted">
          Correcting the file and uploading it again is usually far less work than repairing the
          course afterwards.
        </p>
      </div>
      <div className="px-6 py-4 bg-canvas rounded-b-lg flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel} disabled={submitting}>
          Cancel — I’ll fix the file
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={submitting} loadingLabel="Creating…">
          Create anyway
        </Button>
      </div>
    </Modal>
  );
}

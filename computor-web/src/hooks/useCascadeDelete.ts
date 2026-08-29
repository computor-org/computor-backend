'use client';

import { useState } from 'react';
import { useNotify } from '@/src/contexts/NotificationContext';
import type { CascadeDeleteResult } from 'types/generated';

/**
 * The two-step delete the hierarchy pages share: preview first, then the real
 * call behind the type-to-confirm dialog.
 *
 * `begin()` runs the delete as a dry run and keeps the result as `preview`;
 * the page renders `ConfirmDeleteDialog` while `preview` is set and feeds it a
 * `CascadeDeletePreview` plus the server's `blocked_reason`, so someone whose
 * delete would be refused (a course with student submissions, a family that
 * still has courses) learns that BEFORE typing the name, not from an error
 * afterwards. `confirm()` is what the dialog awaits: the real delete, then the
 * caller's `afterDelete` (refresh permissions, navigate away).
 *
 * A dry run that fails outright (403 for a non-owner, network) is surfaced as
 * a toast and no dialog opens.
 */
export function useCascadeDelete(
  previewFn: () => Promise<CascadeDeleteResult>,
  deleteFn: () => Promise<unknown>,
  afterDelete: () => Promise<void> | void,
) {
  const notify = useNotify();
  const [preview, setPreview] = useState<CascadeDeleteResult | null>(null);
  const [opening, setOpening] = useState(false);

  async function begin() {
    setOpening(true);
    try {
      setPreview(await previewFn());
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Could not prepare the delete', 'error');
    } finally {
      setOpening(false);
    }
  }

  function close() {
    setPreview(null);
  }

  async function confirm() {
    await deleteFn();
    await afterDelete();
  }

  return { preview, opening, begin, close, confirm };
}

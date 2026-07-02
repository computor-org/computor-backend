/**
 * Single-flight guard for token refresh.
 *
 * Both HTTP layers (`apiFetch` and `APIClient`) refresh on 401; without a
 * shared guard a page mixing them could fire two concurrent `/auth/refresh`
 * calls. All layers funnel through `refreshOnce` so at most one refresh is
 * in flight at any time — concurrent callers await the same promise.
 */
export type RefreshOutcome = 'refreshed' | 'failed' | 'unreachable';

let inflight: Promise<RefreshOutcome> | null = null;

export function refreshOnce(doRefresh: () => Promise<RefreshOutcome>): Promise<RefreshOutcome> {
  if (!inflight) {
    inflight = doRefresh().finally(() => {
      inflight = null;
    });
  }
  return inflight;
}

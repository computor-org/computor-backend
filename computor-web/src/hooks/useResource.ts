'use client';

import { useCallback, useEffect, useState, type DependencyList } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface UseResourceResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  /** Like `reload` but silent — refreshes data without flipping `loading`
   *  (for after-action refreshes that shouldn't flash the page). */
  refresh: () => Promise<void>;
  setData: (value: T | null) => void;
}

/**
 * Standard data-fetching for a page: runs `fetcher` once the user is
 * authenticated (and `enabled`), tracking loading/error and exposing `reload`.
 * Replaces the hand-rolled loading/error/useEffect machine repeated across the
 * app. For multiple endpoints, return a composite object from `fetcher`:
 *
 *   const { data, loading, error, reload } = useResource(
 *     async () => ({ org: await api.get(...), families: await api.get(...) }),
 *     [orgId],
 *   );
 *
 * Pass `refetchInterval` (ms) to poll: `fetcher` re-runs on that cadence in the
 * background WITHOUT toggling `loading` (so the page doesn't flash its loading
 * state on every tick). Explicit `reload()` still shows `loading` as usual.
 */
export function useResource<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList = [],
  opts: { enabled?: boolean; refetchInterval?: number } = {},
): UseResourceResult<T> {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const enabled = opts.enabled ?? true;
  const refetchInterval = opts.refetchInterval;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // `silent` runs power background polling: refresh data/error without flipping
  // `loading`. Explicit reloads (silent === false) behave exactly as before.
  const run = useCallback(async (silent: boolean) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      setData(await fetcher());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      if (!silent) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const reload = useCallback(() => run(false), [run]);
  const refresh = useCallback(() => run(true), [run]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !enabled) return;
    reload();
  }, [authLoading, isAuthenticated, enabled, reload]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !enabled || !refetchInterval) return;
    // Skip ticks while the tab is hidden (no point polling a page nobody sees)
    // and refresh immediately when it becomes visible again.
    const id = setInterval(() => {
      if (!document.hidden) run(true);
    }, refetchInterval);
    const handleVisibility = () => {
      if (!document.hidden) run(true);
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [authLoading, isAuthenticated, enabled, refetchInterval, run]);

  return { data, loading, error, reload, refresh, setData };
}

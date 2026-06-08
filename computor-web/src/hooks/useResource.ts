'use client';

import { useCallback, useEffect, useState, type DependencyList } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface UseResourceResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
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
 */
export function useResource<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList = [],
  opts: { enabled?: boolean } = {},
): UseResourceResult<T> {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const enabled = opts.enabled ?? true;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetcher());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !enabled) return;
    reload();
  }, [authLoading, isAuthenticated, enabled, reload]);

  return { data, loading, error, reload, setData };
}

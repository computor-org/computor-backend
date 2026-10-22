'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import { supportClient, type SupportCapabilities } from '@/src/clients/SupportClient';

// Shared across every consumer (Sidebar, pages) so the endpoint is hit once per
// session. A failed request resolves to null (= no access) and is not retried.
let cached: Promise<SupportCapabilities | null> | null = null;
let cachedFor: string | null = null;

function load(userKey: string): Promise<SupportCapabilities | null> {
  if (!cached || cachedFor !== userKey) {
    cachedFor = userKey;
    cached = supportClient.capabilities().catch(() => null);
  }
  return cached;
}

/** Support capabilities of the current user; `capabilities` is null while loading or on failure. */
export function useSupportCapabilities(): { capabilities: SupportCapabilities | null; loading: boolean } {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const userKey = user?.id ?? '';
  const [state, setState] = useState<{ key: string; caps: SupportCapabilities | null } | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let live = true;
    load(userKey).then((caps) => {
      if (live) setState({ key: userKey, caps });
    });
    return () => {
      live = false;
    };
  }, [authLoading, isAuthenticated, userKey]);

  const ready = state !== null && state.key === userKey;
  return { capabilities: ready ? state.caps : null, loading: authLoading || (isAuthenticated && !ready) };
}

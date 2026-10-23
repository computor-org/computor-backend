'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import { CoderClient } from '@/src/clients/CoderClient';

const coderClient = new CoderClient();

// Shared across every consumer so the listing is read once per session. A
// failed request counts as "no workspace" and is not retried.
let cached: Promise<boolean> | null = null;
let cachedFor: string | null = null;

function load(userKey: string): Promise<boolean> {
  if (!cached || cachedFor !== userKey) {
    cachedFor = userKey;
    cached = coderClient
      .listWorkspaces()
      .then((r) => r.workspaces.length > 0)
      .catch(() => false);
  }
  return cached;
}

/**
 * Whether the user owns at least one workspace. Learners who joined a course
 * themselves hold no workspace role, but they get a workspace through the
 * course and need a way back to it besides the course page. `enabled: false`
 * skips the request (callers already know the answer from a role).
 */
export function useHasOwnWorkspace(enabled: boolean): boolean {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const userKey = user?.id ?? '';
  const [state, setState] = useState<{ key: string; has: boolean } | null>(null);

  useEffect(() => {
    if (!enabled || authLoading || !isAuthenticated) return;
    let live = true;
    load(userKey).then((has) => {
      if (live) setState({ key: userKey, has });
    });
    return () => {
      live = false;
    };
  }, [enabled, authLoading, isAuthenticated, userKey]);

  return enabled && state !== null && state.key === userKey && state.has;
}

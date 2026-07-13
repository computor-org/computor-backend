'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import { RolesClient } from '@/src/generated/clients/RolesClient';
import type { RoleList } from 'types/generated';

const rolesClient = new RolesClient();

// Stable display order for the known builtin roles; anything unrecognised is
// appended afterwards (alphabetically) so a newly-seeded role still shows up.
const ROLE_ORDER = [
  '_admin',
  '_user_manager',
  '_organization_manager',
  '_example_manager',
  '_workspace_user',
  '_workspace_maintainer',
  '_git_manager',
];

function orderOf(id: string): number {
  const i = ROLE_ORDER.indexOf(id);
  return i === -1 ? ROLE_ORDER.length : i;
}

/**
 * Fetches the builtin system roles (`_admin`, `_user_manager`, …) once the user
 * is authenticated, sorted into a stable display order. Pages render each
 * role's `title`/`description` (seeded in the DB) instead of hardcoding the
 * cryptic role ids, so a role's human name lives in one place — the database.
 */
export function useSystemRoles(): { roles: RoleList[]; loading: boolean } {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [roles, setRoles] = useState<RoleList[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const list = await rolesClient.listRolesRolesGet({ builtin: true });
        if (cancelled) return;
        const sorted = [...list].sort(
          (a, b) => orderOf(a.id) - orderOf(b.id) || (a.title ?? a.id).localeCompare(b.title ?? b.id),
        );
        setRoles(sorted);
      } catch {
        if (!cancelled) setRoles([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated]);

  return { roles, loading };
}

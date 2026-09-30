'use client';

import { useSystemRoles } from '@/src/hooks/useSystemRoles';
import { usePermissions } from '@/src/hooks/usePermissions';
import { ADMIN_ROLE_LOCKED_HINT, grantsAdmin } from '@/src/utils/systemRoles';

/**
 * Checkbox list of the builtin system roles, labelled with each role's
 * human-readable `title` and `description` from the database (not the raw
 * `_role_id`). Shared by the user create/detail pages and the invite dialog so
 * the role names live in exactly one place.
 *
 * Admin-conferring roles are greyed out for non-admin viewers: the backend
 * refuses those grants (403 AUTHZ_005), so offering the checkbox only invites
 * a confusing save error (#403).
 */
export default function SystemRoleCheckboxes({
  selected,
  onToggle,
  disabled,
}: {
  selected: string[];
  onToggle: (roleId: string) => void;
  disabled?: boolean;
}) {
  const { roles, loading } = useSystemRoles();
  const { isAdmin } = usePermissions();

  if (loading) return <p className="text-xs text-subtle">Loading roles…</p>;
  if (roles.length === 0) return <p className="text-xs text-subtle">No system roles available.</p>;

  return (
    <div className="space-y-2">
      {roles.map((r) => {
        const locked = !isAdmin && grantsAdmin(r.id);
        return (
          <label
            key={r.id}
            className={`flex items-start gap-2 ${locked ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
            title={locked ? ADMIN_ROLE_LOCKED_HINT : undefined}
          >
            <input
              type="checkbox"
              className="mt-0.5"
              checked={selected.includes(r.id)}
              onChange={() => onToggle(r.id)}
              disabled={disabled || locked}
            />
            <span>
              <span className="text-sm font-medium text-fg">{r.title ?? r.id}</span>
              {r.description && <span className="block text-xs text-subtle">{r.description}</span>}
              {locked && <span className="block text-xs text-subtle italic">{ADMIN_ROLE_LOCKED_HINT}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
}

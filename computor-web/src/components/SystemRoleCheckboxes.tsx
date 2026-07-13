'use client';

import { useSystemRoles } from '@/src/hooks/useSystemRoles';

/**
 * Checkbox list of the builtin system roles, labelled with each role's
 * human-readable `title` and `description` from the database (not the raw
 * `_role_id`). Shared by the user create/detail pages and the invite dialog so
 * the role names live in exactly one place.
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

  if (loading) return <p className="text-xs text-gray-400">Loading roles…</p>;
  if (roles.length === 0) return <p className="text-xs text-gray-400">No system roles available.</p>;

  return (
    <div className="space-y-2">
      {roles.map((r) => (
        <label key={r.id} className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={selected.includes(r.id)}
            onChange={() => onToggle(r.id)}
            disabled={disabled}
          />
          <span>
            <span className="text-sm font-medium text-gray-800">{r.title ?? r.id}</span>
            {r.description && <span className="block text-xs text-gray-400">{r.description}</span>}
          </span>
        </label>
      ))}
    </div>
  );
}

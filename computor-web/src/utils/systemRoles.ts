/**
 * System-role helpers mirrored from the backend (`permissions/roles.py`).
 * The backend treats ANY role id ending in `_admin` as admin-conferring
 * (`Principal.set_is_admin_from_roles`) and refuses to let non-admins grant
 * or revoke such roles (403 AUTHZ_005). These helpers only decide what to
 * show/enable — the backend remains the source of truth.
 */

/** True if holding this role makes a user a system admin. */
export function grantsAdmin(roleId: string): boolean {
  return roleId.endsWith('_admin');
}

/** Shown wherever a non-admin sees an admin-role control they cannot use. */
export const ADMIN_ROLE_LOCKED_HINT = 'Only administrators can grant or remove this role.';

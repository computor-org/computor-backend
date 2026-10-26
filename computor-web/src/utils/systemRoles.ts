import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';

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
export function adminRoleLockedHint(language: UiLanguage): string {
  return language === 'de'
    ? 'Nur Administratoren können diese Rolle vergeben oder entziehen.'
    : 'Only administrators can grant or remove this role.';
}

/**
 * German display names and descriptions for the builtin system roles. The
 * backend seeds English text; the ids stay untouched, and custom roles or
 * unknown ids fall back to whatever the backend sent.
 */
const ROLE_TEXT_DE: Record<string, { title: string; description: string }> = {
  _admin: { title: 'Administrator', description: 'Vollständige Systemrechte.' },
  _user_manager: { title: 'Benutzerverwaltung', description: 'Benutzerkonten und Berechtigungen verwalten.' },
  _organization_manager: {
    title: 'Organisationsverwaltung',
    description: 'Organisationen und ihre Mitglieder verwalten.',
  },
  _example_manager: { title: 'Beispielverwaltung', description: 'Beispiele und Beispiel-Repositories verwalten.' },
  _git_manager: {
    title: 'Git-Verwaltung',
    description: 'Vollzugriff auf die Benutzerverwaltung der Git-Server über die /git/*-Endpunkte.',
  },
  _service_manager: { title: 'Dienstverwaltung', description: 'Dienstkonten und ihre Tokens verwalten.' },
  _workspace_user: {
    title: 'Workspace-Nutzer',
    description: 'Grundzugriff auf die eigenen Workspaces: ansehen, starten, stoppen.',
  },
  _workspace_maintainer: {
    title: 'Workspace-Betreuung',
    description: 'Vollständige Workspace-Verwaltung: bereitstellen, löschen, alle Nutzer verwalten.',
  },
  _support: {
    title: 'Support',
    description:
      'Support-Tickets bearbeiten (Team-Postfach, Problemmeldungen): ansehen, übernehmen, zuweisen, antworten, Status setzen, interne Notizen.',
  },
  _support_agent: {
    title: 'Support-Assistenz',
    description:
      'Maschinenrolle für KI-Unterstützung: Tickets lesen und interne Notizen schreiben, aber nicht senden, übernehmen, schließen oder veröffentlichen.',
  },
};

/** Localized display name of a role; `fallback` is the backend title. */
export function roleTitle(roleId: string, fallback: string | null | undefined, language: UiLanguage): string {
  if (language === 'de' && ROLE_TEXT_DE[roleId]) return ROLE_TEXT_DE[roleId].title;
  return fallback ?? roleId;
}

/** Localized role description; `fallback` is the backend description. */
export function roleDescription(
  roleId: string,
  fallback: string | null | undefined,
  language: UiLanguage,
): string | null | undefined {
  if (language === 'de' && ROLE_TEXT_DE[roleId]) return ROLE_TEXT_DE[roleId].description;
  return fallback;
}

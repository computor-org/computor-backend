'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ScrollPanel } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import { WorkspaceRolesClient } from '@/src/clients/WorkspaceRolesClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const coderClient = new CoderClient();
const rolesClient = new WorkspaceRolesClient();
const WORKSPACE_ROLES = ['_workspace_user', '_workspace_maintainer'] as const;

const COPY = {
  de: {
    assignedProvisioned: 'Rolle zugewiesen und Arbeitsumgebung bereitgestellt',
    assignedProvisionFailed: 'Rolle zugewiesen, aber die Bereitstellung der Arbeitsumgebung ist fehlgeschlagen',
    assigned: 'Rolle erfolgreich zugewiesen',
    assignFailed: 'Die Rolle konnte nicht zugewiesen werden',
    removed: 'Rolle entfernt',
    removeFailed: 'Die Rolle konnte nicht entfernt werden',
    added: 'Rolle hinzugefügt',
    addFailed: 'Die Rolle konnte nicht hinzugefügt werden',
    provisioned: 'Arbeitsumgebung bereitgestellt',
    provisionFailed: 'Bereitstellung fehlgeschlagen',
    assignHeading: 'Rolle zuweisen',
    email: 'E-Mail',
    role: 'Rolle',
    provisionWorkspace: 'Arbeitsumgebung bereitstellen',
    assigning: 'Wird zugewiesen …',
    assign: 'Zuweisen',
    searchPlaceholder: 'Nach Name, E-Mail oder Benutzername suchen …',
    name: 'Name',
    username: 'Benutzername',
    roles: 'Rollen',
    workspace: 'Arbeitsumgebung',
    actions: 'Aktionen',
    noMatch: 'Keine Personen entsprechen deiner Suche',
    noUsers: 'Keine Personen mit Rollen für Arbeitsumgebungen',
    removeRole: 'Rolle entfernen',
    add: '+ Hinzufügen',
    na: 'k. A.',
    checking: 'Wird geprüft …',
    yes: 'Ja',
    provision: 'Bereitstellen',
    unknown: 'Unbekannt',
    manage: 'Verwalten',
    removeTitle: 'Rolle entfernen',
    removeMessage: (role: string | undefined, email: string) =>
      `Rolle „${role}“ von ${email} entfernen?`,
    thisUser: 'dieser Person',
    remove: 'Entfernen',
  },
  en: {
    assignedProvisioned: 'Role assigned and workspace provisioned',
    assignedProvisionFailed: 'Role assigned but workspace provisioning failed',
    assigned: 'Role assigned successfully',
    assignFailed: 'Failed to assign role',
    removed: 'Role removed',
    removeFailed: 'Failed to remove role',
    added: 'Role added',
    addFailed: 'Failed to add role',
    provisioned: 'Workspace provisioned',
    provisionFailed: 'Provisioning failed',
    assignHeading: 'Assign Role',
    email: 'Email',
    role: 'Role',
    provisionWorkspace: 'Provision workspace',
    assigning: 'Assigning...',
    assign: 'Assign',
    searchPlaceholder: 'Search by name, email, or username...',
    name: 'Name',
    username: 'Username',
    roles: 'Roles',
    workspace: 'Workspace',
    actions: 'Actions',
    noMatch: 'No users match your search',
    noUsers: 'No users with workspace roles',
    removeRole: 'Remove role',
    add: '+ Add',
    na: 'N/A',
    checking: 'Checking...',
    yes: 'Yes',
    provision: 'Provision',
    unknown: 'Unknown',
    manage: 'Manage',
    removeTitle: 'Remove Role',
    removeMessage: (role: string | undefined, email: string) =>
      `Remove role "${role}" from ${email}?`,
    thisUser: 'this user',
    remove: 'Remove',
  },
};

/** "Users & roles" admin tab: workspace role assignment + per-user overview. */
export default function WorkspaceUsersPanel() {
  const t = COPY[useUiLanguage()];
  const notify = useNotify();
  const [searchQuery, setSearchQuery] = useState('');

  const {
    data,
    loading,
    error,
    reload: fetchUsers,
  } = useResource(() => rolesClient.listUsers(), []);
  const users = useMemo(() => data ?? [], [data]);

  // Assign role form
  const [assignEmail, setAssignEmail] = useState('');
  const [assignRole, setAssignRole] = useState<string>('_workspace_user');
  const [assignProvision, setAssignProvision] = useState(false);
  const [assigning, setAssigning] = useState(false);

  // Workspace status per user
  const [workspaceStatus, setWorkspaceStatus] = useState<Record<string, boolean | 'loading' | null>>({});

  // Role removal confirmation
  const [removeTarget, setRemoveTarget] = useState<{ userId: string; roleId: string; email: string } | null>(null);

  // Check workspace status for each user with a workspace role
  useEffect(() => {
    if (users.length === 0) return;

    users.forEach((u) => {
      if (!u.email || !u.roles.some((r) => r.startsWith('_workspace'))) return;
      if (workspaceStatus[u.user_id] !== undefined) return;

      setWorkspaceStatus((prev) => ({ ...prev, [u.user_id]: 'loading' }));

      coderClient.checkWorkspaceExists({ email: u.email })
        .then((exists) => {
          setWorkspaceStatus((prev) => ({ ...prev, [u.user_id]: exists }));
        })
        .catch(() => {
          setWorkspaceStatus((prev) => ({ ...prev, [u.user_id]: null }));
        });
    });
  }, [users, workspaceStatus]);

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignEmail || !assignRole) return;

    setAssigning(true);
    try {
      await rolesClient.assignRole({
        body: { email: assignEmail, role_id: assignRole },
      });

      // Optionally provision a workspace from the server-default template
      if (assignProvision) {
        try {
          await coderClient.provisionWorkspace({ body: { email: assignEmail } });
          notify(t.assignedProvisioned, 'success');
        } catch {
          notify(t.assignedProvisionFailed, 'error');
        }
      } else {
        notify(t.assigned, 'success');
      }

      setAssignEmail('');
      setAssignProvision(false);
      // Reset workspace statuses so they're re-checked
      setWorkspaceStatus({});
      await fetchUsers();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.assignFailed, 'error');
    } finally {
      setAssigning(false);
    }
  };

  const handleRemoveRole = async () => {
    if (!removeTarget) return;
    try {
      await rolesClient.removeRole({ userId: removeTarget.userId, roleId: removeTarget.roleId });
      notify(t.removed, 'success');
      setRemoveTarget(null);
      await fetchUsers();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.removeFailed, 'error');
      setRemoveTarget(null);
    }
  };

  const handleInlineAddRole = async (userId: string, roleId: string) => {
    const u = users.find((x) => x.user_id === userId);
    if (!u?.email) return;
    try {
      await rolesClient.assignRole({ body: { email: u.email, role_id: roleId } });
      notify(t.added, 'success');
      await fetchUsers();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.addFailed, 'error');
    }
  };

  const handleProvisionForUser = async (email: string) => {
    try {
      // Server-default template; pick a specific one on the user detail page.
      await coderClient.provisionWorkspace({ body: { email } });
      notify(t.provisioned, 'success');
      setWorkspaceStatus({});
    } catch (err) {
      notify(err instanceof Error ? err.message : t.provisionFailed, 'error');
    }
  };

  // Filter users
  const filteredUsers = users.filter((u) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (u.email?.toLowerCase().includes(q)) ||
      (u.username?.toLowerCase().includes(q)) ||
      (u.given_name?.toLowerCase().includes(q)) ||
      (u.family_name?.toLowerCase().includes(q))
    );
  });

  return (
    <>
      {/* Assign Role Form */}
      <div className="shrink-0 bg-surface rounded-lg border border-rule p-6">
        <h2 className="text-lg font-semibold text-fg mb-4">{t.assignHeading}</h2>
        <form onSubmit={handleAssignRole} className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="assign-email" className="block text-sm font-medium text-body mb-1">{t.email}</label>
            <input
              id="assign-email"
              type="email"
              value={assignEmail}
              onChange={(e) => setAssignEmail(e.target.value)}
              className={inputCls}
              placeholder="user@example.com"
              required
            />
          </div>
          <div className="w-48">
            <label htmlFor="assign-role" className="block text-sm font-medium text-body mb-1">{t.role}</label>
            <select
              id="assign-role"
              value={assignRole}
              onChange={(e) => setAssignRole(e.target.value)}
              className={inputCls}
            >
              {WORKSPACE_ROLES.map((role) => (
                <option key={role} value={role}>{role}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-body cursor-pointer">
            <input
              type="checkbox"
              checked={assignProvision}
              onChange={(e) => setAssignProvision(e.target.checked)}
              className="rounded border-rule-strong text-accent-text focus:ring-accent-line"
            />
            {t.provisionWorkspace}
          </label>
          <Button type="submit" loading={assigning} loadingLabel={t.assigning}>
            {t.assign}
          </Button>
        </form>
      </div>

      {/* Search */}
      <div className="shrink-0">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={`${inputCls} max-w-md`}
          placeholder={t.searchPlaceholder}
        />
      </div>

      {/* Loading */}
      {loading && !data && (
        <div className="flex-1 min-h-0 bg-surface rounded-lg border border-rule p-6 animate-pulse">
          <div className="h-6 bg-sunken rounded w-1/4 mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-sunken rounded" />
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      <ErrorBanner>{error}</ErrorBanner>

      {/* Users Table */}
      {data && !error && (
        <ScrollPanel>
          <Table className="text-sm">
            <Thead>
              <tr>
                <Th>{t.name}</Th>
                <Th>{t.email}</Th>
                <Th>{t.username}</Th>
                <Th>{t.roles}</Th>
                <Th>{t.workspace}</Th>
                <Th>{t.actions}</Th>
              </tr>
            </Thead>
            <Tbody>
              {filteredUsers.length === 0 ? (
                <Tr>
                  <Td colSpan={6} className="py-8 text-center text-muted">
                    {searchQuery ? t.noMatch : t.noUsers}
                  </Td>
                </Tr>
              ) : (
                filteredUsers.map((u) => {
                  const missingRoles = WORKSPACE_ROLES.filter((r) => !u.roles.includes(r));
                  const wsStatus = workspaceStatus[u.user_id];
                  const hasWsRole = u.roles.some((r) => r.startsWith('_workspace'));

                  return (
                    <Tr key={u.user_id} className="hover:bg-canvas">
                      <Td className="text-fg">
                        {u.given_name || u.family_name
                          ? `${u.given_name || ''} ${u.family_name || ''}`.trim()
                          : '-'}
                      </Td>
                      <Td className="text-muted">{u.email || '-'}</Td>
                      <Td className="text-muted font-mono text-xs">{u.username || '-'}</Td>
                      <Td>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {u.roles.map((role) => (
                            <Badge key={role} color="blue" pill>
                              {role}
                              <button
                                onClick={() => setRemoveTarget({ userId: u.user_id, roleId: role, email: u.email || '' })}
                                className="text-blue-400 hover:text-danger-text ml-1"
                                title={t.removeRole}
                              >
                                &times;
                              </button>
                            </Badge>
                          ))}
                          {missingRoles.length > 0 && (
                            <select
                              className="text-xs border border-rule rounded px-1 py-0.5 text-muted"
                              value=""
                              onChange={(e) => {
                                if (e.target.value) handleInlineAddRole(u.user_id, e.target.value);
                              }}
                            >
                              <option value="">{t.add}</option>
                              {missingRoles.map((r) => (
                                <option key={r} value={r}>{r}</option>
                              ))}
                            </select>
                          )}
                        </div>
                      </Td>
                      <Td>
                        {!hasWsRole ? (
                          <span className="text-xs text-subtle">{t.na}</span>
                        ) : wsStatus === 'loading' ? (
                          <span className="text-xs text-subtle">{t.checking}</span>
                        ) : wsStatus === true ? (
                          <Badge color="green" pill>{t.yes}</Badge>
                        ) : wsStatus === false ? (
                          <Button size="xs" variant="secondary" onClick={() => u.email && handleProvisionForUser(u.email)}>
                            {t.provision}
                          </Button>
                        ) : (
                          <span className="text-xs text-subtle">{t.unknown}</span>
                        )}
                      </Td>
                      <Td>
                        <Link
                          href={`/workspaces/admin/${u.user_id}`}
                          className="text-sm text-accent-text hover:text-accent-text font-medium"
                        >
                          {t.manage}
                        </Link>
                      </Td>
                    </Tr>
                  );
                })
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}

      {/* Remove role confirmation */}
      <ConfirmDialog
        open={removeTarget !== null}
        title={t.removeTitle}
        message={t.removeMessage(removeTarget?.roleId, removeTarget?.email || t.thisUser)}
        confirmLabel={t.remove}
        variant="danger"
        onConfirm={handleRemoveRole}
        onCancel={() => setRemoveTarget(null)}
      />
    </>
  );
}

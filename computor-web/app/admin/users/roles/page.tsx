'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Forbidden from '@/src/components/Forbidden';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { RolesClient } from '@/src/generated/clients/RolesClient';
import { RoleClaimClient } from '@/src/generated/clients/RoleClaimClient';
import { UserRolesClient } from '@/src/generated/clients/UserRolesClient';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { RoleList, RoleGet, RoleClaimList, UserRoleList, UserList } from 'types/generated';

const rolesClient = new RolesClient();
const roleClaimsClient = new RoleClaimClient();
const userRolesClient = new UserRolesClient();
const usersClient = new UsersClient();

// Readable label per claim_value prefix
const CLAIM_COLORS: Record<string, string> = {
  user: 'bg-purple-100 text-purple-800',
  account: 'bg-indigo-100 text-indigo-800',
  role: 'bg-red-100 text-red-800',
  user_role: 'bg-red-100 text-red-800',
  role_claim: 'bg-red-100 text-red-800',
  workspace: 'bg-teal-100 text-teal-800',
  course: 'bg-blue-100 text-blue-800',
  organization: 'bg-orange-100 text-orange-800',
  course_family: 'bg-yellow-100 text-yellow-800',
};

function claimColor(value: string) {
  const resource = value.split(':')[0];
  return CLAIM_COLORS[resource] ?? 'bg-gray-100 text-gray-700';
}

function ClaimChip({ claim }: { claim: RoleClaimList }) {
  return (
    <span
      title={`${claim.claim_type}: ${claim.claim_value}`}
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium ${claimColor(claim.claim_value)}`}
    >
      {claim.claim_value}
    </span>
  );
}

function RoleBadge({ role }: { role: RoleList | RoleGet }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${role.builtin ? 'bg-slate-200 text-slate-700' : 'bg-green-100 text-green-800'}`}>
      {role.id}
    </span>
  );
}

export default function RolesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  // Backend-refreshed scopes (via usePermissions) instead of the cached
  // session's role string, which can go stale between logins.
  const { isAdmin, isUserManager } = usePermissions();

  const [roles, setRoles] = useState<RoleList[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [rolesError, setRolesError] = useState<string | null>(null);

  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [roleDetail, setRoleDetail] = useState<RoleGet | null>(null);
  const [claims, setClaims] = useState<RoleClaimList[]>([]);
  const [members, setMembers] = useState<UserRoleList[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [allUsers, setAllUsers] = useState<UserList[]>([]);
  const [addSearch, setAddSearch] = useState('');
  const [addUserId, setAddUserId] = useState('');
  const [pickerResults, setPickerResults] = useState<UserList[]>([]);
  // The query the current pickerResults answer — guards the "no matches"
  // message against flashing while a debounced search is still in flight.
  const [pickerQuery, setPickerQuery] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [removeConfirm, setRemoveConfirm] = useState<{ userId: string; email: string } | null>(null);

  const notify = useNotify();

  // Load roles and all users on mount
  useEffect(() => {
    if (authLoading || !isAuthenticated || !isUserManager) return;

    rolesClient.listRolesRolesGet({ limit: 200 })
      .then(data => { setRoles(data); setRolesLoading(false); })
      .catch(e => { setRolesError(e instanceof Error ? e.message : 'Failed to load roles'); setRolesLoading(false); });

    // Kept only for the member-list email display: UserRoleList carries just
    // user_id, and /users has no bulk id filter. The add-member picker below
    // searches server-side on demand instead of relying on this preload.
    usersClient.listUsersUsersGet({ limit: 500 })
      .then(setAllUsers)
      .catch(() => {});
  }, [authLoading, isAuthenticated, isUserManager]);

  // Debounced server-side search for the add-member picker (limit 20), so
  // users beyond the display preload above are still findable.
  useEffect(() => {
    const q = addSearch.trim();
    if (!q || addUserId) return;
    const t = setTimeout(() => {
      usersClient.listUsersUsersGet({ search: q, limit: 20 })
        .then(res => { setPickerResults(res); setPickerQuery(q); })
        .catch(() => {});
    }, 300);
    return () => clearTimeout(t);
  }, [addSearch, addUserId]);

  const userMap = useMemo(() => {
    const m = new Map<string, UserList>();
    allUsers.forEach(u => m.set(u.id, u));
    // Picker results too, so a freshly added member outside the preload
    // still shows an email in the member list.
    pickerResults.forEach(u => m.set(u.id, u));
    return m;
  }, [allUsers, pickerResults]);

  const loadRoleDetail = useCallback(async (roleId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    setRoleDetail(null);
    setClaims([]);
    setMembers([]);
    setAddSearch('');
    setAddUserId('');
    try {
      const [detail, roleClaims, userRoles] = await Promise.all([
        rolesClient.getRolesRolesIdGet({ id: roleId }),
        roleClaimsClient.list({ role_id: roleId, limit: 500 }),
        userRolesClient.listUserRolesUserRolesGet({ roleId, limit: 500 }),
      ]);
      setRoleDetail(detail);
      setClaims(roleClaims);
      setMembers(userRoles);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : 'Failed to load role detail');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleSelectRole = (roleId: string) => {
    setSelectedRoleId(roleId);
    loadRoleDetail(roleId);
  };

  const handleAddMember = async () => {
    if (!selectedRoleId || !addUserId) return;
    setAddingMember(true);
    try {
      await userRolesClient.createUserRoleUserRolesPost({
        body: { user_id: addUserId, role_id: selectedRoleId },
      });
      const updated = await userRolesClient.listUserRolesUserRolesGet({ roleId: selectedRoleId, limit: 500 });
      setMembers(updated);
      setAddSearch('');
      setAddUserId('');
      notify('User added to role', 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to add member', 'error');
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedRoleId) return;
    try {
      await userRolesClient.deleteUserRoleEndpointUserRolesUsersUserIdRolesRoleIdDelete({
        userId,
        roleId: selectedRoleId,
      });
      setMembers(m => m.filter(x => x.user_id !== userId));
      notify('User removed from role', 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to remove member', 'error');
    }
    setRemoveConfirm(null);
  };

  // Group claims by claim_type for display
  const claimsByType = useMemo(() => {
    const groups: Record<string, RoleClaimList[]> = {};
    claims.forEach(c => {
      if (!groups[c.claim_type]) groups[c.claim_type] = [];
      groups[c.claim_type].push(c);
    });
    return groups;
  }, [claims]);

  const memberUserIds = useMemo(() => new Set(members.map(m => m.user_id)), [members]);

  const addCandidates = useMemo(
    () => pickerResults.filter(u => !memberUserIds.has(u.id) && !u.archived_at).slice(0, 8),
    [pickerResults, memberUserIds],
  );

  // Guard
  if (authLoading) return <AuthenticatedLayout><div className="p-8 text-gray-500">Loading…</div></AuthenticatedLayout>;
  if (!isAuthenticated || !isUserManager) {
    return <Forbidden message="Requires admin or _user_manager role." backLink="/dashboard" backText="Back to Dashboard" />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Users', href: '/admin/users' }, { label: 'Roles' }]}
          title="Roles & Claims"
          subtitle={`${roles.length} roles`}
        />

        <div className="flex-1 min-h-0 flex overflow-hidden rounded-lg border border-gray-200 bg-white">

        {/* Left panel — role list */}
        <div className="w-72 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
          <div className="flex-1 overflow-y-auto">
            {rolesLoading ? (
              <div className="p-4 text-sm text-gray-400">Loading…</div>
            ) : rolesError ? (
              <div className="p-4 text-sm text-red-500">{rolesError}</div>
            ) : (
              <>
                {/* Builtin roles */}
                <div className="px-3 pt-3 pb-1">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">System</p>
                </div>
                {roles.filter(r => r.builtin).map(r => (
                  <RoleRow key={r.id} role={r} selected={r.id === selectedRoleId} onClick={() => handleSelectRole(r.id)} />
                ))}

                {/* Custom roles */}
                {roles.some(r => !r.builtin) && (
                  <>
                    <div className="px-3 pt-4 pb-1">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Custom</p>
                    </div>
                    {roles.filter(r => !r.builtin).map(r => (
                      <RoleRow key={r.id} role={r} selected={r.id === selectedRoleId} onClick={() => handleSelectRole(r.id)} />
                    ))}
                  </>
                )}
              </>
            )}
          </div>
        </div>

        {/* Right panel — role detail */}
        <div className="flex-1 overflow-y-auto">
          {!selectedRoleId ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              Select a role to view its claims and members
            </div>
          ) : detailLoading ? (
            <div className="p-8 text-gray-400 text-sm">Loading…</div>
          ) : detailError ? (
            <div className="p-8 text-red-500 text-sm">{detailError}</div>
          ) : roleDetail ? (
            <div className="p-6 space-y-8 max-w-3xl">

              {/* Role header */}
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-xl font-semibold text-gray-900">{roleDetail.title ?? roleDetail.id}</h2>
                  <RoleBadge role={roleDetail} />
                  {roleDetail.builtin && (
                    <span className="text-xs text-gray-400 italic">built-in</span>
                  )}
                </div>
                {roleDetail.description && (
                  <p className="text-sm text-gray-600">{roleDetail.description}</p>
                )}
              </div>

              {/* Claims */}
              <section>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Claims
                  <span className="ml-2 text-xs font-normal text-gray-400">({claims.length} total — read-only)</span>
                </h3>
                {claims.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">No claims defined for this role.</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(claimsByType).sort().map(([type, typeClaims]) => (
                      <div key={type}>
                        <p className="text-xs text-gray-400 mb-1.5">{type}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {typeClaims
                            .slice()
                            .sort((a, b) => a.claim_value.localeCompare(b.claim_value))
                            .map(c => (
                              <ClaimChip key={`${c.claim_type}:${c.claim_value}`} claim={c} />
                            ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Members */}
              <section>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Members
                  <span className="ml-2 text-xs font-normal text-gray-400">({members.length})</span>
                </h3>

                {members.length === 0 ? (
                  <p className="text-sm text-gray-400 italic mb-3">No users have this role.</p>
                ) : (
                  <div className="mb-4 space-y-1">
                    {members.map(m => {
                      const u = userMap.get(m.user_id);
                      const canRemove = isAdmin || roleDetail.id !== '_admin';
                      return (
                        <div key={m.user_id} className="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-lg">
                          <div>
                            <span className="text-sm font-medium text-gray-900">{u?.email ?? m.user_id}</span>
                            {u?.given_name && <span className="ml-2 text-xs text-gray-400">{u.given_name} {u.family_name}</span>}
                          </div>
                          {canRemove && (
                            <button
                              onClick={() => setRemoveConfirm({ userId: m.user_id, email: u?.email ?? m.user_id })}
                              className="text-xs text-red-500 hover:text-red-700 transition-colors ml-4"
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Add member — blocked for _admin role for non-admins */}
                {(isAdmin || roleDetail.id !== '_admin') && (
                  <div className="relative">
                    <p className="text-xs font-medium text-gray-600 mb-1.5">Add user to role</p>
                    <input
                      type="text"
                      placeholder="Search by email or name…"
                      value={addSearch}
                      onChange={e => { setAddSearch(e.target.value); setAddUserId(''); }}
                      className="w-full max-w-sm px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    {addSearch && addCandidates.length > 0 && !addUserId && (
                      <div className="absolute z-10 mt-1 w-full max-w-sm bg-white border border-gray-200 rounded-lg shadow-lg">
                        {addCandidates.map(u => (
                          <button
                            key={u.id}
                            onClick={() => { setAddUserId(u.id); setAddSearch(u.email ?? u.id); }}
                            className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between"
                          >
                            <span className="font-medium text-gray-900">{u.email}</span>
                            <span className="text-xs text-gray-400">{u.given_name} {u.family_name}</span>
                          </button>
                        ))}
                      </div>
                    )}
                    {addUserId && (
                      <button
                        onClick={handleAddMember}
                        disabled={addingMember}
                        className="mt-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                      >
                        {addingMember ? 'Adding…' : 'Add'}
                      </button>
                    )}
                    {addSearch && addCandidates.length === 0 && !addUserId && pickerQuery === addSearch.trim() && (
                      <p className="mt-1 text-xs text-gray-400">No matching users found.</p>
                    )}
                  </div>
                )}
                {!isAdmin && roleDetail.id === '_admin' && (
                  <p className="text-xs text-gray-400 italic">Only admins can modify _admin role membership.</p>
                )}
              </section>

            </div>
          ) : null}
        </div>
        </div>

        <ConfirmDialog
          open={removeConfirm !== null}
          title="Remove from role?"
          message={`Remove ${removeConfirm?.email ?? ''} from ${selectedRoleId ?? ''}?`}
          confirmLabel="Remove"
          variant="danger"
          onConfirm={() => removeConfirm && handleRemoveMember(removeConfirm.userId)}
          onCancel={() => setRemoveConfirm(null)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

function RoleRow({ role, selected, onClick }: { role: RoleList; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 flex items-start gap-2 transition-colors ${selected ? 'bg-blue-50 border-r-2 border-blue-500' : 'hover:bg-gray-100'}`}
    >
      <div className="min-w-0">
        <div className="text-xs font-mono font-medium text-gray-800 truncate">{role.id}</div>
        {role.title && <div className="text-xs text-gray-500 truncate mt-0.5">{role.title}</div>}
      </div>
    </button>
  );
}

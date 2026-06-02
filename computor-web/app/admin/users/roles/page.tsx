'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { RolesClient } from '@/src/generated/clients/RolesClient';
import { RoleClaimClient } from '@/src/generated/clients/RoleClaimClient';
import { UserClient } from '@/src/generated/clients/UserClient';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { RoleList, RoleGet, RoleClaimList, UserRoleList, UserList } from 'types/generated';

const rolesClient = new RolesClient();
const roleClaimsClient = new RoleClaimClient();
const userRolesClient = new UserClient();
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
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const isAdmin = user?.role === 'admin';
  const isUserManager = isAdmin || (user?.systemRoles?.includes('_user_manager') ?? false);

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
  const [addingMember, setAddingMember] = useState(false);
  const [removeConfirm, setRemoveConfirm] = useState<{ userId: string; email: string } | null>(null);

  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const notify = (message: string, type: 'success' | 'error') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load roles and all users on mount
  useEffect(() => {
    if (authLoading || !isAuthenticated || !isUserManager) return;

    rolesClient.listRolesRolesGet({ limit: 200 })
      .then(data => { setRoles(data); setRolesLoading(false); })
      .catch(e => { setRolesError(e instanceof Error ? e.message : 'Failed to load roles'); setRolesLoading(false); });

    usersClient.listUsersUsersGet({ limit: 500 })
      .then(setAllUsers)
      .catch(() => {});
  }, [authLoading, isAuthenticated, isUserManager]);

  const userMap = useMemo(() => {
    const m = new Map<string, UserList>();
    allUsers.forEach(u => m.set(u.id, u));
    return m;
  }, [allUsers]);

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

  const addCandidates = useMemo(() => {
    const q = addSearch.toLowerCase();
    return allUsers.filter(u =>
      !memberUserIds.has(u.id) &&
      !u.archived_at &&
      ((u.email?.toLowerCase().includes(q) ?? false)
        || `${u.given_name ?? ''} ${u.family_name ?? ''}`.toLowerCase().includes(q))
    ).slice(0, 8);
  }, [allUsers, memberUserIds, addSearch]);

  // Guard
  if (authLoading) return <AuthenticatedLayout><div className="p-8 text-gray-500">Loading…</div></AuthenticatedLayout>;
  if (!isAuthenticated || !isUserManager) {
    return (
      <AuthenticatedLayout>
        <div className="p-8 text-red-600 font-medium">Access denied. Requires admin or _user_manager role.</div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="flex h-[calc(100vh-4rem)] overflow-hidden">

        {/* Left panel — role list */}
        <div className="w-72 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h1 className="text-base font-semibold text-gray-900">Roles & Claims</h1>
            <p className="text-xs text-gray-500 mt-0.5">{roles.length} roles</p>
          </div>

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

              {/* Notification */}
              {notification && (
                <div className={`px-4 py-3 rounded-lg text-sm ${notification.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                  {notification.message}
                </div>
              )}

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
                    {addSearch && addCandidates.length === 0 && !addUserId && (
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

      {/* Remove member confirm */}
      {removeConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Remove from role?</h2>
            <p className="text-sm text-gray-600 mb-4">
              Remove <strong>{removeConfirm.email}</strong> from <strong>{selectedRoleId}</strong>?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setRemoveConfirm(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
              <button
                onClick={() => handleRemoveMember(removeConfirm.userId)}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
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

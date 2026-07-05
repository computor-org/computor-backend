'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { inputCls } from '@/src/components/FormPanel';
import type { ApiTokenGet, ApiTokenCreateResponse, AccountGet } from 'types/generated';
import type { ConsentStatus } from '@/src/types/consent';

const KC_URL = process.env.NEXT_PUBLIC_KEYCLOAK_URL;
const KC_REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'computor';
const accountConsoleUrl = KC_URL ? `${KC_URL.replace(/\/$/, '')}/realms/${KC_REALM}/account/` : null;

// The generated AccountGet doesn't carry `builtin` until the types are regenerated.
type AccountRow = AccountGet & { builtin?: boolean };

function Section({ title, description, children, actions }: {
  title: string;
  description?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <div className="px-6 py-4 border-b border-gray-100 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">{title}</h2>
          {description && <p className="text-sm text-gray-500 mt-0.5">{description}</p>}
        </div>
        {actions}
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

function fmtDate(s?: string | null): string {
  return s ? new Date(s).toLocaleDateString() : '—';
}

export default function SettingsPage() {
  const router = useRouter();
  const { user: authUser, isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();

  const [tokens, setTokens] = useState<ApiTokenGet[]>([]);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Consent / privacy
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [consentLoading, setConsentLoading] = useState(true);
  const [withdrawing, setWithdrawing] = useState(false);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  // Token creation
  const [newName, setNewName] = useState('');
  const [newExpiry, setNewExpiry] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdToken, setCreatedToken] = useState<ApiTokenCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const [confirm, setConfirm] = useState<
    { title: string; message: string; confirmWord: string; onConfirm: () => Promise<void> } | null
  >(null);

  async function load() {
    if (!authUser) return;
    try {
      const [tk, ac] = await Promise.all([
        api.get<ApiTokenGet[]>('/api-tokens'),
        api.get<AccountRow[]>(`/accounts?user_id=${authUser.id}`).catch(() => [] as AccountRow[]),
      ]);
      setTokens(tk);
      setAccounts(ac);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authLoading || !isAuthenticated || !authUser) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated, authUser?.id]);

  async function createToken() {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const created = await api.post<ApiTokenCreateResponse>('/api-tokens', {
        name: newName.trim(),
        expires_at: newExpiry ? new Date(newExpiry).toISOString() : null,
      });
      setCreatedToken(created);
      setCopied(false);
      setNewName('');
      setNewExpiry('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create token');
    } finally {
      setCreating(false);
    }
  }

  const activeTokens = tokens.filter((t) => !t.revoked_at);

  useEffect(() => {
    async function fetchConsentStatus() {
      try {
        setConsentStatus(await api.get<ConsentStatus>('/consent/status'));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load consent status');
      } finally {
        setConsentLoading(false);
      }
    }
    fetchConsentStatus();
  }, []);

  const handleWithdraw = async () => {
    setWithdrawing(true);
    setError(null);
    try {
      await api.post('/consent/withdraw');
      // Access is gated again; the consent page is the only place left to go.
      router.push('/consent');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to withdraw consent');
      setWithdrawing(false);
      setConfirmWithdraw(false);
    }
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={[{ label: 'Settings' }]} title="Settings" subtitle="Manage your account, security, and API access." />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          <div className="max-w-3xl space-y-6">
            {/* Account & Security — only shown when the account console is configured */}
            {accountConsoleUrl && (
              <Section title="Account & Security" description="Password, email, two-factor authentication and active sessions are managed by your login provider.">
                <a
                  href={accountConsoleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Open account console
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </Section>
            )}

            {/* API Tokens */}
            <Section
              title="API Tokens"
              description="Personal access tokens for the CLI, VS Code extension and scripts. Treat them like passwords."
            >
              {createdToken && (
                <div className="mb-5 rounded-lg border border-green-300 bg-green-50 p-4">
                  <p className="text-sm font-medium text-green-800">Token created — copy it now. You won’t be able to see it again.</p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="flex-1 font-mono text-xs bg-white border border-green-200 rounded px-2 py-1.5 break-all">{createdToken.token}</code>
                    <button
                      onClick={() => {
                        navigator.clipboard?.writeText(createdToken.token);
                        setCopied(true);
                      }}
                      className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 whitespace-nowrap"
                    >
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                    <button onClick={() => setCreatedToken(null)} className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded">Dismiss</button>
                  </div>
                </div>
              )}

              {/* Create form */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  createToken();
                }}
                className="flex flex-wrap items-end gap-3 mb-5"
              >
                <div className="flex-1 min-w-[12rem]">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Token name</label>
                  <input className={inputCls} value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. laptop CLI" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Expires (optional)</label>
                  <input type="date" className={inputCls} value={newExpiry} onChange={(e) => setNewExpiry(e.target.value)} />
                </div>
                <button
                  type="submit"
                  disabled={creating || !newName.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {creating ? 'Creating…' : 'Create token'}
                </button>
              </form>

              {loading ? (
                <div className="text-sm text-gray-500">Loading…</div>
              ) : activeTokens.length === 0 ? (
                <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-lg p-6 text-center">No active tokens.</div>
              ) : (
                <div className="border border-gray-200 rounded-lg divide-y">
                  {activeTokens.map((t) => (
                    <div key={t.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">{t.name}</div>
                        <div className="text-xs text-gray-500">
                          <span className="font-mono">{t.token_prefix}…</span> · created {fmtDate(t.created_at)} ·{' '}
                          {t.expires_at ? `expires ${fmtDate(t.expires_at)}` : 'no expiry'} ·{' '}
                          {t.last_used_at ? `last used ${fmtDate(t.last_used_at)}` : 'never used'}
                        </div>
                      </div>
                      <button
                        onClick={() =>
                          setConfirm({
                            title: 'Revoke token',
                            message: `Revoking "${t.name}" immediately invalidates it. Anything using it will stop working.`,
                            confirmWord: t.name,
                            onConfirm: async () => {
                              await api.del(`/api-tokens/${t.id}`);
                              await load();
                            },
                          })
                        }
                        className="text-sm text-red-600 hover:underline whitespace-nowrap"
                      >
                        Revoke
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* Accounts */}
            <Section
              title="Accounts"
              description="Your sign-in and Git-server identities."
            >
              {loading ? (
                <div className="text-sm text-gray-500">Loading…</div>
              ) : accounts.length === 0 ? (
                <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-lg p-6 text-center">No accounts yet.</div>
              ) : (
                <div className="border border-gray-200 rounded-lg divide-y">
                  {accounts.map((a) => (
                    <div key={a.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 capitalize flex items-center gap-2">
                          {a.type || a.provider}
                          {a.builtin && <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-600 capitalize">built-in</span>}
                        </div>
                        <div className="text-xs text-gray-500">
                          <span className="font-mono">{a.provider_account_id}</span> · {a.provider}
                        </div>
                      </div>
                      {(isAdmin || !a.builtin) && (
                        <button
                          onClick={() =>
                            setConfirm({
                              title: 'Unlink account',
                              message: `Unlink ${a.provider} account "${a.provider_account_id}"?`,
                              confirmWord: a.provider_account_id,
                              onConfirm: async () => {
                                await api.del(`/accounts/${a.id}`);
                                await load();
                              },
                            })
                          }
                          className="text-sm text-red-600 hover:underline whitespace-nowrap"
                        >
                          Unlink
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* Privacy & Consent */}
            <Section
              title="Privacy & Consent"
              description="Review the current privacy notice and manage your consent."
            >
              {consentLoading ? (
                <div className="text-sm text-gray-500">Loading…</div>
              ) : !consentStatus?.required_version ? (
                <div className="text-sm text-gray-500">No privacy notice is currently configured.</div>
              ) : (
                <div className="space-y-4">
                  <div className="text-sm text-gray-700 space-y-1">
                    <p>
                      Privacy notice version:{' '}
                      <span className="font-mono">{consentStatus.required_version}</span>
                    </p>
                    {consentStatus.has_consented && consentStatus.granted_at ? (
                      <p>Consent given on {new Date(consentStatus.granted_at).toLocaleString()}.</p>
                    ) : (
                      <p className="text-amber-700">You have not consented to the current privacy notice.</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <a
                      href="/consent?review=1"
                      className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium"
                    >
                      View privacy notice
                    </a>

                    {consentStatus.has_consented && (
                      confirmWithdraw ? (
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="text-sm text-gray-600">
                            Withdrawing consent will block access to the platform until you consent again. Continue?
                          </span>
                          <button
                            onClick={handleWithdraw}
                            disabled={withdrawing}
                            className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300 text-sm font-medium"
                          >
                            {withdrawing ? 'Withdrawing…' : 'Yes, withdraw'}
                          </button>
                          <button
                            onClick={() => setConfirmWithdraw(false)}
                            disabled={withdrawing}
                            className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmWithdraw(true)}
                          className="px-4 py-2 rounded-lg border border-red-300 text-red-700 hover:bg-red-50 text-sm font-medium"
                        >
                          Withdraw consent
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}
            </Section>
          </div>
        </ScrollArea>
      </ListPageLayout>

      {confirm && (
        <ConfirmDeleteDialog
          title={confirm.title}
          message={confirm.message}
          confirmWord={confirm.confirmWord}
          onConfirm={async () => {
            await confirm.onConfirm();
            setConfirm(null);
          }}
          onClose={() => setConfirm(null)}
        />
      )}
    </AuthenticatedLayout>
  );
}

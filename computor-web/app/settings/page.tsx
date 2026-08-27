'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { TokensClient } from '@/src/generated/clients/TokensClient';
import { AccountsClient } from '@/src/generated/clients/AccountsClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import ThemePicker from '@/src/components/ThemePicker';
import { inputCls } from '@/src/components/ui/tokens';
import type { ApiTokenGet, ApiTokenCreateResponse, AccountList } from 'types/generated';
import type { ConsentStatusGet } from '@/src/generated/types/common';
import { ConsentClient } from '@/src/generated/clients/ConsentClient';
import { appPath } from '@/src/utils/appPath';

const tokensClient = new TokensClient();
const accountsClient = new AccountsClient();

const KC_URL = process.env.NEXT_PUBLIC_KEYCLOAK_URL;
const KC_REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'computor';
const accountConsoleUrl = KC_URL ? `${KC_URL.replace(/\/$/, '')}/realms/${KC_REALM}/account/` : null;

// The accounts list endpoint returns AccountList, which already carries `builtin`.
type AccountRow = AccountList;

function Section({ title, description, children, actions }: {
  title: string;
  description?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="bg-surface border border-rule rounded-lg">
      <div className="px-6 py-4 border-b border-rule-soft flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-fg">{title}</h2>
          {description && <p className="text-sm text-muted mt-0.5">{description}</p>}
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


const consentClient = new ConsentClient();
export default function SettingsPage() {
  const router = useRouter();
  const { user: authUser, isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();

  const [tokens, setTokens] = useState<ApiTokenGet[]>([]);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Consent / privacy
  const [consentStatus, setConsentStatus] = useState<ConsentStatusGet | null>(null);
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
        tokensClient.listTokensEndpointApiTokensGet({}),
        accountsClient.listAccountsAccountsGet({ userId: authUser.id }).catch(() => [] as AccountRow[]),
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
      const created = await tokensClient.createTokenEndpointApiTokensPost({
        body: {
          name: newName.trim(),
          expires_at: newExpiry ? new Date(newExpiry).toISOString() : null,
        },
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
        setConsentStatus(await consentClient.getConsentStatusConsentStatusGet({}));
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
      await consentClient.withdrawConsentConsentWithdrawPost({});
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
      <ListPageLayout width="narrow">
        <PageHeader breadcrumbs={[{ label: 'Settings' }]} title="Settings" subtitle="Manage your account, security, and API access." />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          <div className="space-y-6">
            <Section
              title="Appearance"
              description="How Computor looks on this device. Not synced across devices."
            >
              <ThemePicker />
            </Section>

            {/* Account & Security — only shown when the account console is configured */}
            {accountConsoleUrl && (
              <Section title="Account & Security" description="Password, email, two-factor authentication and active sessions are managed by your login provider.">
                <a
                  href={accountConsoleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover"
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
              title="API tokens"
              description="Personal access tokens for the CLI, VS Code extension and scripts. Treat them like passwords."
            >
              {/*
                Scopes are additive claims (PrincipalBuilder.build), so a
                personal token is never weaker than the account. Users assume
                the opposite; say it where the token is minted.
              */}
              <div className="mb-5 rounded-lg border border-warn-line bg-warn-wash p-3 text-sm text-warn-text">
                <strong className="font-medium">A token acts with your full permissions.</strong>{' '}
                Scopes only add permissions — they never remove any. Anyone holding one of these tokens
                can do anything you can.
              </div>

              {createdToken && (
                <div className="mb-5 rounded-lg border border-success-line bg-success-wash p-4">
                  <p className="text-sm font-medium text-success-text">Token created — copy it now. You won’t be able to see it again.</p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="flex-1 font-mono text-xs bg-surface border border-success-line rounded px-2 py-1.5 break-all">{createdToken.token}</code>
                    <button
                      onClick={() => {
                        navigator.clipboard?.writeText(createdToken.token);
                        setCopied(true);
                      }}
                      className="px-3 py-1.5 text-xs font-medium bg-success text-on-accent rounded hover:bg-success-hover whitespace-nowrap"
                    >
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                    <button onClick={() => setCreatedToken(null)} className="px-3 py-1.5 text-xs text-muted hover:bg-sunken rounded">Dismiss</button>
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
                  <label className="block text-xs font-medium text-body mb-1">Token name</label>
                  <input className={inputCls} value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. laptop CLI" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-body mb-1">Expires (optional)</label>
                  <input type="date" className={inputCls} value={newExpiry} onChange={(e) => setNewExpiry(e.target.value)} />
                </div>
                <button
                  type="submit"
                  disabled={creating || !newName.trim()}
                  className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
                >
                  {creating ? 'Creating…' : 'Create token'}
                </button>
              </form>

              {loading ? (
                <div className="text-sm text-muted">Loading…</div>
              ) : activeTokens.length === 0 ? (
                <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">No active tokens.</div>
              ) : (
                <div className="border border-rule rounded-lg divide-y">
                  {activeTokens.map((t) => (
                    <div key={t.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg truncate">{t.name}</div>
                        <div className="text-xs text-muted">
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
                              await tokensClient.revokeTokenEndpointApiTokensTokenIdDelete({ tokenId: t.id });
                              await load();
                            },
                          })
                        }
                        className="text-sm text-danger-text hover:underline whitespace-nowrap"
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
                <div className="text-sm text-muted">Loading…</div>
              ) : accounts.length === 0 ? (
                <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">No accounts yet.</div>
              ) : (
                <div className="border border-rule rounded-lg divide-y">
                  {accounts.map((a) => (
                    <div key={a.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg capitalize flex items-center gap-2">
                          {a.type || a.provider}
                          {a.builtin && <span className="px-2 py-0.5 text-xs font-medium rounded bg-sunken text-muted capitalize">built-in</span>}
                        </div>
                        <div className="text-xs text-muted">
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
                                await accountsClient.deleteAccountsAccountsIdDelete({ id: a.id });
                                await load();
                              },
                            })
                          }
                          className="text-sm text-danger-text hover:underline whitespace-nowrap"
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
                <div className="text-sm text-muted">Loading…</div>
              ) : !consentStatus?.required_version ? (
                <div className="text-sm text-muted">No privacy notice is currently configured.</div>
              ) : (
                <div className="space-y-4">
                  <div className="text-sm text-body space-y-1">
                    <p>
                      Privacy notice version:{' '}
                      <span className="font-mono">{consentStatus.required_version}</span>
                    </p>
                    {consentStatus.has_consented && consentStatus.granted_at ? (
                      <p>Consent given on {new Date(consentStatus.granted_at).toLocaleString()}.</p>
                    ) : (
                      <p className="text-warn-text">You have not consented to the current privacy notice.</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <a
                      href={`${appPath('/consent')}?review=1`}
                      className="px-4 py-2 rounded-lg border border-rule-strong text-body hover:bg-canvas text-sm font-medium"
                    >
                      View privacy notice
                    </a>

                    {consentStatus.has_consented && (
                      confirmWithdraw ? (
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="text-sm text-muted">
                            Withdrawing consent will block access to the platform until you consent again. Continue?
                          </span>
                          <button
                            onClick={handleWithdraw}
                            disabled={withdrawing}
                            className="px-4 py-2 rounded-lg bg-danger text-on-accent hover:bg-danger-hover disabled:bg-faint text-sm font-medium"
                          >
                            {withdrawing ? 'Withdrawing…' : 'Yes, withdraw'}
                          </button>
                          <button
                            onClick={() => setConfirmWithdraw(false)}
                            disabled={withdrawing}
                            className="px-4 py-2 rounded-lg border border-rule-strong text-body hover:bg-canvas text-sm font-medium"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmWithdraw(true)}
                          className="px-4 py-2 rounded-lg border border-danger-line text-danger-text hover:bg-danger-wash text-sm font-medium"
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

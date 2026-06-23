'use client';

import { useEffect, useState } from 'react';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { OnboardingClient } from '@/src/clients/OnboardingClient';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { inputCls } from '@/src/components/FormPanel';
import type { ApiTokenGet, ApiTokenCreateResponse, AccountGet } from 'types/generated';

const KC_URL = process.env.NEXT_PUBLIC_KEYCLOAK_URL;
const KC_REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'computor';
const accountConsoleUrl = KC_URL ? `${KC_URL.replace(/\/$/, '')}/realms/${KC_REALM}/account/` : null;

const onboarding = new OnboardingClient();

// The generated AccountGet doesn't carry `builtin` until the types are regenerated.
type AccountRow = AccountGet & { builtin?: boolean };
type LinkProvider = { id: string; display_name: string };

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

/** Inline "Link account" flow: choose the account type, then its fields appear —
 * rendered inside Settings so the chrome (top bar + sidebar) stays put. */
function LinkAccountPanel({ providers, onLinked, onCancel }: {
  providers: LinkProvider[];
  onLinked: () => void;
  onCancel: () => void;
}) {
  const [providerId, setProviderId] = useState('');
  const [gitlabUrl, setGitlabUrl] = useState('');
  const [gitlabPat, setGitlabPat] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function submitGitlab() {
    setError(null);
    if (password !== confirm) return setError('Passwords do not match');
    if (password.length < 8) return setError('Password must be at least 8 characters');
    setSubmitting(true);
    try {
      const res = await onboarding.registerViaGitlab({
        gitlab_url: gitlabUrl.trim(),
        gitlab_pat: gitlabPat.trim(),
        new_password: password,
      });
      setDone(res.email);
      onLinked();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Linking failed');
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="rounded-lg border border-green-300 bg-green-50 p-4 text-sm text-green-800">
        Verified <strong>{done}</strong> and linked your GitLab account.
        <button onClick={onCancel} className="ml-3 text-green-700 underline">Close</button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4">
      {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Account type</label>
        <select className={inputCls} value={providerId} onChange={(e) => setProviderId(e.target.value)}>
          <option value="">— choose a type —</option>
          {providers.map((p) => (
            <option key={p.id} value={p.id}>{p.display_name}</option>
          ))}
        </select>
      </div>

      {providerId === 'gitlab' && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitGitlab();
          }}
          className="space-y-3"
        >
          <p className="text-xs text-gray-500">
            Verify with a GitLab Personal Access Token (read profile), then set your Computor password. The token is never stored.
          </p>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">GitLab URL</label>
            <input type="url" required className={inputCls} value={gitlabUrl} onChange={(e) => setGitlabUrl(e.target.value)} placeholder="https://gitlab.example.com" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Personal Access Token</label>
            <input type="password" required className={inputCls} value={gitlabPat} onChange={(e) => setGitlabPat(e.target.value)} placeholder="glpat-…" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
              <input type="password" required minLength={8} className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Confirm password</label>
              <input type="password" required className={inputCls} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
            <button type="submit" disabled={submitting} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {submitting ? 'Verifying…' : 'Verify & link'}
            </button>
          </div>
        </form>
      )}

      {providerId === '' && (
        <div className="flex justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const { user: authUser, isAuthenticated, isLoading: authLoading } = useAuth();

  const [tokens, setTokens] = useState<ApiTokenGet[]>([]);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [providers, setProviders] = useState<LinkProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Token creation
  const [newName, setNewName] = useState('');
  const [newExpiry, setNewExpiry] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdToken, setCreatedToken] = useState<ApiTokenCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const [linkOpen, setLinkOpen] = useState(false);
  const [confirm, setConfirm] = useState<
    { title: string; message: string; confirmWord: string; onConfirm: () => Promise<void> } | null
  >(null);

  async function load() {
    if (!authUser) return;
    try {
      const [tk, ac, pv] = await Promise.all([
        api.get<ApiTokenGet[]>('/api-tokens'),
        api.get<AccountRow[]>(`/accounts?user_id=${authUser.id}`).catch(() => [] as AccountRow[]),
        api.get<LinkProvider[]>('/accounts/providers').catch(() => [] as LinkProvider[]),
      ]);
      setTokens(tk);
      setAccounts(ac);
      setProviders(pv);
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

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-3xl">
        <PageHeader breadcrumbs={[{ label: 'Settings' }]} title="Settings" subtitle="Manage your account, security, and API access." />

        <ErrorBanner>{error}</ErrorBanner>

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
          description="Your sign-in and Git-server identities, plus any external accounts you’ve linked."
          actions={
            !linkOpen && providers.length > 0 ? (
              <button
                onClick={() => setLinkOpen(true)}
                className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 whitespace-nowrap"
              >
                Link account
              </button>
            ) : undefined
          }
        >
          {linkOpen && (
            <div className="mb-5">
              <LinkAccountPanel
                providers={providers}
                onLinked={load}
                onCancel={() => setLinkOpen(false)}
              />
            </div>
          )}

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
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

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

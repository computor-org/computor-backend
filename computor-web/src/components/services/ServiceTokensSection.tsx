'use client';

import { useCallback, useEffect, useState } from 'react';
import { inputCls } from '@/src/components/ui/tokens';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { TokensClient } from '@/src/generated/clients/TokensClient';
import type { ApiTokenCreateResponse, ApiTokenGet } from 'types/generated';

const tokensClient = new TokensClient();

function fmtDate(s?: string | null): string {
  return s ? new Date(s).toLocaleDateString() : '—';
}

/**
 * API tokens for one service account.
 *
 * Lives on the service detail page rather than its own route: a token has no
 * meaning apart from the account it belongs to, and the query is simply
 * `GET /api-tokens?user_id=<service.user_id>`.
 */
export default function ServiceTokensSection({
  userId,
  serviceName,
}: {
  userId: string;
  serviceName: string;
}) {
  const [tokens, setTokens] = useState<ApiTokenGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newName, setNewName] = useState('');
  const [newExpiry, setNewExpiry] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdToken, setCreatedToken] = useState<ApiTokenCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState<ApiTokenGet | null>(null);

  const load = useCallback(async () => {
    try {
      const list = await tokensClient.listTokensEndpointApiTokensGet({ userId });
      setTokens(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load tokens');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createToken() {
    setCreating(true);
    setError(null);
    setCopied(false);
    try {
      const created = await tokensClient.createTokenEndpointApiTokensPost({
        body: {
          name: newName.trim(),
          user_id: userId,
          // Left empty on purpose: the backend fills the defaults for this
          // service type's category (DEFAULT_SERVICE_SCOPES).
          scopes: [],
          expires_at: newExpiry ? new Date(newExpiry).toISOString() : null,
        },
      });
      setCreatedToken(created);
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
    <div className="bg-surface border border-rule rounded-lg">
      <div className="px-6 py-4 border-b border-rule-soft">
        <h2 className="text-base font-semibold text-fg">API Tokens</h2>
        <p className="text-sm text-muted mt-0.5">
          How this service authenticates. Set the value as <code className="font-mono text-xs">API_TOKEN</code> on
          the worker, sent as the <code className="font-mono text-xs">X-API-Token</code> header.
        </p>
      </div>

      <div className="p-6">
        {/*
          Not a nicety: scopes are additive claims (PrincipalBuilder.build), so
          a token is never weaker than its account. Saying so where tokens are
          minted is the only thing that stops someone treating an empty scope
          list as "harmless".
        */}
        <div className="mb-5 rounded-lg border border-warn-line bg-warn-wash p-3 text-sm text-warn-text">
          <strong className="font-medium">Scopes only add permissions — they never remove any.</strong>{' '}
          A token acts with the full permissions of its account. A service account holds no roles,
          so its scopes are its entire authority; a token on a human account would carry all of that
          person&apos;s roles regardless of what is listed here.
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-danger-line bg-danger-wash px-3 py-2 text-sm text-danger-text">{error}</div>
        )}

        {createdToken && (
          <div className="mb-5 rounded-lg border border-green-300 bg-success-wash p-4">
            <p className="text-sm font-medium text-success-text">
              Token created — copy it now. You won’t be able to see it again.
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="flex-1 font-mono text-xs bg-surface border border-success-line rounded px-2 py-1.5 break-all">
                {createdToken.token}
              </code>
              <button
                onClick={() => {
                  navigator.clipboard?.writeText(createdToken.token);
                  setCopied(true);
                }}
                className="px-3 py-1.5 text-xs font-medium bg-green-600 text-on-accent rounded hover:bg-green-700 whitespace-nowrap"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
              <button
                onClick={() => setCreatedToken(null)}
                className="px-3 py-1.5 text-xs text-muted hover:bg-sunken rounded"
              >
                Dismiss
              </button>
            </div>
            {createdToken.scopes.length > 0 && (
              <p className="mt-2 text-xs text-success-text">
                Granted {createdToken.scopes.length} default scope(s) for this service type:{' '}
                <span className="font-mono">{createdToken.scopes.join(', ')}</span>
              </p>
            )}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void createToken();
          }}
          className="flex flex-wrap items-end gap-3 mb-5"
        >
          <div className="flex-1 min-w-[12rem]">
            <label className="block text-xs font-medium text-body mb-1">Token name</label>
            <input
              className={inputCls}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={`${serviceName} token`}
            />
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
          <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">
            No active tokens — this service cannot authenticate yet.
          </div>
        ) : (
          <div className="border border-rule rounded-lg divide-y">
            {activeTokens.map((t) => (
              <div key={t.id} className="flex items-center justify-between px-4 py-3 gap-4">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-fg truncate">{t.name}</div>
                  <div className="text-xs text-muted">
                    <span className="font-mono">{t.token_prefix}…</span> · {t.scopes.length} scope(s) ·{' '}
                    {t.expires_at ? `expires ${fmtDate(t.expires_at)}` : 'no expiry'} ·{' '}
                    {t.last_used_at ? `last used ${fmtDate(t.last_used_at)}` : 'never used'}
                  </div>
                </div>
                <button
                  onClick={() => setConfirmRevoke(t)}
                  className="text-sm text-danger-text hover:underline whitespace-nowrap"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {confirmRevoke && (
        <ConfirmDialog
          open
          title="Revoke token"
          message={
            `Revoking "${confirmRevoke.name}" invalidates it immediately. If a running worker is using ` +
            `it, that worker keeps failing until its API_TOKEN is updated and it restarts.`
          }
          confirmLabel="Revoke"
          variant="danger"
          onConfirm={async () => {
            await tokensClient.revokeTokenEndpointApiTokensTokenIdDelete({ tokenId: confirmRevoke.id });
            setConfirmRevoke(null);
            await load();
          }}
          onCancel={() => setConfirmRevoke(null)}
        />
      )}
    </div>
  );
}

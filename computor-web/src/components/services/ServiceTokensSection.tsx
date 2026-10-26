'use client';

import { useCallback, useEffect, useState } from 'react';
import { inputCls } from '@/src/components/ui/tokens';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { TokensClient } from '@/src/generated/clients/TokensClient';
import type { ApiTokenCreateResponse, ApiTokenGet } from 'types/generated';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDate } from '@/src/utils/locale';

const tokensClient = new TokensClient();

const COPY = {
  de: {
    loadFailed: 'Tokens konnten nicht geladen werden',
    createFailed: 'Token konnte nicht erstellt werden',
    heading: 'API-Tokens',
    howAuth: 'So authentifiziert sich dieser Dienst. Setze den Wert als',
    onWorker: 'auf dem Worker; er wird im Header',
    asHeader: 'gesendet.',
    scopesTitle: 'Scopes fügen nur Berechtigungen hinzu – sie nehmen nie welche weg.',
    scopesBody:
      'Ein Token handelt mit den vollen Berechtigungen seines Kontos. Ein Dienstkonto hat keine Rollen, daher sind seine Scopes seine gesamte Berechtigung; ein Token auf einem Benutzerkonto würde alle Rollen dieser Person tragen, unabhängig davon, was hier aufgelistet ist.',
    createdNotice: 'Token erstellt – kopiere es jetzt. Du kannst es danach nicht mehr einsehen.',
    copied: 'Kopiert',
    copy: 'Kopieren',
    dismiss: 'Schließen',
    granted: (n: number) => `${n} Standard-Scope(s) für diesen Diensttyp vergeben:`,
    tokenName: 'Token-Name',
    tokenSuffix: 'Token',
    expires: 'Läuft ab (optional)',
    creating: 'Wird erstellt …',
    create: 'Token erstellen',
    loading: 'Wird geladen …',
    empty: 'Keine aktiven Tokens – dieser Dienst kann sich noch nicht authentifizieren.',
    scopeCount: (n: number) => `${n} Scope(s)`,
    expiresOn: (d: string) => `läuft ab am ${d}`,
    noExpiry: 'läuft nie ab',
    lastUsed: (d: string) => `zuletzt verwendet am ${d}`,
    neverUsed: 'nie verwendet',
    revoke: 'Widerrufen',
    revokeTitle: 'Token widerrufen',
    revokeMessage: (name: string) =>
      `Das Widerrufen von „${name}“ macht es sofort ungültig. Verwendet ein laufender Worker es noch, schlägt dort alles fehl, bis sein API_TOKEN aktualisiert und der Worker neu gestartet wurde.`,
  },
  en: {
    loadFailed: 'Could not load tokens',
    createFailed: 'Could not create token',
    heading: 'API Tokens',
    howAuth: 'How this service authenticates. Set the value as',
    onWorker: 'on the worker, sent as the',
    asHeader: 'header.',
    scopesTitle: 'Scopes only add permissions — they never remove any.',
    scopesBody:
      "A token acts with the full permissions of its account. A service account holds no roles, so its scopes are its entire authority; a token on a human account would carry all of that person's roles regardless of what is listed here.",
    createdNotice: 'Token created — copy it now. You won’t be able to see it again.',
    copied: 'Copied',
    copy: 'Copy',
    dismiss: 'Dismiss',
    granted: (n: number) => `Granted ${n} default scope(s) for this service type:`,
    tokenName: 'Token name',
    tokenSuffix: 'token',
    expires: 'Expires (optional)',
    creating: 'Creating…',
    create: 'Create token',
    loading: 'Loading…',
    empty: 'No active tokens — this service cannot authenticate yet.',
    scopeCount: (n: number) => `${n} scope(s)`,
    expiresOn: (d: string) => `expires ${d}`,
    noExpiry: 'no expiry',
    lastUsed: (d: string) => `last used ${d}`,
    neverUsed: 'never used',
    revoke: 'Revoke',
    revokeTitle: 'Revoke token',
    revokeMessage: (name: string) =>
      `Revoking "${name}" invalidates it immediately. If a running worker is using it, that worker keeps failing until its API_TOKEN is updated and it restarts.`,
  },
} as const;

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
  const language = useUiLanguage();
  const tx = COPY[language];
  const fmtDate = (s?: string | null) => formatDate(s, language);
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
      setError(e instanceof Error ? e.message : tx.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [userId, tx]);

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
      setError(e instanceof Error ? e.message : tx.createFailed);
    } finally {
      setCreating(false);
    }
  }

  const activeTokens = tokens.filter((t) => !t.revoked_at);

  return (
    <div className="bg-surface border border-rule rounded-lg">
      <div className="px-6 py-4 border-b border-rule-soft">
        <h2 className="text-base font-semibold text-fg">{tx.heading}</h2>
        <p className="text-sm text-muted mt-0.5">
          {language === 'de' ? (
            <>
              So authentifiziert sich dieser Dienst. Setze den Wert als{' '}
              <code className="font-mono text-xs">API_TOKEN</code> auf dem Worker; er wird im Header{' '}
              <code className="font-mono text-xs">X-API-Token</code> gesendet.
            </>
          ) : (
            <>
              How this service authenticates. Set the value as <code className="font-mono text-xs">API_TOKEN</code> on
              the worker, sent as the <code className="font-mono text-xs">X-API-Token</code> header.
            </>
          )}
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
          <strong className="font-medium">{tx.scopesTitle}</strong> {tx.scopesBody}
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-danger-line bg-danger-wash px-3 py-2 text-sm text-danger-text">{error}</div>
        )}

        {createdToken && (
          <div className="mb-5 rounded-lg border border-success-line bg-success-wash p-4">
            <p className="text-sm font-medium text-success-text">
              {tx.createdNotice}
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
                className="px-3 py-1.5 text-xs font-medium bg-success text-on-accent rounded hover:bg-success-hover whitespace-nowrap"
              >
                {copied ? tx.copied : tx.copy}
              </button>
              <button
                onClick={() => setCreatedToken(null)}
                className="px-3 py-1.5 text-xs text-muted hover:bg-sunken rounded"
              >
                {tx.dismiss}
              </button>
            </div>
            {createdToken.scopes.length > 0 && (
              <p className="mt-2 text-xs text-success-text">
                {tx.granted(createdToken.scopes.length)}{' '}
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
            <label className="block text-xs font-medium text-body mb-1">{tx.tokenName}</label>
            <input
              className={inputCls}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={`${serviceName} ${tx.tokenSuffix}`}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-body mb-1">{tx.expires}</label>
            <input type="date" className={inputCls} value={newExpiry} onChange={(e) => setNewExpiry(e.target.value)} />
          </div>
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
          >
            {creating ? tx.creating : tx.create}
          </button>
        </form>

        {loading ? (
          <div className="text-sm text-muted">{tx.loading}</div>
        ) : activeTokens.length === 0 ? (
          <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">
            {tx.empty}
          </div>
        ) : (
          <div className="border border-rule rounded-lg divide-y">
            {activeTokens.map((t) => (
              <div key={t.id} className="flex items-center justify-between px-4 py-3 gap-4">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-fg truncate">{t.name}</div>
                  <div className="text-xs text-muted">
                    <span className="font-mono">{t.token_prefix}…</span> · {tx.scopeCount(t.scopes.length)} ·{' '}
                    {t.expires_at ? tx.expiresOn(fmtDate(t.expires_at)) : tx.noExpiry} ·{' '}
                    {t.last_used_at ? tx.lastUsed(fmtDate(t.last_used_at)) : tx.neverUsed}
                  </div>
                </div>
                <button
                  onClick={() => setConfirmRevoke(t)}
                  className="text-sm text-danger-text hover:underline whitespace-nowrap"
                >
                  {tx.revoke}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {confirmRevoke && (
        <ConfirmDialog
          open
          title={tx.revokeTitle}
          message={tx.revokeMessage(confirmRevoke.name)}
          confirmLabel={tx.revoke}
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

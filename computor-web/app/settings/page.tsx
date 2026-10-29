'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { TokensClient } from '@/src/generated/clients/TokensClient';
import { AccountsClient } from '@/src/generated/clients/AccountsClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import ThemePicker from '@/src/components/ThemePicker';
import { inputCls } from '@/src/components/ui/tokens';
import type { ApiTokenGet, ApiTokenCreateResponse, AccountList } from 'types/generated';
import type { ConsentStatusGet, InstanceStatusGet } from '@/src/generated/types/common';
import { ConsentClient } from '@/src/generated/clients/ConsentClient';
import { InstanceStatusClient } from '@/src/generated/clients/InstanceStatusClient';
import { AuthenticationClient } from '@/src/generated/clients/AuthenticationClient';
import DescriptionList from '@/src/components/DescriptionList';
import { WEB_COMMIT, duration, shortCommit } from '@/src/utils/instanceStatus';
import { LEGAL_LINKS, englishLegalLink } from '@/src/config/legal';
import { localeFor } from '@/src/utils/locale';
import { accountConsoleFrom } from '@/src/utils/accountConsole';

const tokensClient = new TokensClient();
const accountsClient = new AccountsClient();
const instanceStatusClient = new InstanceStatusClient();

const authenticationClient = new AuthenticationClient();

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

function fmtDate(s: string | null | undefined, language: UiLanguage): string {
  return s ? new Date(s).toLocaleDateString(localeFor(language)) : '—';
}

function stamp(value: string | null | undefined, language: UiLanguage): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString(localeFor(language));
}

/** Lifetimes offered for a new API token, in days; empty means no expiry. */
const TOKEN_LIFETIME_DAYS = [7, 30, 90, 365];
const DAY_MS = 24 * 60 * 60 * 1000;

const COPY = {
  de: {
    loadFailed: 'Einstellungen konnten nicht geladen werden',
    createFailed: 'Token konnte nicht erstellt werden',
    consentLoadFailed: 'Einwilligungsstatus konnte nicht geladen werden',
    withdrawFailed: 'Einwilligung konnte nicht widerrufen werden',
    settings: 'Einstellungen',
    subtitle: 'Verwalte dein Konto, die Sicherheit und den API-Zugriff.',
    appearance: 'Darstellung',
    appearanceDesc: 'So sieht Computor auf diesem Gerät aus. Wird nicht zwischen Geräten synchronisiert.',
    accountSecurity: 'Konto und Sicherheit',
    accountSecurityDesc: 'In der Kontoverwaltung deines Login-Anbieters änderst du dein Passwort und deine E-Mail-Adresse, richtest die Zwei-Faktor-Authentifizierung ein und meldest andere Geräte ab.',
    openConsole: 'Kontoverwaltung öffnen',
    apiTokens: 'API-Tokens',
    apiTokensDesc: 'Persönliche Zugriffstokens für die CLI, die VS-Code-Erweiterung und Skripte. Behandle sie wie Passwörter.',
    tokenWarnStrong: 'Ein Token hat alle deine Berechtigungen.',
    tokenWarn: 'Wer eines deiner Tokens besitzt, kann alles tun, was du kannst.',
    tokenCreated: 'Token erstellt. Kopiere es jetzt, du kannst es später nicht mehr sehen.',
    copied: 'Kopiert',
    copy: 'Kopieren',
    dismiss: 'Schließen',
    tokenName: 'Token-Name',
    tokenNamePlaceholder: 'z. B. Laptop-CLI',
    expires: 'Gültigkeit',
    lifetimeNever: 'Unbegrenzt',
    lifetimeDays: (days: number) => (days === 365 ? '1 Jahr' : `${days} Tage`),
    creating: 'Wird erstellt …',
    createToken: 'Token erstellen',
    loading: 'Wird geladen …',
    noTokens: 'Keine aktiven Tokens.',
    created: 'erstellt',
    expiresOn: 'läuft ab',
    noExpiry: 'läuft nie ab',
    lastUsed: 'zuletzt verwendet',
    neverUsed: 'nie verwendet',
    revokeTitle: 'Token widerrufen',
    revokeMessage: (name: string) => `Wenn du „${name}“ widerrufst, wird es sofort ungültig. Alles, was es verwendet, funktioniert dann nicht mehr.`,
    revoke: 'Widerrufen',
    accounts: 'Konten',
    accountsDesc: 'Deine Anmelde- und Git-Server-Identitäten.',
    noAccounts: 'Noch keine Konten.',
    builtIn: 'integriert',
    unlinkTitle: 'Konto trennen',
    unlinkMessage: (provider: string, id: string) => `${provider}-Konto „${id}“ trennen?`,
    unlink: 'Trennen',
    privacy: 'Datenschutz und Einwilligung',
    privacyDesc: 'Sieh dir die aktuelle Datenschutzerklärung an und verwalte deine Einwilligung.',
    noNotice: 'Aktuell ist keine Datenschutzerklärung hinterlegt.',
    noConsentNeeded: 'Diese Instanz verlangt keine gesonderte Einwilligung. Was mit deinen Daten geschieht, steht in der Datenschutzerklärung.',
    noticeVersion: 'Version der Datenschutzerklärung:',
    consentGiven: (date: string) => `Einwilligung erteilt am ${date}.`,
    notConsented: 'Du hast der aktuellen Datenschutzerklärung nicht zugestimmt.',
    viewNotice: 'Datenschutzerklärung ansehen',
    withdrawWarn: 'Wenn du die Einwilligung widerrufst, ist der Zugriff auf die Plattform gesperrt, bis du erneut zustimmst. Fortfahren?',
    withdrawing: 'Wird widerrufen …',
    yesWithdraw: 'Ja, widerrufen',
    cancel: 'Abbrechen',
    withdraw: 'Einwilligung widerrufen',
    about: 'Über diese Instanz',
    aboutDesc: 'Welche Version von Computor du nutzt und wann der Server zuletzt neu gestartet wurde.',
    onlineSince: 'Server online seit',
    up: 'Laufzeit',
    version: 'Version',
    lastUpdated: 'Zuletzt aktualisiert',
    devBuild: 'Entwicklungsversion',
    serverCommit: 'Server-Commit',
    webApp: 'Web-App',
    devServer: 'Entwicklungsserver',
  },
  en: {
    loadFailed: 'Failed to load settings',
    createFailed: 'Could not create token',
    consentLoadFailed: 'Failed to load consent status',
    withdrawFailed: 'Failed to withdraw consent',
    settings: 'Settings',
    subtitle: 'Manage your account, security, and API access.',
    appearance: 'Appearance',
    appearanceDesc: 'How Computor looks on this device. Not synced across devices.',
    accountSecurity: 'Account & Security',
    accountSecurityDesc: 'In your login provider’s account console you change your password and email, set up two-factor authentication and sign out other devices.',
    openConsole: 'Open account console',
    apiTokens: 'API tokens',
    apiTokensDesc: 'Personal access tokens for the CLI, VS Code extension and scripts. Treat them like passwords.',
    tokenWarnStrong: 'A token acts with your full permissions.',
    tokenWarn: 'Anyone holding one of your tokens can do anything you can.',
    tokenCreated: 'Token created — copy it now. You won’t be able to see it again.',
    copied: 'Copied',
    copy: 'Copy',
    dismiss: 'Dismiss',
    tokenName: 'Token name',
    tokenNamePlaceholder: 'e.g. laptop CLI',
    expires: 'Valid for',
    lifetimeNever: 'No expiry',
    lifetimeDays: (days: number) => (days === 365 ? '1 year' : `${days} days`),
    creating: 'Creating…',
    createToken: 'Create token',
    loading: 'Loading…',
    noTokens: 'No active tokens.',
    created: 'created',
    expiresOn: 'expires',
    noExpiry: 'no expiry',
    lastUsed: 'last used',
    neverUsed: 'never used',
    revokeTitle: 'Revoke token',
    revokeMessage: (name: string) => `Revoking "${name}" immediately invalidates it. Anything using it will stop working.`,
    revoke: 'Revoke',
    accounts: 'Accounts',
    accountsDesc: 'Your sign-in and Git-server identities.',
    noAccounts: 'No accounts yet.',
    builtIn: 'built-in',
    unlinkTitle: 'Unlink account',
    unlinkMessage: (provider: string, id: string) => `Unlink ${provider} account "${id}"?`,
    unlink: 'Unlink',
    privacy: 'Privacy & Consent',
    privacyDesc: 'Review the current privacy notice and manage your consent.',
    noNotice: 'No privacy notice is currently configured.',
    noConsentNeeded: 'This instance does not ask for separate consent. The privacy notice explains what happens to your data.',
    noticeVersion: 'Privacy notice version:',
    consentGiven: (date: string) => `Consent given on ${date}.`,
    notConsented: 'You have not consented to the current privacy notice.',
    viewNotice: 'View privacy notice',
    withdrawWarn: 'Withdrawing consent will block access to the platform until you consent again. Continue?',
    withdrawing: 'Withdrawing…',
    yesWithdraw: 'Yes, withdraw',
    cancel: 'Cancel',
    withdraw: 'Withdraw consent',
    about: 'About this instance',
    aboutDesc: 'Which version of Computor you are using, and when the server last restarted.',
    onlineSince: 'Server online since',
    up: 'up',
    version: 'Version',
    lastUpdated: 'Last updated',
    devBuild: 'development build',
    serverCommit: 'Server commit',
    webApp: 'Web app',
    devServer: 'development server',
  },
};


const consentClient = new ConsentClient();
export default function SettingsPage() {
  const router = useRouter();
  const { user: authUser, isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const language = useUiLanguage();
  const t = COPY[language];

  const [tokens, setTokens] = useState<ApiTokenGet[]>([]);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // About this instance. Fetched once per visit and never polled: nobody sits on
  // Settings watching for a restart — System → Status is the page that does.
  const [instanceStatus, setInstanceStatus] = useState<InstanceStatusGet | null>(null);
  const [accountConsoleUrl, setAccountConsoleUrl] = useState<string | null>(null);

  // Consent / privacy
  const publishedPrivacy = LEGAL_LINKS.find((link) => link.label === 'Datenschutz');
  const privacyLink =
    publishedPrivacy && language === 'en' ? englishLegalLink(publishedPrivacy) : publishedPrivacy;
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
      const [tk, ac, status, providers] = await Promise.all([
        tokensClient.listTokensEndpointApiTokensGet({}),
        accountsClient.listAccountsAccountsGet({ userId: authUser.id }).catch(() => [] as AccountRow[]),
        // Swallowed on purpose: the About section is the least of what this page
        // is for, and an old deployment that predates the endpoint should not
        // cost the user their tokens list.
        instanceStatusClient.getInstanceStatusInstanceStatusGet().catch(() => null),
        authenticationClient.listProvidersAuthProvidersGet().catch(() => null),
      ]);
      setTokens(tk);
      setAccounts(ac);
      setInstanceStatus(status);
      setAccountConsoleUrl(accountConsoleFrom(providers));
    } catch (e) {
      setError(e instanceof Error ? e.message : t.loadFailed);
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
          expires_at: newExpiry ? new Date(Date.now() + Number(newExpiry) * DAY_MS).toISOString() : null,
        },
      });
      setCreatedToken(created);
      setCopied(false);
      setNewName('');
      setNewExpiry('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t.createFailed);
    } finally {
      setCreating(false);
    }
  }

  const activeTokens = tokens.filter((tok) => !tok.revoked_at);

  useEffect(() => {
    async function fetchConsentStatus() {
      try {
        setConsentStatus(await consentClient.getConsentStatusConsentStatusGet({}));
      } catch (err) {
        setError(err instanceof Error ? err.message : t.consentLoadFailed);
      } finally {
        setConsentLoading(false);
      }
    }
    fetchConsentStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleWithdraw = async () => {
    setWithdrawing(true);
    setError(null);
    try {
      await consentClient.withdrawConsentConsentWithdrawPost({});
      // Access is gated again; the consent page is the only place left to go.
      router.push('/consent');
    } catch (err) {
      setError(err instanceof Error ? err.message : t.withdrawFailed);
      setWithdrawing(false);
      setConfirmWithdraw(false);
    }
  };

  const onlineSince = stamp(instanceStatus?.started_at, language);
  const lastUpdated = stamp(instanceStatus?.build_time, language);
  const serverCommit = shortCommit(instanceStatus?.commit);

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader breadcrumbs={[{ label: t.settings }]} title={t.settings} subtitle={t.subtitle} />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          <div className="space-y-6">
            <Section
              title={t.appearance}
              description={t.appearanceDesc}
            >
              <ThemePicker />
            </Section>

            {/* Account & Security — only shown when the API names an account console */}
            {accountConsoleUrl && (
              <Section title={t.accountSecurity} description={t.accountSecurityDesc}>
                <a
                  href={accountConsoleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover"
                >
                  {t.openConsole}
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </Section>
            )}

            {/* API Tokens */}
            <Section
              title={t.apiTokens}
              description={t.apiTokensDesc}
            >
              {/*
                Scopes are additive claims (PrincipalBuilder.build), so a
                personal token is never weaker than the account. Users assume
                the opposite; say it where the token is minted. The form offers
                no scopes, so the warning does not mention them either.
              */}
              <div className="mb-5 rounded-lg border border-warn-line bg-warn-wash p-3 text-sm text-warn-text">
                <strong className="font-medium">{t.tokenWarnStrong}</strong>{' '}
                {t.tokenWarn}
              </div>

              {createdToken && (
                <div className="mb-5 rounded-lg border border-success-line bg-success-wash p-4">
                  <p className="text-sm font-medium text-success-text">{t.tokenCreated}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="flex-1 font-mono text-xs bg-surface border border-success-line rounded px-2 py-1.5 break-all">{createdToken.token}</code>
                    <button
                      onClick={() => {
                        navigator.clipboard?.writeText(createdToken.token);
                        setCopied(true);
                      }}
                      className="px-3 py-1.5 text-xs font-medium bg-success text-on-accent rounded hover:bg-success-hover whitespace-nowrap"
                    >
                      {copied ? t.copied : t.copy}
                    </button>
                    <button onClick={() => setCreatedToken(null)} className="px-3 py-1.5 text-xs text-muted hover:bg-sunken rounded">{t.dismiss}</button>
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
                  <label className="block text-xs font-medium text-body mb-1">{t.tokenName}</label>
                  <input className={inputCls} value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={t.tokenNamePlaceholder} />
                </div>
                <div>
                  {/*
                    A lifetime rather than <input type="date">: the native date
                    field shows its placeholder in the browser's language
                    (mm/dd/yyyy on an English browser), whatever the page says.
                  */}
                  <label htmlFor="token-expiry" className="block text-xs font-medium text-body mb-1">{t.expires}</label>
                  <select
                    id="token-expiry"
                    className={`${inputCls} !w-auto`}
                    value={newExpiry}
                    onChange={(e) => setNewExpiry(e.target.value)}
                  >
                    <option value="">{t.lifetimeNever}</option>
                    {TOKEN_LIFETIME_DAYS.map((days) => (
                      <option key={days} value={String(days)}>
                        {t.lifetimeDays(days)}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={creating || !newName.trim()}
                  className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
                >
                  {creating ? t.creating : t.createToken}
                </button>
              </form>

              {loading ? (
                <div className="text-sm text-muted">{t.loading}</div>
              ) : activeTokens.length === 0 ? (
                <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">{t.noTokens}</div>
              ) : (
                <div className="border border-rule rounded-lg divide-y divide-rule">
                  {activeTokens.map((tok) => (
                    <div key={tok.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg truncate">{tok.name}</div>
                        <div className="text-xs text-muted">
                          <span className="font-mono">{tok.token_prefix}…</span> · {t.created} {fmtDate(tok.created_at, language)} ·{' '}
                          {tok.expires_at ? `${t.expiresOn} ${fmtDate(tok.expires_at, language)}` : t.noExpiry} ·{' '}
                          {tok.last_used_at ? `${t.lastUsed} ${fmtDate(tok.last_used_at, language)}` : t.neverUsed}
                        </div>
                      </div>
                      <button
                        onClick={() =>
                          setConfirm({
                            title: t.revokeTitle,
                            message: t.revokeMessage(tok.name),
                            confirmWord: tok.name,
                            onConfirm: async () => {
                              await tokensClient.revokeTokenEndpointApiTokensTokenIdDelete({ tokenId: tok.id });
                              await load();
                            },
                          })
                        }
                        className="text-sm text-danger-text hover:underline whitespace-nowrap"
                      >
                        {t.revoke}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* Accounts */}
            <Section
              title={t.accounts}
              description={t.accountsDesc}
            >
              {loading ? (
                <div className="text-sm text-muted">{t.loading}</div>
              ) : accounts.length === 0 ? (
                <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">{t.noAccounts}</div>
              ) : (
                <div className="border border-rule rounded-lg divide-y divide-rule">
                  {accounts.map((a) => (
                    <div key={a.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg capitalize flex items-center gap-2">
                          {a.type || a.provider}
                          {a.builtin && <span className="px-2 py-0.5 text-xs font-medium rounded bg-sunken text-muted capitalize">{t.builtIn}</span>}
                        </div>
                        <div className="text-xs text-muted">
                          <span className="font-mono">{a.provider_account_id}</span> · {a.provider}
                        </div>
                      </div>
                      {(isAdmin || !a.builtin) && (
                        <button
                          onClick={() =>
                            setConfirm({
                              title: t.unlinkTitle,
                              message: t.unlinkMessage(a.provider, a.provider_account_id),
                              confirmWord: a.provider_account_id,
                              onConfirm: async () => {
                                await accountsClient.deleteAccountsAccountsIdDelete({ id: a.id });
                                await load();
                              },
                            })
                          }
                          className="text-sm text-danger-text hover:underline whitespace-nowrap"
                        >
                          {t.unlink}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* Privacy & Consent */}
            <Section
              title={t.privacy}
              description={t.privacyDesc}
            >
              {consentLoading ? (
                <div className="text-sm text-muted">{t.loading}</div>
              ) : !consentStatus?.required_version ? (
                // No in-app consent version is configured, but the deployment
                // may still publish a privacy notice (footer "Datenschutz").
                privacyLink ? (
                  <div className="space-y-4">
                    <p className="text-sm text-body">{t.noConsentNeeded}</p>
                    <a
                      href={privacyLink.href}
                      {...(privacyLink.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                      className="inline-block px-4 py-2 rounded-lg border border-rule-strong text-body hover:bg-canvas text-sm font-medium"
                    >
                      {t.viewNotice}
                    </a>
                  </div>
                ) : (
                  <div className="text-sm text-muted">{t.noNotice}</div>
                )
              ) : (
                <div className="space-y-4">
                  <div className="text-sm text-body space-y-1">
                    <p>
                      {t.noticeVersion}{' '}
                      <span className="font-mono">{consentStatus.required_version}</span>
                    </p>
                    {consentStatus.has_consented && consentStatus.granted_at ? (
                      <p>{t.consentGiven(new Date(consentStatus.granted_at).toLocaleString(localeFor(language)))}</p>
                    ) : (
                      <p className="text-warn-text">{t.notConsented}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <a
                      href="/consent?review=1"
                      className="px-4 py-2 rounded-lg border border-rule-strong text-body hover:bg-canvas text-sm font-medium"
                    >
                      {t.viewNotice}
                    </a>

                    {consentStatus.has_consented && (
                      confirmWithdraw ? (
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="text-sm text-muted">
                            {t.withdrawWarn}
                          </span>
                          <button
                            onClick={handleWithdraw}
                            disabled={withdrawing}
                            className="px-4 py-2 rounded-lg bg-danger text-on-accent hover:bg-danger-hover disabled:bg-faint text-sm font-medium"
                          >
                            {withdrawing ? t.withdrawing : t.yesWithdraw}
                          </button>
                          <button
                            onClick={() => setConfirmWithdraw(false)}
                            disabled={withdrawing}
                            className="px-4 py-2 rounded-lg border border-rule-strong text-body hover:bg-canvas text-sm font-medium"
                          >
                            {t.cancel}
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmWithdraw(true)}
                          className="px-4 py-2 rounded-lg border border-danger-line text-danger-text hover:bg-danger-wash text-sm font-medium"
                        >
                          {t.withdraw}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}
            </Section>

            {/*
              About this instance. Nothing here is privileged — a restart time,
              an uptime and a version label — and "did the server restart?" is
              the first thing anyone asks when something breaks under them. The
              API withholds the running commit from a non-admin, so that row
              simply isn't there for them.
            */}
            {instanceStatus && (
              <Section
                title={t.about}
                description={t.aboutDesc}
              >
                <DescriptionList
                  items={[
                    {
                      term: t.onlineSince,
                      value: onlineSince
                        ? `${onlineSince} · ${t.up} ${duration(instanceStatus.uptime_seconds)}`
                        : '—',
                    },
                    { term: t.version, value: instanceStatus.branch },
                    {
                      term: t.lastUpdated,
                      // No build time means no build: the API is running from a
                      // working tree. Saying so beats a blank where a date belongs.
                      value: lastUpdated ?? t.devBuild,
                    },
                    ...(serverCommit
                      ? [{ term: t.serverCommit, value: serverCommit, mono: true }]
                      : []),
                    {
                      term: t.webApp,
                      value: WEB_COMMIT ? WEB_COMMIT.slice(0, 7) : t.devServer,
                      mono: !!WEB_COMMIT,
                    },
                  ]}
                />
              </Section>
            )}
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

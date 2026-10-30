import type { UiLanguage } from '@/src/hooks/useUiLanguage';

// What Settings calls a linked account. The stored row names the provider by
// its internal id ("keycloak"), its type ("oidc") and, for the Git server, the
// address the backend reaches it at ("http://forgejo:3030"); none of that tells
// a learner which account it is.

export interface AccountLike {
  provider: string;
  type: string;
  provider_account_id: string;
}

const GIT_SERVERS: Record<string, string> = { forgejo: 'Forgejo', gitlab: 'GitLab', github: 'GitHub' };

/** The host of a public address, or null for an internal one (no dot in the host name). */
export function publicHost(address: string): string | null {
  try {
    const host = new URL(address).hostname;
    return host.includes('.') ? host : null;
  } catch {
    return null;
  }
}

/**
 * A readable name and detail line for `account`. The sign-in account shows the
 * user's email rather than the provider's internal user id.
 */
export function accountLabel(
  account: AccountLike,
  language: UiLanguage,
  email?: string | null,
): { name: string; detail: string | null } {
  const type = account.type.toLowerCase();
  if (type === 'oidc' || type === 'saml' || account.provider.toLowerCase() === 'keycloak') {
    return { name: language === 'de' ? 'Computor-Konto' : 'Computor account', detail: email || null };
  }
  const server = GIT_SERVERS[type];
  if (server) {
    const host = publicHost(account.provider);
    const name = language === 'de' ? `Git-Server (${server})` : `Git server (${server})`;
    return { name, detail: [account.provider_account_id, host].filter(Boolean).join(' · ') || null };
  }
  return { name: account.type || account.provider, detail: account.provider_account_id };
}

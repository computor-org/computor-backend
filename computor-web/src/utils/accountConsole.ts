import type { ProviderInfo } from 'types/generated';

/**
 * The login provider's account console, where users change their password and
 * email, set up two-factor authentication and sign out other devices
 * (issues#485, computor-org/issues#557). The API names it from the address
 * sign-in already uses; a build-time NEXT_PUBLIC_KEYCLOAK_URL reached no deployment.
 */
export function accountConsoleFrom(providers: unknown): string | null {
  if (!Array.isArray(providers)) return null;
  const url = (providers as ProviderInfo[]).find((p) => p.account_url)?.account_url;
  return url && /^https?:\/\//.test(url) ? url : null;
}

// Terms of Use version and the date it takes effect for existing contracts.
//
// NEXT_PUBLIC_TERMS_EFFECTIVE_FROM (YYYY-MM-DD) is the one configurable value
// of a terms rollout. The release sets it to release day + TERMS_NOTICE_DAYS in
// the deployment env before the web image is built (inlined at build time like
// NEXT_PUBLIC_LEGAL_PROFILE), and passes the same value to the notice email job
// (computor_backend.support.terms_notice). The terms pages, the changes page and
// the sign-in notice read it from here. Unset: no rollout is scheduled, the
// texts say "the announced date" and no notice is shown.

import { HAS_OWN_LEGAL_PAGES } from './legal';

export const TERMS_VERSION = '1.6';
/** Notice period: E = release day + 35 days (30 days by §11 plus delivery). */
export const TERMS_NOTICE_DAYS = 35;
/** The sign-in notice stays this long after E. */
export const TERMS_NOTICE_GRACE_DAYS = 7;

const DAY_MS = 24 * 60 * 60 * 1000;

export function parseEffectiveDate(raw: string | undefined): string | null {
  const value = raw?.trim() ?? '';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? null : value;
}

export const TERMS_EFFECTIVE_FROM: string | null = parseEffectiveDate(
  process.env.NEXT_PUBLIC_TERMS_EFFECTIVE_FROM,
);

/** The effective date as written in the legal texts (Vienna calendar date). */
export function formatEffectiveDate(iso: string | null, lang: 'de' | 'en'): string {
  if (!iso) return lang === 'de' ? 'dem per E-Mail angekündigten Tag' : 'the date announced by email';
  const [y, m, d] = iso.split('-').map(Number);
  if (lang === 'de') return `${String(d).padStart(2, '0')}.${String(m).padStart(2, '0')}.${y}`;
  const month = new Date(Date.UTC(y, m - 1, d)).toLocaleString('en-GB', { month: 'long', timeZone: 'UTC' });
  return `${d} ${month} ${y}`;
}

/**
 * Whether a signed-in user sees the notice at `now`: only on computor.at, only
 * while a rollout is scheduled, until TERMS_NOTICE_GRACE_DAYS after E, and only
 * for accounts created up to the end of release day (E − TERMS_NOTICE_DAYS).
 * Accounts from the next day on accepted this version at signup; the few
 * created on release day after the deploy see a notice they do not need.
 */
export function termsNoticeDue(
  now: Date,
  createdAt: string | null | undefined,
  effectiveFrom: string | null = TERMS_EFFECTIVE_FROM,
  enabled: boolean = HAS_OWN_LEGAL_PAGES,
): boolean {
  if (!enabled || !effectiveFrom || !createdAt) return false;
  const effective = Date.parse(`${effectiveFrom}T00:00:00Z`);
  const created = Date.parse(createdAt);
  if (Number.isNaN(created)) return false;
  const afterRelease = effective - (TERMS_NOTICE_DAYS - 1) * DAY_MS;
  const end = effective + TERMS_NOTICE_GRACE_DAYS * DAY_MS;
  return created < afterRelease && now.getTime() < end;
}

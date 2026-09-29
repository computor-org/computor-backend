// Same-origin validation for post-login redirect targets (?next= on /login and
// the stored auth_redirect consumed by /auth/success).
//
// Prefix checks on the raw string are not enough: browsers strip tab/CR/LF
// from URLs and treat "\" like "/", so "/\t/evil.example" passes a
// startsWith('/') && !startsWith('//') test and still navigates off-site. The
// target is therefore rejected on any control character or backslash, plain or
// percent-encoded (raw and after one round of percent-decoding), resolved with
// the URL parser against the current origin, and only the parser's canonical
// path is ever navigated to.

const FORBIDDEN = /[\u0000-\u001f\u007f\\]/;
// The same characters percent-encoded (%09, %0A, %7F, %5C, ...), so a value
// that is decoded once more further down the line cannot turn into them.
const FORBIDDEN_ENCODED = /%(?:[01][0-9a-f]|7f|5c)/i;

function hasForbidden(value: string): boolean {
  return FORBIDDEN.test(value) || FORBIDDEN_ENCODED.test(value);
}

/**
 * The canonical same-origin path (`/path?query#hash`) for `raw`, or null when
 * `raw` is missing, not a root-relative path, or could leave `origin`.
 */
export function safeInternalPath(raw: string | null | undefined, origin: string): string | null {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//')) return null;
  if (hasForbidden(raw)) return null;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return null;
  }
  if (hasForbidden(decoded)) return null;
  let url: URL;
  try {
    url = new URL(raw, origin);
  } catch {
    return null;
  }
  if (url.origin !== new URL(origin).origin) return null;
  const canonical = `${url.pathname}${url.search}${url.hash}`;
  // "/.//evil" canonicalises to "//evil", which is protocol-relative again.
  if (!canonical.startsWith('/') || canonical.startsWith('//')) return null;
  return canonical;
}

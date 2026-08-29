/**
 * Formatting for `GET /instance-status`, shared by the two places that read it:
 * System → Status (the operator view, polled) and the About section in Settings
 * (every user, once per visit). One definition so the two never drift into
 * describing the same deployment differently.
 */

// Baked into the web image by computor.sh (docker/web/Dockerfile GIT_COMMIT
// arg); unset under `next dev`. The same constant the sidebar footer shows.
export const WEB_COMMIT = process.env.NEXT_PUBLIC_GIT_COMMIT;

/** A timestamp in the viewer's locale, or null when there isn't one to show. */
export function stamp(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString();
}

/** "1d 6h", "18m" — coarse on purpose, this is read at a glance. */
export function duration(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/**
 * The short hash, or null when there is none to show.
 *
 * Two different absences land here and neither is worth distinguishing in the
 * UI: 'unknown' (an image built without the args) and null (the reader is not
 * an admin, so the API withheld it).
 */
export const shortCommit = (commit?: string | null) =>
  commit && commit !== 'unknown' ? commit.slice(0, 7) : null;

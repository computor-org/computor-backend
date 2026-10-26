/**
 * Shared helpers for the service-accounts admin surface.
 */

/**
 * Languages a testing service may set in `config.language`.
 *
 * Mirrors `TestingBackendFactory._language_backends`
 * (computor-backend/.../testing/backends.py). This is what selects the test
 * runner — the service slug never does; that is the `meta.yaml`
 * `properties.executionBackend.slug` contract and is only an identifier.
 */
export const TESTING_LANGUAGES = [
  'python',
  'octave',
  'r',
  'julia',
  'c',
  'cpp',
  'fortran',
  'document',
  'matlab',
] as const;

import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';

/**
 * Human-readable freshness for a service heartbeat.
 *
 * "Never" is the tell that a worker has not started or cannot reach the API —
 * worth surfacing prominently, since a task queue with no listening worker
 * leaves test workflows queued indefinitely rather than failing.
 */
export function lastSeenLabel(lastSeenAt?: string | null, language: UiLanguage = 'en'): string {
  const de = language === 'de';
  const never = de ? 'nie' : 'never';
  if (!lastSeenAt) return never;

  const seen = new Date(lastSeenAt).getTime();
  if (Number.isNaN(seen)) return never;

  const minutes = Math.floor((Date.now() - seen) / 60000);
  if (minutes < 1) return de ? 'gerade eben' : 'just now';
  if (minutes < 60) return de ? `vor ${minutes} Min.` : `${minutes} min ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return de ? `vor ${hours} Std.` : `${hours} h ago`;

  const days = Math.floor(hours / 24);
  return de ? `vor ${days} ${days === 1 ? 'Tag' : 'Tagen'}` : `${days} d ago`;
}

/** Read `config.language` off a service without fighting the JSON typing. */
export function configLanguage(config?: Record<string, unknown> | null): string {
  const value = config?.language;
  return typeof value === 'string' ? value : '';
}

/** Read `config.temporal.task_queue` off a service. */
export function configTaskQueue(config?: Record<string, unknown> | null): string {
  const temporal = config?.temporal;
  if (temporal && typeof temporal === 'object') {
    const queue = (temporal as Record<string, unknown>).task_queue;
    if (typeof queue === 'string') return queue;
  }
  return '';
}

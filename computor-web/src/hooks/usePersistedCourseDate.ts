'use client';

import { useCallback, useSyncExternalStore } from 'react';

// Same-tab writes are announced on this event; cross-tab ones arrive as `storage`.
const STORE_EVENT = 'computor:persisted-course-date';

function subscribe(onStoreChange: () => void): () => void {
  window.addEventListener('storage', onStoreChange);
  window.addEventListener(STORE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener('storage', onStoreChange);
    window.removeEventListener(STORE_EVENT, onStoreChange);
  };
}

// No localStorage during SSR — must match the client's first paint.
function getServerSnapshot(): string | null {
  return null;
}

// `<input type="datetime-local">` works in the browser's local time and has no
// timezone; convert its value to an ISO instant for storage.
function localInputToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * A date the lecturer configures on a course page, persisted in localStorage.
 *
 * Scoped per course, but with a global "last-used" fallback: a course with no
 * stored value pre-fills from the last date set anywhere (`kind:__last`), so you
 * never start from blank after the first setup. A per-course value always wins.
 *
 * Returns the ISO value and a setter that takes a raw `datetime-local` string.
 */
export function usePersistedCourseDate(
  courseId: string | undefined,
  kind: string,
): [string | null, (localInput: string) => void] {
  const perCourseKey = courseId ? `grading-${kind}:${courseId}` : null;
  const globalKey = `grading-${kind}:__last`;

  // localStorage is an external mutable store, so subscribe to it rather than
  // copying it into state from an effect. The separate server snapshot below
  // keeps SSR returning null (storage does not exist there), which is what makes
  // hydration match — a render-time read would differ between server and client.
  const getSnapshot = useCallback(
    () => (perCourseKey ? read(perCourseKey) ?? read(globalKey) : null),
    [perCourseKey, globalKey],
  );
  const iso = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const set = useCallback(
    (localInput: string) => {
      const next = localInputToIso(localInput);
      try {
        if (next) {
          if (perCourseKey) localStorage.setItem(perCourseKey, next);
          localStorage.setItem(globalKey, next); // remember as the global default
        } else if (perCourseKey) {
          localStorage.removeItem(perCourseKey);
        }
      } catch {
        /* storage unavailable */
      }
      // `storage` only fires in *other* tabs, so announce our own write too.
      window.dispatchEvent(new Event(STORE_EVENT));
    },
    [perCourseKey, globalKey],
  );

  return [iso, set];
}

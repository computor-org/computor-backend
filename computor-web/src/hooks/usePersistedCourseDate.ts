'use client';

import { useCallback, useEffect, useState } from 'react';

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

  const [iso, setIso] = useState<string | null>(null);

  // Load on mount / when the course changes (client-only; localStorage is not
  // available during SSR, so this can't run in a render-time initializer).
  useEffect(() => {
    if (!perCourseKey) return;
    setIso(read(perCourseKey) ?? read(globalKey));
  }, [perCourseKey, globalKey]);

  const set = useCallback(
    (localInput: string) => {
      const next = localInputToIso(localInput);
      setIso(next);
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
    },
    [perCourseKey, globalKey],
  );

  return [iso, set];
}

'use client';

import { useSearchParams } from 'next/navigation';

/**
 * Read a single query param as a string ('' when absent). Like useSearchParams,
 * the component using this must sit under a <Suspense> boundary.
 */
export function useSearchParam(key: string): string {
  return useSearchParams().get(key) ?? '';
}

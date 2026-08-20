'use client';

import Link from 'next/link';

/**
 * Route-level error boundary. Catches uncaught render/runtime errors in any
 * page and offers a retry instead of Next.js's blank default error screen.
 */
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas p-6">
      <div className="max-w-md w-full bg-surface rounded-lg border border-rule p-8 text-center">
        <svg
          className="mx-auto h-12 w-12 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h1 className="mt-4 text-xl font-semibold text-fg">Something went wrong</h1>
        <p className="mt-2 text-sm text-muted">
          An unexpected error occurred. You can try again, or go back to the dashboard.
        </p>
        {error.digest && (
          <p className="mt-2 text-xs text-subtle">Error reference: {error.digest}</p>
        )}
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="px-4 py-2 bg-blue-600 text-on-accent rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Try again
          </button>
          <Link
            href="/dashboard"
            className="px-4 py-2 border border-rule-strong text-body rounded-lg text-sm font-medium hover:bg-canvas"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

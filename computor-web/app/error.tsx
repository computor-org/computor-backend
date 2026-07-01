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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <div className="max-w-md w-full bg-white rounded-lg border border-gray-200 p-8 text-center">
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
        <h1 className="mt-4 text-xl font-semibold text-gray-900">Something went wrong</h1>
        <p className="mt-2 text-sm text-gray-600">
          An unexpected error occurred. You can try again, or go back to the dashboard.
        </p>
        {error.digest && (
          <p className="mt-2 text-xs text-gray-400">Error reference: {error.digest}</p>
        )}
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Try again
          </button>
          <Link
            href="/dashboard"
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

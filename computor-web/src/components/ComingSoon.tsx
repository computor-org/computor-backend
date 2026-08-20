'use client';

import type { ReactNode } from 'react';
import AuthenticatedLayout from './AuthenticatedLayout';
import { ButtonLink } from './ui/Button';

/**
 * "This is planned, but not built yet."
 *
 * Its own component because the app had one visual for three different
 * meanings: NotFound (this address is wrong), Forbidden (this address is fine
 * but you may not see it — it literally wrapped NotFound), and unbuilt features,
 * which rendered the 404 broken-face illustration under the title
 * "Tutor - Coming Soon". A user who lands here has done nothing wrong and the
 * page should not look like a fault.
 */
export default function ComingSoon({
  title,
  message,
  backLink,
  backText = 'Go back',
  children,
}: {
  /** What is coming — "Tutor view", not "Tutor - Coming Soon". */
  title: string;
  message?: string;
  backLink?: string;
  backText?: string;
  /** Anything worth offering meanwhile, e.g. a link to where the work happens today. */
  children?: ReactNode;
}) {
  return (
    <AuthenticatedLayout>
      <div className="min-h-[60vh] flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-4">
          <div className="flex justify-center" aria-hidden="true">
            <svg className="h-16 w-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 8v4l2.5 2.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">Coming soon</p>
            <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
            {message && <p className="text-gray-600">{message}</p>}
          </div>

          {children}

          {backLink && (
            <div className="pt-2">
              <ButtonLink href={backLink} variant="secondary">
                {backText}
              </ButtonLink>
            </div>
          )}
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

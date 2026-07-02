'use client';

/**
 * Root error boundary — catches errors thrown by the root layout itself.
 * Must render its own <html>/<body> because the layout is gone at this point.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif' }}>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem',
            background: '#f9fafb',
          }}
        >
          <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#111827' }}>
              Something went wrong
            </h1>
            <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#4b5563' }}>
              An unexpected error occurred while loading the application.
            </p>
            {error.digest && (
              <p style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#9ca3af' }}>
                Error reference: {error.digest}
              </p>
            )}
            <button
              onClick={reset}
              style={{
                marginTop: '1.5rem',
                padding: '0.5rem 1rem',
                background: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}

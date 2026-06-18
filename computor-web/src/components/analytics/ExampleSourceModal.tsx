'use client';

import { useEffect, useState } from 'react';
import { getExampleSource } from '@/src/api/analytics';
import type { ExampleSource, StandardExampleResult } from './integrity';

/**
 * Source code of one example, shown over the analytics page. An overlay keeps
 * the student detail underneath, so reading an example never loses the curve or
 * the roster selection. Esc or a backdrop click closes it.
 */
export default function ExampleSourceModal({
  courseId,
  example,
  onClose,
}: {
  courseId: string;
  example: StandardExampleResult;
  onClose: () => void;
}) {
  const [source, setSource] = useState<ExampleSource | null>(null);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setActive(0);
      try {
        const s = await getExampleSource(courseId, example.content_id);
        if (cancelled) return;
        setSource(s);
        if (!s) setError('No source available for this example.');
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load source.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, example.content_id]);

  const file = source?.files[active];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 print:hidden"
      role="dialog"
      aria-modal="true"
      aria-label={`Source for ${example.title}`}
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-4 border-b border-gray-200 px-4 py-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-gray-900">{example.title}</h3>
            <p className="truncate font-mono text-xs text-gray-400">{example.path}</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {source?.href && (
              <a href={source.href} className="text-sm font-medium text-blue-600 hover:underline">
                Open full page
              </a>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </header>

        {loading && <p className="p-6 text-sm text-gray-500">Loading source…</p>}
        {error && <p className="p-6 text-sm text-red-600">{error}</p>}

        {source && source.files.length > 0 && (
          <>
            <div className="flex shrink-0 gap-1 overflow-x-auto border-b border-gray-100 bg-gray-50 px-2 py-1.5">
              {source.files.map((f, i) => (
                <button
                  key={f.name}
                  type="button"
                  onClick={() => setActive(i)}
                  className={`rounded px-2.5 py-1 font-mono text-xs ${
                    i === active ? 'bg-white font-medium text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-800'
                  }`}
                >
                  {f.name}
                </button>
              ))}
            </div>
            <pre className="m-0 flex-1 overflow-auto bg-gray-900 p-4 text-xs leading-relaxed text-gray-100">
              <code>{file?.content}</code>
            </pre>
          </>
        )}
      </div>
    </div>
  );
}

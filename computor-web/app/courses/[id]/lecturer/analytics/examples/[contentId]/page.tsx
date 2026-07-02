'use client';


import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import CodeBlock from '@/src/components/analytics/CodeBlock';
import { getExampleSource } from '@/src/api/analytics';
import type { ExampleSource } from '@/src/components/analytics/integrity';

/** Full-page source view for one example, reached from the analytics evidence
 * table. The `student` query param carries the selection back, so "Back" returns
 * to the same student's detail. */
export default function ExampleSourcePage() {
  const params = useParams();
  const courseId = params.id as string;
  const contentId = params.contentId as string;
  const member = useSearchParams().get('student');

  const [source, setSource] = useState<ExampleSource | null>(null);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const backHref = `/courses/${courseId}/lecturer/analytics${member ? `?student=${encodeURIComponent(member)}` : ''}`;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const s = await getExampleSource(courseId, contentId);
        if (cancelled) return;
        setSource(s);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load source.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, contentId]);

  const file = source?.files[active];

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <div>
          <Link href={backHref} className="text-sm text-blue-600 hover:underline">
            ← Back to student
          </Link>
          <div className="mt-2">
            <h1 className="text-2xl font-bold text-gray-900">{source?.title ?? 'Example source'}</h1>
            {source && <p className="font-mono text-xs text-gray-400">{contentId}</p>}
          </div>
        </div>

        <ScrollArea className="space-y-4">
        {loading && <p className="text-sm text-gray-500">Loading source…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!loading && !error && (!source || source.files.length === 0) && (
          <p className="rounded-lg border border-dashed border-gray-200 p-6 text-sm text-gray-500">
            The example source isn’t available in this analytics snapshot. It is served
            from the deployed example repository, which this snapshot doesn’t include yet.
          </p>
        )}

        {source && source.files.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-white">
            <div className="flex gap-1 overflow-x-auto border-b border-gray-100 bg-gray-50 px-2 py-1.5">
              {source.files.map((f, i) => (
                <button
                  key={f.name}
                  type="button"
                  onClick={() => setActive(i)}
                  className={`rounded px-2.5 py-1 font-mono text-xs ${
                    i === active
                      ? 'bg-white font-medium text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-800'
                  }`}
                >
                  {f.name}
                </button>
              ))}
            </div>
            <div className="p-3">
              {file && <CodeBlock filename={file.name} content={file.content} />}
            </div>
          </div>
        )}
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

'use client';

import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import DescriptionList from '@/src/components/DescriptionList';
import SectionCard from '@/src/components/SectionCard';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { InstanceStatusClient } from '@/src/generated/clients/InstanceStatusClient';
import { WEB_COMMIT, duration, shortCommit, stamp } from '@/src/utils/instanceStatus';

const statusClient = new InstanceStatusClient();

/**
 * What is running here, and since when (#350).
 *
 * The two questions an operator asks first — "did it restart?" and "is this the
 * build I deployed?" — had no answer anywhere in the UI. Updates answers a
 * different one ("is there something newer"), which is why this is its own page
 * rather than another card over there.
 *
 * The endpoint itself is readable by any authenticated user and Settings shows
 * the same restart time there. This page stays under /admin with its siblings
 * because it is the operator's view of it: the running commit, which the API
 * only fills in for an admin, and a poll that catches a restart live.
 *
 * The issue also asks for memory, of the host and of each workspace. That is
 * deliberately not here: the API holds no docker socket and nothing collects
 * metrics, so the only workspace memory figure that exists is the per-template
 * cap. A reservation shown under the word "usage" would be read as a
 * measurement, and an operator would size the machine on it.
 */
export default function InstanceStatusPage() {
  const { isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();

  // Polled, so a restart shows up on a page someone left open — which is the
  // moment this page is worth having.
  const { data, loading, error } = useResource(() => statusClient.getInstanceStatusInstanceStatusGet(), [], {
    enabled: isAdmin,
    refetchInterval: 30000,
  });

  if (!authLoading && !isAdmin) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-danger-wash border border-danger-line rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-danger-text">Access Denied</h2>
            <p className="text-sm text-danger-text mt-2">
              Admin privileges are required to access this page.
            </p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const started = stamp(data?.started_at);
  const built = stamp(data?.build_time);
  const commit = shortCommit(data?.commit);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Status' }]}
          title="Status"
          subtitle="When this deployment last restarted, and which build it is running."
        />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          {loading && !data && (
            <div className="bg-surface rounded-lg border border-rule p-6 animate-pulse">
              <div className="h-6 bg-sunken rounded w-1/4 mb-4" />
              <div className="h-4 bg-sunken rounded w-1/2" />
            </div>
          )}

          {data && (
            <SectionCard title="API server">
              <DescriptionList
                items={[
                  {
                    term: 'Last restart',
                    value: started ? `${started} · up ${duration(data.uptime_seconds)}` : '—',
                  },
                  {
                    term: 'Built at',
                    // No build time means no build: the API is running from a
                    // working tree. Saying so beats an em dash nobody can read.
                    value: built ?? 'not a built image (development)',
                  },
                  {
                    term: 'Running commit',
                    value: commit ?? 'unknown',
                    mono: commit != null,
                  },
                  { term: 'Branch', value: data.branch },
                  {
                    term: 'Web build',
                    value: WEB_COMMIT ? WEB_COMMIT.slice(0, 7) : 'development server',
                    mono: !!WEB_COMMIT,
                  },
                ]}
              />
              <p className="text-sm text-muted">
                Whether a newer build exists is a different question —{' '}
                <Link href="/admin/updates" className="text-accent-text hover:underline">
                  System → Updates
                </Link>{' '}
                answers it.
              </p>
            </SectionCard>
          )}
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { CoderClient } from '@/src/clients/CoderClient';
import type { CoderTemplate } from '@/src/types/workspaces';

const coderClient = new CoderClient();

function TemplateIcon({ name }: { name: string }) {
  const lower = name.toLowerCase();
  if (lower.includes('python')) {
    return (
      <div className="p-3 bg-blue-100 rounded-lg">
        <svg className="h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
        </svg>
      </div>
    );
  }
  if (lower.includes('matlab')) {
    return (
      <div className="p-3 bg-orange-100 rounded-lg">
        <svg className="h-8 w-8 text-orange-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M3 3v18h18V3H3zm16 16H5V5h14v14zM7 7h4v4H7V7zm6 0h4v4h-4V7zm-6 6h4v4H7v-4zm6 0h4v4h-4v-4z" />
        </svg>
      </div>
    );
  }
  return (
    <div className="p-3 bg-gray-100 rounded-lg">
      <svg className="h-8 w-8 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    </div>
  );
}

export default function TemplatesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [templates, setTemplates] = useState<CoderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;

    async function fetchTemplates() {
      try {
        const data = await coderClient.listTemplates();
        setTemplates(data.templates);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchTemplates();
  }, [authLoading, isAuthenticated]);

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link href="/workspaces" className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-2">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Workspaces
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">Templates</h1>
            <p className="mt-2 text-gray-600">Browse available workspace templates</p>
          </div>
          {!loading && (
            <div className="text-sm text-gray-500">
              {templates.length} {templates.length === 1 ? 'template' : 'templates'}
            </div>
          )}
        </div>

        {/* Loading */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-14 w-14 bg-gray-200 rounded-lg mb-4" />
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-4 bg-gray-200 rounded w-full" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && templates.length === 0 && (
          <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No templates available</h3>
            <p className="mt-2 text-sm text-gray-500">No workspace templates are currently configured.</p>
          </div>
        )}

        {/* Template Grid */}
        {!loading && !error && templates.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <div key={template.id} className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow flex flex-col">
                <div className="flex items-start gap-4 mb-4">
                  <TemplateIcon name={template.name} />
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-gray-900">{template.display_name || template.name}</h3>
                    {template.description && (
                      <p className="text-sm text-gray-500 mt-1">{template.description}</p>
                    )}
                  </div>
                </div>

                <div className="text-xs text-gray-400 space-y-1 mb-4">
                  <p>ID: {template.id}</p>
                  {template.active_version_id && <p>Version: {template.active_version_id.slice(0, 8)}</p>}
                </div>

                <div className="mt-auto pt-4 border-t border-gray-200">
                  <Link
                    href={`/workspaces/provision?template=${encodeURIComponent(template.name)}`}
                    className="block w-full text-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    Use Template
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

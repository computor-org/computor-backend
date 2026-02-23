'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { CoderClient } from '@/src/clients/CoderClient';
import type {
  CoderTemplate,
  ProvisionResult,
  WorkspaceTemplate,
} from '@/src/types/workspaces';

const coderClient = new CoderClient();

// Fallback templates if API fails
const FALLBACK_TEMPLATES: CoderTemplate[] = [
  { id: 'fallback-python', name: 'python-workspace', display_name: 'Python 3.13 Workspace', description: 'Python development environment' },
  { id: 'fallback-matlab', name: 'matlab-workspace', display_name: 'MATLAB Workspace', description: 'MATLAB development environment' },
];

export default function ProvisionPage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><div className="p-6"><div className="h-10 bg-gray-100 rounded-lg animate-pulse" /></div></AuthenticatedLayout>}>
      <ProvisionPageContent />
    </Suspense>
  );
}

function ProvisionPageContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const preselectedTemplate = searchParams.get('template');

  const [templates, setTemplates] = useState<CoderTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<ProvisionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  // Load templates
  useEffect(() => {
    if (authLoading || !isAuthenticated) return;

    async function fetchTemplates() {
      try {
        const data = await coderClient.listTemplates();
        setTemplates(data.templates.length > 0 ? data.templates : FALLBACK_TEMPLATES);
      } catch {
        setTemplates(FALLBACK_TEMPLATES);
      } finally {
        setLoadingTemplates(false);
      }
    }

    fetchTemplates();
  }, [authLoading, isAuthenticated]);

  // Set preselected template once templates are loaded
  useEffect(() => {
    if (templates.length === 0) return;

    if (preselectedTemplate) {
      const match = templates.find((t) => t.name === preselectedTemplate);
      if (match) {
        setSelectedTemplate(match.name);
        return;
      }
    }

    // Default to first template
    if (!selectedTemplate && templates.length > 0) {
      setSelectedTemplate(templates[0].name);
    }
  }, [templates, preselectedTemplate, selectedTemplate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) return;

    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const data = await coderClient.provisionWorkspace({
        body: { template: selectedTemplate as WorkspaceTemplate },
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-2xl">
        {/* Header */}
        <div>
          <Link href="/workspaces" className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-2">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Workspaces
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Provision Workspace</h1>
          <p className="mt-2 text-gray-600">Create a new development workspace</p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Template Selector */}
            <div>
              <label htmlFor="template" className="block text-sm font-medium text-gray-700 mb-2">
                Workspace Template
              </label>
              {loadingTemplates ? (
                <div className="h-10 bg-gray-100 rounded-lg animate-pulse" />
              ) : (
                <select
                  id="template"
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  <option value="" disabled>Select a template...</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.name}>
                      {t.display_name || t.name}
                    </option>
                  ))}
                </select>
              )}
              {templates.find((t) => t.name === selectedTemplate)?.description && (
                <p className="mt-1 text-sm text-gray-500">
                  {templates.find((t) => t.name === selectedTemplate)?.description}
                </p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting || !selectedTemplate}
              className="w-full px-4 py-3 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? 'Provisioning...' : 'Provision Workspace'}
            </button>
          </form>
        </div>

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

        {/* Success */}
        {result && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <svg className="h-6 w-6 text-green-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="text-lg font-semibold text-green-900">Workspace Provisioned</h3>
            </div>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-green-100">
                <tr>
                  <td className="py-2 font-medium text-green-800 pr-4">User</td>
                  <td className="py-2 text-green-900">{result.user.email}</td>
                </tr>
                {result.workspace && (
                  <tr>
                    <td className="py-2 font-medium text-green-800 pr-4">Workspace</td>
                    <td className="py-2 text-green-900">{result.workspace.name}</td>
                  </tr>
                )}
                <tr>
                  <td className="py-2 font-medium text-green-800 pr-4">Created User</td>
                  <td className="py-2 text-green-900">{result.created_user ? 'Yes' : 'No (existing)'}</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium text-green-800 pr-4">Created Workspace</td>
                  <td className="py-2 text-green-900">{result.created_workspace ? 'Yes' : 'No (existing)'}</td>
                </tr>
              </tbody>
            </table>
            <div className="mt-4">
              <Link
                href="/workspaces"
                className="text-sm font-medium text-green-700 hover:text-green-900"
              >
                Go to Workspaces &rarr;
              </Link>
            </div>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

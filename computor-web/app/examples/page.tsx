'use client';

import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';

export default function ExamplesPage() {
  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Examples</h1>

        <div className="bg-white rounded-lg shadow border border-gray-200 p-12 text-center">
          <svg className="h-16 w-16 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
          </svg>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Examples Page</h2>
          <p className="text-gray-600">This is a placeholder for the examples page. Code examples and learning resources will be displayed here.</p>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

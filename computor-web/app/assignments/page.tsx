'use client';

import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';

export default function AssignmentsPage() {
  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900">Assignments</h1>

        <div className="bg-white rounded-lg shadow border border-gray-200 p-12 text-center">
          <svg className="h-16 w-16 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Assignments Page</h2>
          <p className="text-gray-600">This is a placeholder for the assignments page. Assignment submission and grading features will be implemented here.</p>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

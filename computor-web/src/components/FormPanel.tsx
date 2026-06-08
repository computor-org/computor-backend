'use client';

import type { ReactNode } from 'react';
import Breadcrumbs, { type Crumb } from './Breadcrumbs';

export const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

export function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

/**
 * Standard create/edit page scaffold: breadcrumb trail + title + a card with
 * the form body and a Cancel/Save footer. Used by every entity's create and
 * edit panel so they look and behave identically (replacing the old modals).
 */
export default function FormPanel({
  breadcrumbs,
  title,
  description,
  error,
  onSubmit,
  onCancel,
  submitting,
  submitLabel = 'Save',
  disabled,
  children,
}: {
  breadcrumbs: Crumb[];
  title: string;
  description?: string;
  error?: string | null;
  onSubmit: () => void;
  onCancel: () => void;
  submitting?: boolean;
  submitLabel?: string;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="p-6 max-w-2xl">
      <Breadcrumbs items={breadcrumbs} />
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      {description && <p className="mt-1 text-gray-600">{description}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="mt-6 bg-white border border-gray-200 rounded-lg"
      >
        <div className="p-6 space-y-4">
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}
          {children}
        </div>
        <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex justify-end gap-2 border-t border-gray-100">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || disabled}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? 'Saving…' : submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}

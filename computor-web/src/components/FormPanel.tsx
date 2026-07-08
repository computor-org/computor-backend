'use client';

import { cloneElement, isValidElement, useId, type ReactNode } from 'react';
import { type Crumb } from './Breadcrumbs';
import ListPageLayout, { ScrollArea } from './ListPageLayout';
import PageHeader from './PageHeader';
import ErrorBanner from './ErrorBanner';

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
  // Associate the label with its control so clicking it focuses the input and
  // screen readers announce it. A single element child without an id gets the
  // generated one; multi-element children keep their own ids.
  const generatedId = useId();
  let control = children;
  let htmlFor: string | undefined;
  if (isValidElement<{ id?: string }>(children)) {
    htmlFor = children.props.id ?? generatedId;
    control = children.props.id ? children : cloneElement(children, { id: generatedId });
  }

  return (
    <div>
      <label htmlFor={htmlFor} className="block text-xs font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </label>
      {control}
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

/**
 * Standard create/edit page scaffold: a fixed PageHeader (breadcrumb trail +
 * title) whose Cancel/Save actions sit top-right — OUTSIDE the scroll — with
 * the form body scrolling beneath it. Used by every entity's create and edit
 * panel so they look and behave identically. The header Save button is wired
 * to the form via the HTML `form=` attribute, so Enter-to-submit still works.
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
  const formId = useId();
  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={breadcrumbs}
        title={title}
        subtitle={description}
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              form={formId}
              disabled={submitting || disabled}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Saving…' : submitLabel}
            </button>
          </div>
        }
      />

      <ErrorBanner>{error}</ErrorBanner>

      <ScrollArea>
        <form
          id={formId}
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
          className="max-w-2xl"
        >
          <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">{children}</div>
        </form>
      </ScrollArea>
    </ListPageLayout>
  );
}

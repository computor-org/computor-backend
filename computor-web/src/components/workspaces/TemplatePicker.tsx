'use client';

import type { CoderTemplate } from '@/src/types/workspaces';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';

/**
 * Card-style radio group for choosing a workspace template — shows the real
 * display metadata (display_name / description) that the template push
 * PATCHes into Coder.
 */
export default function TemplatePicker({
  templates,
  value,
  onChange,
}: {
  templates: CoderTemplate[];
  /** Raw template name of the selected template. */
  value: string;
  onChange: (name: string) => void;
}) {
  if (templates.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No templates available — Coder may still be initializing.
      </p>
    );
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="radiogroup">
      {templates.map((t) => {
        const selected = t.name === value;
        return (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(t.name)}
            className={`flex items-start gap-3 rounded-lg border p-4 text-left transition-colors ${
              selected
                ? 'border-blue-600 ring-1 ring-blue-600 bg-blue-50/50'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <TemplateIcon template={t} />
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-gray-900">
                {t.display_name || t.name}
              </span>
              {t.description && (
                <span className="mt-0.5 block text-xs text-gray-500">{t.description}</span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}

'use client';

import type { CoderTemplate } from '@/src/types/workspaces';

/**
 * Template glyph. Coder's `icon` field is authoritative (set from the
 * template.json manifest, e.g. "/icon/python.svg") but those built-in paths
 * live on the internal Coder server, which the browser cannot reach — so
 * known slugs map to local glyphs, absolute http(s) icons render as an image,
 * and everything else falls back to a generic device.
 */
function TemplateIcon({ template }: { template: CoderTemplate }) {
  const hint = `${template.icon ?? ''} ${template.name}`.toLowerCase();

  if (template.icon && /^https?:\/\//.test(template.icon)) {
    return (
      <div className="p-3 bg-gray-100 rounded-lg shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={template.icon} alt="" className="h-8 w-8 object-contain" />
      </div>
    );
  }
  if (hint.includes('python')) {
    return (
      <div className="p-3 bg-blue-100 rounded-lg shrink-0">
        <svg className="h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
        </svg>
      </div>
    );
  }
  if (hint.includes('terminal') || hint.includes('bash')) {
    return (
      <div className="p-3 bg-gray-800 rounded-lg shrink-0">
        <svg className="h-8 w-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M4 5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
        </svg>
      </div>
    );
  }
  if (hint.includes('ubuntu') || hint.includes('desktop')) {
    return (
      <div className="p-3 bg-orange-100 rounded-lg shrink-0">
        <svg className="h-8 w-8 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
    );
  }
  if (hint.includes('debian') || hint.includes('code')) {
    return (
      <div className="p-3 bg-red-100 rounded-lg shrink-0">
        <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      </div>
    );
  }
  return (
    <div className="p-3 bg-gray-100 rounded-lg shrink-0">
      <svg className="h-8 w-8 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    </div>
  );
}

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

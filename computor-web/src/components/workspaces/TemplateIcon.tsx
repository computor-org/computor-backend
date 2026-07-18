'use client';

/**
 * Template glyph. Coder's `icon` field is authoritative (set from the
 * template.json manifest, e.g. "/icon/python.svg") but those built-in paths
 * live on the internal Coder server, which the browser cannot reach — so
 * known slugs map to local glyphs, absolute http(s) icons render as an image,
 * and everything else falls back to a generic device.
 *
 * Accepts anything template-shaped ({ icon, name }) — CoderTemplate or a
 * CourseWorkspaceTemplateItem mapped to { icon, name: template_name }.
 */
export default function TemplateIcon({
  template,
  size = 'md',
}: {
  template: { icon?: string | null; name: string };
  size?: 'md' | 'sm';
}) {
  const hint = `${template.icon ?? ''} ${template.name}`.toLowerCase();
  const pad = size === 'sm' ? 'p-1.5' : 'p-3';
  const dim = size === 'sm' ? 'h-5 w-5' : 'h-8 w-8';

  if (template.icon && /^https?:\/\//.test(template.icon)) {
    return (
      <div className={`${pad} bg-gray-100 rounded-lg shrink-0`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={template.icon} alt="" className={`${dim} object-contain`} />
      </div>
    );
  }
  if (hint.includes('python')) {
    return (
      <div className={`${pad} bg-blue-100 rounded-lg shrink-0`}>
        <svg className={`${dim} text-blue-600`} viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
        </svg>
      </div>
    );
  }
  if (hint.includes('terminal') || hint.includes('bash')) {
    return (
      <div className={`${pad} bg-gray-800 rounded-lg shrink-0`}>
        <svg className={`${dim} text-green-400`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M4 5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
        </svg>
      </div>
    );
  }
  if (hint.includes('ubuntu') || hint.includes('desktop')) {
    return (
      <div className={`${pad} bg-orange-100 rounded-lg shrink-0`}>
        <svg className={`${dim} text-orange-600`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
    );
  }
  if (hint.includes('debian') || hint.includes('code')) {
    return (
      <div className={`${pad} bg-red-100 rounded-lg shrink-0`}>
        <svg className={`${dim} text-red-600`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      </div>
    );
  }
  return (
    <div className={`${pad} bg-gray-100 rounded-lg shrink-0`}>
      <svg className={`${dim} text-gray-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    </div>
  );
}

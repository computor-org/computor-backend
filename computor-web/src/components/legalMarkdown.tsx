import type { Components } from 'react-markdown';

/**
 * The heading and table renderers every legal page uses, shared so the anchor
 * ids stay identical wherever a legal text is rendered — the language switch on
 * the bilingual pages jumps to `#deutsch` and `#english`, which these produce.
 */

function textOf(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  return '';
}

function slug(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export const legalMarkdownComponents: Components = {
  h2: ({ children }) => <h2 id={slug(textOf(children))}>{children}</h2>,
  // Wide tables (the privacy notice's processing overview) scroll
  // inside their own box instead of widening the page on phones.
  table: ({ children }) => (
    <div className="overflow-x-auto">
      <table>{children}</table>
    </div>
  ),
};

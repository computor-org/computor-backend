'use client';

import ReactMarkdown from 'react-markdown';
import { mathMarkdownPlugins } from '../markdownMath';

function normalizeLegacyHtml(markdown: string): string {
  return markdown
    .replace(/<img\s+([^>]*?)\/?\s*>/gi, (_whole, attrs: string) => {
      const src = /\bsrc=["']([^"']+)["']/i.exec(attrs)?.[1];
      if (!src) return '';
      const alt = /\balt=["']([^"']*)["']/i.exec(attrs)?.[1] ?? '';
      return `![${alt}](${src})`;
    })
    .replace(/<\/?div\b[^>]*>/gi, '')
    .replace(/<\/?span\b[^>]*>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n');
}

function publicAssetUrl(base: string, media: string[], value: string): string | undefined {
  const normalized = value.replace(/^\.\//, '');
  if (!normalized.startsWith('mediaFiles/')) return undefined;
  let parts: string[];
  try { parts = normalized.slice('mediaFiles/'.length).split('/').map(decodeURIComponent); }
  catch { return undefined; }
  if (parts.some(part => !/^[a-zA-Z0-9_. -]+$/.test(part) || ['.', '..'].includes(part))) return undefined;
  if (!/\.(?:png|jpe?g|gif|webp)$/i.test(parts.at(-1) ?? '')) return undefined;
  if (!media.includes(parts.join('/'))) return undefined;
  return base + parts.map(encodeURIComponent).join('/');
}

export default function PublicMarkdown({
  assetBaseUrl,
  mediaFiles,
  markdown,
}: {
  assetBaseUrl: string;
  mediaFiles: string[];
  markdown: string;
}) {
  const source = normalizeLegacyHtml(markdown);

  return (
    <div className="prose markdown public-markdown max-w-none">
      <ReactMarkdown
        {...mathMarkdownPlugins}
        skipHtml
        components={{
          a: ({ href, children, ...props }) => (
            <a
              {...props}
              href={href && (/^(?:https?:|mailto:|#)/i.test(href) ? href : publicAssetUrl(assetBaseUrl, mediaFiles, href))}
              target={href && /^https?:/i.test(href) ? '_blank' : undefined}
              rel={href && /^https?:/i.test(href) ? 'noreferrer' : undefined}
            >
              {children}
            </a>
          ),
          img: ({ src, alt, ...props }) => {
            const resolved = typeof src === 'string' ? publicAssetUrl(assetBaseUrl, mediaFiles, src) : undefined;
            if (!resolved) return <span>{alt ?? ''}</span>;
            // Dynamic assignment media has no reliable dimensions in metadata.
            // eslint-disable-next-line @next/next/no-img-element
            return <img {...props} src={resolved} alt={alt ?? ''} className="max-w-full h-auto rounded-md" />;
          },
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}

/** Titles share the reader's math parser while remaining inline inside links. */
export function PublicMarkdownTitle({ markdown }: { markdown: string }) {
  return (
    <ReactMarkdown
      {...mathMarkdownPlugins}
      skipHtml
      components={{
        p: ({ children }) => <>{children}</>,
        a: ({ children }) => <>{children}</>,
        img: () => null,
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
}

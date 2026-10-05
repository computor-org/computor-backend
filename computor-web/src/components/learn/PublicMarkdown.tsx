'use client';

import type { ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import katex from 'katex';

const MATH_RE = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;

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

function mathify(children: ReactNode): ReactNode {
  if (!Array.isArray(children)) {
    return typeof children === 'string' ? mathifyString(children, 'm') : children;
  }
  return children.map((child, index) =>
    typeof child === 'string' ? mathifyString(child, `m${index}`) : child,
  );
}

function mathifyString(text: string, keyPrefix: string): ReactNode {
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  MATH_RE.lastIndex = 0;
  while ((match = MATH_RE.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const displayMode = match[1] !== undefined;
    const expression = (match[1] ?? match[2] ?? '').trim();
    const html = katex.renderToString(expression, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
      output: 'htmlAndMathml',
      trust: false,
      maxExpand: 1000,
      maxSize: 10,
    });
    nodes.push(
      <span
        key={`${keyPrefix}-${match.index}`}
        className={displayMode ? 'block overflow-x-auto py-2' : 'inline'}
        dangerouslySetInnerHTML={{ __html: html }}
      />,
    );
    last = match.index + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes.length > 0 ? nodes : text;
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
    <div className="prose markdown max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          p: ({ children }) => <p>{mathify(children)}</p>,
          li: ({ children }) => <li>{mathify(children)}</li>,
          td: ({ children }) => <td>{mathify(children)}</td>,
          th: ({ children }) => <th>{mathify(children)}</th>,
          strong: ({ children }) => <strong>{mathify(children)}</strong>,
          em: ({ children }) => <em>{mathify(children)}</em>,
          h1: ({ children }) => <h1>{mathify(children)}</h1>,
          h2: ({ children }) => <h2>{mathify(children)}</h2>,
          h3: ({ children }) => <h3>{mathify(children)}</h3>,
          h4: ({ children }) => <h4>{mathify(children)}</h4>,
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

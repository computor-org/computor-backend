'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { mathify } from '@/src/components/learn/PublicMarkdown';

/**
 * A Luna tutor answer, which the model writes as Markdown (issues#457).
 * The text is model output, so it gets no more than formatting: raw HTML is
 * dropped, images show only their alt text (nothing is fetched on the
 * student's behalf) and only http(s) links stay clickable.
 */
export default function LunaAnswer({ answer }: { answer: string }) {
  return (
    <div className="prose markdown max-w-none text-sm" data-testid="luna-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          p: ({ children }) => <p>{mathify(children)}</p>,
          li: ({ children }) => <li>{mathify(children)}</li>,
          strong: ({ children }) => <strong>{mathify(children)}</strong>,
          em: ({ children }) => <em>{mathify(children)}</em>,
          a: ({ href, children }) =>
            href && /^https?:\/\//i.test(href) ? (
              <a href={href} target="_blank" rel="noreferrer nofollow">{children}</a>
            ) : (
              <span>{children}</span>
            ),
          img: ({ alt }) => <span>{alt ?? ''}</span>,
        }}
      >
        {answer}
      </ReactMarkdown>
    </div>
  );
}

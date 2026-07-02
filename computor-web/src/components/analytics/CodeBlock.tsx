'use client';

import { useMemo } from 'react';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import bash from 'highlight.js/lib/languages/bash';
import markdown from 'highlight.js/lib/languages/markdown';
import json from 'highlight.js/lib/languages/json';
import 'highlight.js/styles/github-dark.css';

hljs.registerLanguage('python', python);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('json', json);

const BY_EXT: Record<string, string> = {
  py: 'python',
  sh: 'bash',
  bash: 'bash',
  md: 'markdown',
  json: 'json',
};

function languageFor(filename: string): string | null {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  return BY_EXT[ext] ?? null;
}

/** Syntax-highlighted source for one file via highlight.js. */
export default function CodeBlock({ filename, content }: { filename: string; content: string }) {
  const html = useMemo(() => {
    const lang = languageFor(filename);
    try {
      if (lang && hljs.getLanguage(lang)) return hljs.highlight(content, { language: lang }).value;
      return hljs.highlightAuto(content).value;
    } catch {
      return null;
    }
  }, [filename, content]);

  return (
    <pre className="m-0 overflow-auto rounded-md bg-[#0d1117] p-4 text-xs leading-relaxed">
      {html === null ? (
        <code className="hljs text-gray-100">{content}</code>
      ) : (
        <code className="hljs" dangerouslySetInnerHTML={{ __html: html }} />
      )}
    </pre>
  );
}

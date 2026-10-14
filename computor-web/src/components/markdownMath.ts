import type { Options } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// Parse TeX before Markdown can consume its backslashes or underscores.
// Keep code spans/fences literal and disallow trusted HTML/URL math commands.
export const mathMarkdownPlugins: Pick<Options, 'remarkPlugins' | 'rehypePlugins'> = {
  remarkPlugins: [remarkGfm, remarkMath],
  rehypePlugins: [[rehypeKatex, {
    strict: 'ignore',
    trust: false,
    maxExpand: 1000,
    maxSize: 10,
    output: 'htmlAndMathml',
  }]],
};

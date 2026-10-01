import Link from 'next/link';

export const PUBLIC_COURSES_URL = 'https://github.com/computor-org/data-science-python';
export const CODESPACES_URL = 'https://codespaces.new/computor-org/data-science-python?quickstart=1';
export const COMPUTOR_EXTENSION_URL = 'https://marketplace.visualstudio.com/items?itemName=computor-org.computor';

export default function LearningOptions({ capacity = false }: { capacity?: boolean }) {
  return (
    <aside aria-label="Learning options" className="rounded-lg border border-rule bg-surface p-5 text-left">
      <h3 className="text-lg font-semibold text-fg">
        {capacity ? 'Hosted workspaces are full. Keep working:' : 'Choose where to work'}
      </h3>
      <div className="mt-3 flex flex-wrap gap-4 text-accent-text">
        {!capacity && <Link href="/workspaces" className="underline">Hosted workspace</Link>}
        <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noopener noreferrer" className="underline">Desktop VS Code</a>
        <a href={CODESPACES_URL} target="_blank" rel="noopener noreferrer" className="underline">GitHub Codespaces</a>
        <Link href="/learn" className="underline">Read courses</Link>
      </div>
      <p className="mt-3 text-sm text-muted">
        Codespaces uses your GitHub quota. Sign in to submit work or ask Luna.
      </p>
    </aside>
  );
}

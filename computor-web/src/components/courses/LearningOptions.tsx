'use client';

import Link from 'next/link';
import { useBrowserLanguage, type UiLanguage } from '@/src/hooks/useBrowserLanguage';

export const PUBLIC_COURSES_URL = 'https://github.com/computor-org/data-science-python';
export const CODESPACES_URL = 'https://codespaces.new/computor-org/data-science-python?quickstart=1';
export const COMPUTOR_EXTENSION_URL = 'https://marketplace.visualstudio.com/items?itemName=computor-org.computor';

const COPY = {
  de: {
    options: 'Lernmöglichkeiten',
    full: 'Alle Arbeitsumgebungen im Browser sind belegt. Weiterarbeiten mit:',
    choose: 'Wo möchtest du arbeiten?',
    hosted: 'Im Browser arbeiten',
    read: 'Kurse anschauen',
    note: 'Codespaces nutzt dein GitHub-Kontingent. Zum Einreichen und für Fragen an Lena melde dich an.',
  },
  en: {
    options: 'Learning options',
    full: 'Hosted workspaces are full. Keep working:',
    choose: 'Choose where to work',
    hosted: 'Hosted workspace',
    read: 'Read courses',
    note: 'Codespaces uses your GitHub quota. Sign in to submit work or ask Lena.',
  },
};

export default function LearningOptions({ capacity = false, language }: { capacity?: boolean; language?: UiLanguage }) {
  const browserLanguage = useBrowserLanguage();
  const t = COPY[language ?? browserLanguage];
  return (
    <aside aria-label={t.options} className="rounded-lg border border-rule bg-surface p-5 text-left">
      <h3 className="text-lg font-semibold text-fg">
        {capacity ? t.full : t.choose}
      </h3>
      <div className="mt-3 flex flex-wrap gap-4 text-accent-text">
        {!capacity && <Link href="/workspaces" className="underline">{t.hosted}</Link>}
        <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noopener noreferrer" className="underline">Desktop VS Code</a>
        <a href={CODESPACES_URL} target="_blank" rel="noopener noreferrer" className="underline">GitHub Codespaces</a>
        <Link href="/learn" className="underline">{t.read}</Link>
      </div>
      <p className="mt-3 text-sm text-muted">
        {t.note}
      </p>
    </aside>
  );
}

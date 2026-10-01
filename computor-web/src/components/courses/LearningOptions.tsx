import Link from 'next/link';

export const PUBLIC_COURSES_URL = 'https://github.com/computor-org/data-science-python';
export const CODESPACES_URL = 'https://codespaces.new/computor-org/data-science-python?quickstart=1';
export const COMPUTOR_EXTENSION_URL = 'https://marketplace.visualstudio.com/items?itemName=computor-org.computor';

export default function LearningOptions({ capacity = false }: { capacity?: boolean }) {
  return (
    <aside aria-label="Learning options" className="rounded-lg border border-rule bg-surface p-5 text-left">
      <h3 className="text-lg font-semibold text-fg">
        {capacity ? 'Weiterlernen bei voller Kapazität / Keep learning at capacity' : 'Frei lernen / Learn freely'}
      </h3>
      <p className="mt-2 text-muted">
        Kurse und Beispiele ohne Anmeldung lesen. Code auf deinem Computer oder in deinem GitHub Codespace ausführen.
        {' '}Read courses without signing in; practice on your computer or in your GitHub Codespace.
      </p>
      <div className="mt-3 flex flex-wrap gap-4 text-accent-text">
        <Link href="/learn" className="underline">Kurse lesen / Read courses</Link>
        <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noopener noreferrer" className="underline">Desktop VS Code</a>
        <a href={CODESPACES_URL} target="_blank" rel="noopener noreferrer" className="underline">GitHub Codespaces</a>
      </div>
      <p className="mt-3 text-sm text-muted">
        Codespaces benötigt ein GitHub-Konto und nutzt dein Kontingent. Der Hackl-Tutor verwendet deinen eigenen
        externen KI-Schlüssel; lokal kannst du auch ein lokales Modell verwenden.
        {' '}Codespaces needs a GitHub account and uses your quota. Bring your own AI provider key;
        desktop VS Code also supports local models. Computor login is needed for progress, submissions and server grading.
      </p>
    </aside>
  );
}

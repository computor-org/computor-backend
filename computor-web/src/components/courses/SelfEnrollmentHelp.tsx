'use client';

import { useState, type ReactNode } from 'react';
import Link from 'next/link';
import SectionCard from '@/src/components/SectionCard';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Button from '@/src/components/ui/Button';
import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';

// The learner documentation lives with the VS Code extension, which is also
// what runs in the browser workspace. It is written in English only.
const DOCS = 'https://github.com/computor-org/computor-vscode/blob/main/docs';
const HELP = {
  browser: `${DOCS}/user-guide.md#student-guide`,
  local: `${DOCS}/user-guide.md#getting-started`,
  course: `${DOCS}/help/student-course.md`,
  unit: `${DOCS}/help/student-unit.md`,
  assignment: `${DOCS}/help/student-assignment.md`,
  files: `${DOCS}/user-guide.md#keeping-a-copy-of-your-work`,
};

const mention = (text: string) => <code className="rounded bg-canvas px-1 font-mono text-[0.9em]">{text}</code>;

const COPY = {
  de: {
    title: 'Hilfe & Kontakt',
    lena: <>Fragen zum Kurs? Schreib {mention('@lena')} in die Nachrichten einer Aufgabe. Technische Probleme:</>,
    report: 'Problem melden',
    more: 'Mehr Hilfe',
    guides: 'Anleitungen (auf Englisch)',
    browser: 'Im Browser arbeiten',
    local: 'Mit VS Code auf dem eigenen Rechner arbeiten',
    structure: 'Kurse, Einheiten und Aufgaben:',
    course: 'Kurse',
    unit: 'Einheiten',
    assignment: 'Aufgaben',
    files: 'Eigene Dateien herunterladen',
    filesHow: (
      <>
        : In VS Code mit Rechtsklick auf den Kurs „Kursaufgaben exportieren…“ wählen. Deine Aufgaben werden
        als ZIP-Datei gespeichert.
      </>
    ),
    leave: 'Kurs verlassen',
    leaving: 'Wird verlassen …',
    confirmTitle: 'Kurs verlassen?',
    confirmMessage: (title: string) => `Du wirst aus ${title} ausgetragen. Deine Abgaben bleiben gespeichert.`,
    account: 'Soll dein ganzes Konto gelöscht werden? Das geht über eine Anfrage an den Support:',
    deleteAccount: 'Konto löschen',
  },
  en: {
    title: 'Help & contact',
    lena: <>Questions? Write {mention('@lena')} in an assignment&apos;s messages. Technical problems:</>,
    report: 'Report a problem',
    more: 'More help',
    guides: 'Guides',
    browser: 'Working in the browser',
    local: 'Working with VS Code on your own computer',
    structure: 'Courses, units and assignments:',
    course: 'Courses',
    unit: 'Units',
    assignment: 'Assignments',
    files: 'Downloading your own files',
    filesHow: (
      <>
        : in VS Code, right-click the course and choose “Export Course Examples…”. Your assignments are
        saved as a ZIP file.
      </>
    ),
    leave: 'Leave course',
    leaving: 'Leaving…',
    confirmTitle: 'Leave this course?',
    confirmMessage: (title: string) => `You leave ${title}. Your submissions are kept.`,
    account: 'Do you want your whole account deleted? Send a request to support:',
    deleteAccount: 'Delete account',
  },
};

function External({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline">
      {children}
    </a>
  );
}

/**
 * Help and contact for a course the learner joined through the catalog
 * (issues#458). A self-enrolled learner has no lecturer or tutor to ask, so
 * the course page says who answers what and where the guides are, and offers
 * the way out of the course that the catalog's join dialog promises.
 */
export default function SelfEnrollmentHelp({
  courseId,
  courseTitle,
  canLeave,
  language,
  onLeave,
}: {
  courseId: string;
  courseTitle: string;
  canLeave: boolean;
  language: UiLanguage;
  onLeave: () => Promise<void>;
}) {
  const t = COPY[language];
  const [confirming, setConfirming] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const from = encodeURIComponent(`/courses/${courseId}`);

  async function leave() {
    setLeaving(true);
    try {
      await onLeave();
    } finally {
      setLeaving(false);
      setConfirming(false);
    }
  }

  return (
    <SectionCard title={t.title}>
      <p className="text-sm text-body">
        {t.lena}{' '}
        <Link href={`/problem?from=${from}`} className="text-accent-text hover:underline">
          {t.report}
        </Link>
        .
      </p>

      {/* Guides, export and account deletion only on request. */}
      <details className="text-sm text-body">
        <summary className="cursor-pointer text-accent-text hover:underline">{t.more}</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 marker:text-muted">
          <li>
            {t.guides}: <External href={HELP.browser}>{t.browser}</External>
            {', '}
            <External href={HELP.local}>{t.local}</External>
          </li>
          <li>
            {t.structure} <External href={HELP.course}>{t.course}</External>
            {', '}
            <External href={HELP.unit}>{t.unit}</External>
            {', '}
            <External href={HELP.assignment}>{t.assignment}</External>
          </li>
          <li>
            <External href={HELP.files}>{t.files}</External>
            {t.filesHow}
          </li>
          <li>
            {t.account}{' '}
            <Link href={`/problem?topic=delete-account&from=${from}`} className="text-accent-text hover:underline">
              {t.deleteAccount}
            </Link>
          </li>
        </ul>
      </details>

      {canLeave && (
        <Button variant="ghost" size="xs" onClick={() => setConfirming(true)}>
          {t.leave}
        </Button>
      )}

      <ConfirmDialog
        open={confirming}
        title={t.confirmTitle}
        message={t.confirmMessage(courseTitle)}
        confirmLabel={leaving ? t.leaving : t.leave}
        variant="danger"
        onCancel={() => setConfirming(false)}
        onConfirm={() => { if (!leaving) void leave(); }}
      />
    </SectionCard>
  );
}

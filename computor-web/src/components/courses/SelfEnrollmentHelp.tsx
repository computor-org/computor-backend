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
    lena: (
      <>
        In diesem Kurs gibt es keine Tutorinnen und Tutoren, die Nachrichten beantworten. Fragen zum
        Kursinhalt beantwortet die KI-Tutorin Lena: Schreib {mention('@lena')} in die Nachrichten zu
        einer Aufgabe. Lena gibt Hinweise statt fertiger Lösungen.
      </>
    ),
    support: 'Probleme mit der Plattform oder mit deinem Konto meldest du dem Computor-Support-Team über',
    report: 'Problem melden',
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
    leaveTitle: 'Kurs verlassen',
    leaveText:
      'Du bist diesem Kurs selbst beigetreten und kannst ihn auch selbst wieder verlassen. Deine Abgaben und Ergebnisse bleiben gespeichert.',
    leave: 'Kurs verlassen',
    leaving: 'Wird verlassen …',
    confirmTitle: 'Kurs verlassen?',
    confirmMessage: (title: string) =>
      `Du wirst aus ${title} ausgetragen und siehst den Kurs nicht mehr unter „Meine Kurse“. ` +
      'Deine Abgaben und Ergebnisse bleiben gespeichert. Trittst du dem Kurs später über den Katalog wieder bei, ist alles wieder da.',
    account: 'Soll dein ganzes Konto gelöscht werden? Das geht über eine Anfrage an den Support:',
    deleteAccount: 'Konto löschen',
  },
  en: {
    title: 'Help & contact',
    lena: (
      <>
        This course has no tutors who answer messages. Questions about the course content are answered
        by Lena, the AI tutor: write {mention('@lena')} in the messages of an assignment. Lena gives hints
        instead of complete solutions.
      </>
    ),
    support: 'Problems with the platform or your account go to the Computor support team via',
    report: 'Report a problem',
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
    leaveTitle: 'Leave the course',
    leaveText:
      'You joined this course yourself and can leave it yourself. Your submissions and results are kept.',
    leave: 'Leave course',
    leaving: 'Leaving…',
    confirmTitle: 'Leave this course?',
    confirmMessage: (title: string) =>
      `You will be removed from ${title} and no longer see it under “My courses”. ` +
      'Your submissions and results are kept. If you join the course again from the catalog, everything is back.',
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
      <p className="text-body">{t.lena}</p>
      <p className="text-sm text-body">
        {t.support}{' '}
        <Link href={`/problem?from=${from}`} className="text-accent-text hover:underline">
          {t.report}
        </Link>
        .
      </p>

      <div>
        <h3 className="text-sm font-semibold text-fg">{t.guides}</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-body marker:text-muted">
          <li><External href={HELP.browser}>{t.browser}</External></li>
          <li><External href={HELP.local}>{t.local}</External></li>
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
        </ul>
      </div>

      <div className="space-y-3 border-t border-rule-soft pt-4">
        {canLeave && (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-fg">{t.leaveTitle}</h3>
              <p className="mt-1 text-sm text-muted">{t.leaveText}</p>
            </div>
            <Button variant="secondary" className="shrink-0 self-start sm:self-center" onClick={() => setConfirming(true)}>
              {t.leave}
            </Button>
          </div>
        )}
        <p className="text-sm text-muted">
          {t.account}{' '}
          <Link href={`/problem?topic=delete-account&from=${from}`} className="text-accent-text hover:underline">
            {t.deleteAccount}
          </Link>
        </p>
      </div>

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

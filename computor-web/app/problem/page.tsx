'use client';

import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PublicLearnShell from '@/src/components/learn/PublicLearnShell';
import ListPageLayout, { ScrollArea, PageLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import FileInput from '@/src/components/ui/FileInput';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { APP_VERSION } from '@/src/utils/appVersion';
import { safeInternalPath } from '@/src/utils/safeRedirect';
import {
  createReport,
  fetchIssueReportingMode,
  ReportError,
  type ReportReceipt,
} from '@/src/clients/SupportClient';

const CONTACT = 'contact@computor.at';

// Preset ticket categories (issues#458). The topic travels in the report
// context and the preset title becomes the ticket subject the team sees.
type Topic = 'problem' | 'delete-account';
const TOPICS: Topic[] = ['problem', 'delete-account'];
const MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024;
const SCREENSHOT_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];

const COPY = {
  de: {
    title: 'Problem melden',
    subtitle: 'Schreib uns, was nicht funktioniert.',
    home: 'Start',
    privacy:
      'Deine Meldung geht an das Computor-Support-Team. Sie wird nicht veröffentlicht. Der Screenshot sollte keine Daten anderer Personen zeigen.',
    titleLabel: 'Titel (optional)',
    description: 'Was ist das Problem?',
    expected: 'Was hast du erwartet? (optional)',
    steps: 'Wie lässt sich das Problem nachstellen? (optional)',
    screenshot: 'Screenshot (optional, PNG, JPEG, GIF oder WebP, höchstens 5 MB)',
    screenshotType: 'Der Screenshot muss ein PNG, JPEG, GIF oder WebP sein.',
    screenshotSize: 'Der Screenshot ist größer als 5 MB.',
    send: 'Meldung senden',
    sending: 'Wird gesendet …',
    failed: 'Die Meldung konnte nicht gesendet werden.',
    rateLimited: (min: number) => `Du hast gerade erst eine Meldung gesendet. Bitte warte etwa ${min} Min.`,
    offTitle: 'Meldungen sind hier nicht möglich',
    offText: 'Auf dieser Instanz ist keine Problemmeldung eingerichtet. Schreib uns bitte per Mail an',
    thanks: 'Danke für deine Meldung.',
    ticket: (n: number) => `Ticket #${n}`,
    report: (n: number) => `Meldung #${n}`,
    follow: 'Meldung ansehen',
    myReports: 'Meine Meldungen',
    another: 'Weitere Meldung',
    signInTitle: 'Zum Melden ist eine Anmeldung nötig',
    signInText: 'Melde dich an, um ein Problem an das Support-Team zu schicken. Ohne Konto schreib uns bitte per Mail an',
    signIn: 'Anmelden',
    content: 'Rechtswidrige Inhalte melden',
    loading: 'Wird geladen …',
    topic: 'Anliegen',
    topics: { problem: 'Problem mit der Plattform', 'delete-account': 'Konto löschen' },
    deleteTitle: 'Konto löschen',
    request: 'Deine Anfrage',
    deleteDescription: 'Bitte löscht mein Computor-Konto.',
    deleteHint:
      'Schick diese Anfrage ab, wenn dein Konto gelöscht werden soll. Das Support-Team antwortet dir unter „Meine Meldungen“, bevor etwas gelöscht wird. Um nur einen selbst gewählten Kurs zu verlassen, nutze „Kurs verlassen“ auf der Kursseite.',
  },
  en: {
    title: 'Report a problem',
    subtitle: 'Tell us what is not working.',
    home: 'Home',
    privacy:
      'Your report goes to the Computor support team. It is not published. The screenshot should not show other people\'s data.',
    titleLabel: 'Title (optional)',
    description: 'What is the problem?',
    expected: 'What did you expect? (optional)',
    steps: 'How can the problem be reproduced? (optional)',
    screenshot: 'Screenshot (optional, PNG, JPEG, GIF or WebP, 5 MB at most)',
    screenshotType: 'The screenshot must be a PNG, JPEG, GIF or WebP image.',
    screenshotSize: 'The screenshot is larger than 5 MB.',
    send: 'Send report',
    sending: 'Sending…',
    failed: 'The report could not be sent.',
    rateLimited: (min: number) => `You just sent a report. Please wait about ${min} min.`,
    offTitle: 'Reports are not available here',
    offText: 'This instance has no problem reporting set up. Please write to us by email at',
    thanks: 'Thank you for your report.',
    ticket: (n: number) => `Ticket #${n}`,
    report: (n: number) => `Report #${n}`,
    follow: 'View your report',
    myReports: 'My reports',
    another: 'Send another report',
    signInTitle: 'Reporting needs a sign-in',
    signInText: 'Sign in to send a problem to the support team. Without an account please write to us by email at',
    signIn: 'Sign in',
    content: 'Report illegal content',
    loading: 'Loading…',
    topic: 'Topic',
    topics: { problem: 'Problem with the platform', 'delete-account': 'Delete account' },
    deleteTitle: 'Delete account',
    request: 'Your request',
    deleteDescription: 'Please delete my Computor account.',
    deleteHint:
      'Send this request if you want your account deleted. The support team replies under “My reports” before anything is deleted. To leave only a course you joined yourself, use “Leave course” on the course page.',
  },
};

function Mail() {
  return (
    <a href={`mailto:${CONTACT}`} className="text-accent-text hover:underline">
      {CONTACT}
    </a>
  );
}

export default function ProblemPage() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  return isAuthenticated ? (
    <AuthenticatedLayout>
      <ListPageLayout>
        <ReportForm />
      </ListPageLayout>
    </AuthenticatedLayout>
  ) : (
    <PublicLearnShell>
      <div className="container mx-auto max-w-2xl px-4 py-10">
        <SignedOut />
      </div>
    </PublicLearnShell>
  );
}

function Header({ children }: { children?: ReactNode }) {
  const t = COPY[useUiLanguage()];
  return (
    <>
      <PageHeader breadcrumbs={[{ label: t.title }]} title={t.title} subtitle={t.subtitle} />
      {children}
    </>
  );
}

function SignedOut() {
  const t = COPY[useUiLanguage()];
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-fg">{t.signInTitle}</h1>
      <p className="text-muted">
        {t.signInText} <Mail />.
      </p>
      <Link href="/login?next=%2Fproblem" className="inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-hover">
        {t.signIn}
      </Link>
    </div>
  );
}

function ReportForm() {
  const language = useUiLanguage();
  const t = COPY[language];
  const [mode, setMode] = useState<'loading' | 'on' | 'off'>('loading');
  const [topic, setTopic] = useState<Topic>('problem');
  const deleting = topic === 'delete-account';
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [expected, setExpected] = useState('');
  const [steps, setSteps] = useState('');
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [fileKey, setFileKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [receipt, setReceipt] = useState<ReportReceipt | null>(null);

  const chooseTopic = (next: Topic) => {
    setTopic(next);
    if (next === 'delete-account') {
      setTitle(t.deleteTitle);
      setDescription((current) => current.trim() ? current : t.deleteDescription);
    } else if (title === t.deleteTitle) {
      setTitle('');
      if (description === t.deleteDescription) setDescription('');
    }
  };

  // A link may preset the topic, e.g. "Konto löschen" on a course page.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('topic') === 'delete-account') chooseTopic('delete-account');
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, on arrival
  }, []);

  useEffect(() => {
    let live = true;
    void fetchIssueReportingMode().then((info) => {
      if (live) setMode(info && (!info.enabled || info.mode === 'off') ? 'off' : 'on');
    });
    return () => {
      live = false;
    };
  }, []);

  const pickFile = (file: File | null) => {
    setError(null);
    if (file && !SCREENSHOT_TYPES.includes(file.type)) {
      setError(t.screenshotType);
    } else if (file && file.size > MAX_SCREENSHOT_BYTES) {
      setError(t.screenshotSize);
    } else {
      setScreenshot(file);
      return;
    }
    setScreenshot(null);
    setFileKey((k) => k + 1);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSending(true);
    setError(null);
    const from = safeInternalPath(new URLSearchParams(window.location.search).get('from'), window.location.origin);
    try {
      setReceipt(
        await createReport({
          title: title.trim() || undefined,
          description: description.trim(),
          expected: (!deleting && expected.trim()) || undefined,
          steps: (!deleting && steps.trim()) || undefined,
          context: {
            client: 'computor-web',
            client_version: APP_VERSION,
            page: from ?? undefined,
            language: navigator.language,
            topic: deleting ? 'delete_account' : undefined,
          },
          screenshot: deleting ? null : screenshot,
        }),
      );
    } catch (err) {
      if (err instanceof ReportError && err.status === 404) setMode('off');
      else if (err instanceof ReportError && err.status === 429) {
        setError(t.rateLimited(Math.max(1, Math.ceil((err.retryAfter ?? 300) / 60))));
      } else setError(err instanceof Error && err.message ? err.message : t.failed);
    } finally {
      setSending(false);
    }
  };

  if (mode === 'loading') {
    return <Header><p className="text-muted">{t.loading}</p></Header>;
  }
  if (mode === 'off') {
    return (
      <Header>
        <div className="rounded-lg border border-rule bg-surface p-4">
          <h2 className="font-medium text-fg">{t.offTitle}</h2>
          <p className="mt-1 text-muted">
            {t.offText} <Mail />.
          </p>
        </div>
      </Header>
    );
  }
  if (receipt) {
    const label = receipt.ticket_number != null ? t.ticket(receipt.ticket_number) : t.report(receipt.issue_number);
    return (
      <Header>
        <div role="status" className="space-y-3 rounded-lg border border-rule bg-surface p-4">
          <p className="font-medium text-fg">{t.thanks}</p>
          <p className="text-muted">{label}</p>
          <div className="flex gap-4 text-sm">
            {receipt.ticket_id && (
              <Link href={`/support/${receipt.ticket_id}`} className="text-accent-text hover:underline">
                {t.follow}
              </Link>
            )}
            <Link href="/support" className="text-accent-text hover:underline">
              {t.myReports}
            </Link>
          </div>
        </div>
      </Header>
    );
  }

  return (
    <Header>
      <ScrollArea>
        <form onSubmit={submit} className="max-w-2xl space-y-4">
          <p className="text-sm text-muted">{t.privacy}</p>
          <ErrorBanner>{error}</ErrorBanner>
          <label className="block text-sm text-muted">
            {t.topic}
            <select className={`${inputCls} mt-1`} value={topic} onChange={(e) => chooseTopic(e.target.value as Topic)}>
              {TOPICS.map((value) => (
                <option key={value} value={value}>{t.topics[value]}</option>
              ))}
            </select>
          </label>
          {deleting && <p className="text-sm text-body">{t.deleteHint}</p>}
          <label className="block text-sm text-muted">
            {t.titleLabel}
            <input className={`${inputCls} mt-1`} value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="block text-sm text-muted">
            {deleting ? t.request : t.description}
            <textarea className={`${inputCls} mt-1 min-h-32`} required value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          {!deleting && (
            <>
              <label className="block text-sm text-muted">
                {t.expected}
                <textarea className={`${inputCls} mt-1 min-h-20`} value={expected} onChange={(e) => setExpected(e.target.value)} />
              </label>
              <label className="block text-sm text-muted">
                {t.steps}
                <textarea className={`${inputCls} mt-1 min-h-20`} value={steps} onChange={(e) => setSteps(e.target.value)} />
              </label>
              <FileInput
                key={fileKey}
                label={t.screenshot}
                accept={SCREENSHOT_TYPES.join(',')}
                file={screenshot}
                onChange={pickFile}
                language={language}
              />
            </>
          )}
          <Button type="submit" disabled={!description.trim()} loading={sending} loadingLabel={t.sending}>
            {t.send}
          </Button>
          <p className="text-sm">
            <Link href="/report" className="text-muted hover:underline">
              {t.content}
            </Link>
          </p>
        </form>
      </ScrollArea>
    </Header>
  );
}

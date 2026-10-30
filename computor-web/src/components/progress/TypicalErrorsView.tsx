'use client';

import { Fragment, useState } from 'react';
import Link from 'next/link';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Button from '@/src/components/ui/Button';
import Panel from '@/src/components/ui/Panel';
import Notice from '@/src/components/ui/Notice';
import Toolbar from '@/src/components/ui/Toolbar';
import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import { Table, Thead, Tbody, Th, Td } from '@/src/components/ui/Table';
import { inputCls } from '@/src/components/ui/tokens';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { courseAnalyticsClient } from '@/src/clients/CourseAnalyticsClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime, formatNumber } from '@/src/utils/locale';
import { assignmentsOf } from '@/src/utils/courseAnalytics';
import { useCourseTitles } from '@/src/hooks/useCourseTitles';
import type { TypicalError } from 'types/generated';

const SCAN_SIZES = [300, 1000, 2000];

const COPY = {
  de: {
    title: 'Typische Fehler',
    subtitle: 'Fehlgeschlagene Tests über alle Studierenden, gruppiert nach Fehlermeldung',
    refresh: 'Aktualisieren',
    assignment: 'Aufgabe',
    wholeCourse: 'Ganzer Kurs',
    scan: 'Die neuesten durchsuchen',
    failingRuns: (n: string) => `${n} fehlgeschlagene Läufe`,
    errorGroups: 'Fehlergruppen',
    runsScanned: 'Durchsuchte Läufe',
    runsScannedHint: 'neueste Testläufe unter voller Punktzahl',
    largest: 'Größte Gruppe',
    largestHint: 'Studierende mit demselben Fehler',
    withoutReport: 'Läufe ohne Bericht',
    truncated: (n: string) =>
      `Es gibt mehr fehlgeschlagene Läufe, als durchsucht wurden. Einbezogen sind nur die neuesten ${n}. Wähle einen größeren Umfang oder eine einzelne Aufgabe, um weiter zurückzuschauen.`,
    noneTitle: 'Keine fehlgeschlagenen Tests gefunden.',
    noneText: 'Entweder waren alle durchsuchten Läufe erfolgreich, oder zu ihnen sind keine Testberichte gespeichert.',
    failingTest: 'Fehlgeschlagener Test',
    message: 'Meldung (normalisiert)',
    students: 'Studierende',
    runs: 'Läufe',
    lastSeen: 'Zuletzt gesehen',
    examples: 'Beispiele (neueste zuerst)',
    student: 'Studierende/r',
    howTitle: 'So werden Meldungen gruppiert',
  },
  en: {
    title: 'Typical errors',
    subtitle: 'Failing tests across students, grouped by error message',
    refresh: 'Refresh',
    assignment: 'Assignment',
    wholeCourse: 'Whole course',
    scan: 'Scan the newest',
    failingRuns: (n: string) => `${n} failing runs`,
    errorGroups: 'Error groups',
    runsScanned: 'Runs scanned',
    runsScannedHint: 'newest test runs below full score',
    largest: 'Largest group',
    largestHint: 'students sharing one error',
    withoutReport: 'Runs without report',
    truncated: (n: string) =>
      `More failing runs exist than were scanned. Only the newest ${n} are included; choose a larger scan or a single assignment to look further back.`,
    noneTitle: 'No failing tests found.',
    noneText: 'Either every scanned run passed, or no test reports are stored for them.',
    failingTest: 'Failing test',
    message: 'Message (normalized)',
    students: 'Students',
    runs: 'Runs',
    lastSeen: 'Last seen',
    examples: 'Examples (newest first)',
    student: 'Student',
    howTitle: 'How messages are grouped',
  },
};

/**
 * Typical errors: failing tests across students, grouped by a normalized
 * message so that "assert 3 == 4" and "assert 7 == 2" count as one problem.
 */
export default function TypicalErrorsView({ courseId }: { courseId: string }) {
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, t.title);
  const [contentId, setContentId] = useState('');
  const [maxResults, setMaxResults] = useState(SCAN_SIZES[0]);
  const [open, setOpen] = useState<string | null>(null);
  // Assignment options come from the course-wide scan and stay put while one is selected.
  const [assignments, setAssignments] = useState<{ id: string; title: string }[]>([]);

  const { data, loading, error, reload } = useResource(async () => {
    const res = await courseAnalyticsClient.typicalErrors(courseId, {
      courseContentId: contentId || null,
      maxResults,
    });
    if (!contentId) setAssignments(assignmentsOf(res.errors ?? []));
    return res;
  }, [courseId, contentId, maxResults]);

  const { contentTitle } = useCourseTitles(courseId);
  const errors = data?.errors ?? [];
  const keyOf = (e: TypicalError) => `${e.course_content_id}|${e.test_name}|${e.message}`;
  const largest = errors.reduce((m, e) => Math.max(m, e.affected_students), 0);

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={crumbs}
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <Button variant="secondary" onClick={() => reload()} disabled={loading}>
            {t.refresh}
          </Button>
        }
      />
      <ScrollArea>
        <ErrorBanner>{error}</ErrorBanner>

        <Panel padding="none">
          <Toolbar className="px-4 py-3">
            <label className="text-xs font-medium text-muted" htmlFor="te-assignment">{t.assignment}</label>
            <select
              id="te-assignment"
              className={`${inputCls} max-w-xs`}
              value={contentId}
              onChange={(e) => setContentId(e.target.value)}
            >
              <option value="">{t.wholeCourse}</option>
              {assignments.map((a) => (
                <option key={a.id} value={a.id}>{contentTitle(a.id, a.title)}</option>
              ))}
            </select>
            <label className="text-xs font-medium text-muted ml-4" htmlFor="te-scan">{t.scan}</label>
            <select
              id="te-scan"
              className={`${inputCls} max-w-xs`}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
            >
              {SCAN_SIZES.map((n) => (
                <option key={n} value={n}>{t.failingRuns(language === 'de' ? formatNumber(n, language) : String(n))}</option>
              ))}
            </select>
          </Toolbar>
        </Panel>

        {loading && <div className="h-64 bg-sunken rounded-lg animate-pulse" />}

        {!loading && data && (
          <>
            <StatGrid columns={4}>
              <StatCard label={t.errorGroups} value={errors.length} />
              <StatCard label={t.runsScanned} value={data.results_scanned} hint={t.runsScannedHint} />
              <StatCard label={t.largest} value={largest} hint={t.largestHint} />
              <StatCard
                label={t.withoutReport}
                value={data.results_without_report}
                tone={data.results_without_report ? 'warning' : 'muted'}
              />
            </StatGrid>

            {data.truncated && (
              <Notice tone="info">
                {t.truncated(String(data.results_scanned))}
              </Notice>
            )}

            {errors.length === 0 ? (
              <EmptyState
                compact
                title={t.noneTitle}
                description={t.noneText}
              />
            ) : (
              <Panel padding="none">
                <div className="overflow-x-auto">
                  <Table>
                    <Thead>
                      <tr>
                        <Th className="normal-case tracking-normal text-sm">{t.assignment}</Th>
                        <Th className="normal-case tracking-normal text-sm">{t.failingTest}</Th>
                        <Th className="normal-case tracking-normal text-sm">{t.message}</Th>
                        <Th className="normal-case tracking-normal text-sm text-right">{t.students}</Th>
                        <Th className="normal-case tracking-normal text-sm text-right">{t.runs}</Th>
                        <Th className="normal-case tracking-normal text-sm">{t.lastSeen}</Th>
                      </tr>
                    </Thead>
                    <Tbody>
                      {errors.map((e) => {
                        const k = keyOf(e);
                        const isOpen = open === k;
                        return (
                          <Fragment key={k}>
                            <tr
                              className="hover:bg-accent-wash/50 cursor-pointer align-top"
                              onClick={() => setOpen(isOpen ? null : k)}
                              aria-expanded={isOpen}
                            >
                              <Td className="py-2.5 text-body">{contentTitle(e.course_content_id, e.course_content_title || '—')}</Td>
                              <Td className="py-2.5 font-medium text-fg">{e.test_name}</Td>
                              <Td className="py-2.5 font-mono text-xs text-body break-all">{e.message}</Td>
                              <Td className="py-2.5 text-right tabular-nums font-medium">{e.affected_students}</Td>
                              <Td className="py-2.5 text-right tabular-nums">{e.occurrences}</Td>
                              <Td className="py-2.5 text-xs text-muted whitespace-nowrap">{formatDateTime(e.last_seen_at, language)}</Td>
                            </tr>
                            {isOpen && (
                              <tr>
                                <Td colSpan={6} className="bg-canvas py-3">
                                  <p className="text-xs font-medium text-muted mb-2">{t.examples}</p>
                                  <ul className="space-y-2">
                                    {(e.examples ?? []).map((x) => (
                                      <li key={x.result_id} className="text-sm">
                                        <Link
                                          className="font-medium text-accent-text hover:underline"
                                          href={`/courses/${courseId}/lecturer/grading/${x.course_member_id}`}
                                        >
                                          {x.student_name || t.student}
                                        </Link>
                                        <span className="ml-2 text-xs text-subtle">{formatDateTime(x.created_at, language)}</span>
                                        {x.message && (
                                          <pre className="mt-1 p-2 bg-surface border border-rule rounded text-xs whitespace-pre-wrap break-all max-h-40 overflow-auto">
                                            {x.message}
                                          </pre>
                                        )}
                                      </li>
                                    ))}
                                  </ul>
                                </Td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })}
                    </Tbody>
                  </Table>
                </div>
              </Panel>
            )}

            <details className="text-xs text-muted">
              <summary className="cursor-pointer select-none">{t.howTitle}</summary>
              <p className="mt-2">
                {language === 'de' ? (
                  <>
                    Jeder fehlgeschlagene Test eines gespeicherten Testberichts zählt einmal pro Lauf.
                    Meldungen werden auf ihre erste Fehlerzeile gekürzt; Zahlen werden zu &lt;n&gt;,
                    Werte in Anführungszeichen zu &lt;str&gt; (einfache Namen wie &apos;np&apos; bleiben
                    erhalten), Dateipfade zu &lt;path&gt; und Speicheradressen zu &lt;addr&gt;. Läufe
                    von Lehrenden und Tutoren sind nicht enthalten.
                  </>
                ) : (
                  <>
                    Each failing test of a stored test report counts once per run. Messages are reduced to
                    their first error line; numbers become &lt;n&gt;, quoted values &lt;str&gt; (plain names
                    such as &apos;np&apos; are kept), file paths &lt;path&gt; and memory addresses
                    &lt;addr&gt;. Runs by lecturers and tutors are not included.
                  </>
                )}
              </p>
            </details>
          </>
        )}
      </ScrollArea>
    </ListPageLayout>
  );
}

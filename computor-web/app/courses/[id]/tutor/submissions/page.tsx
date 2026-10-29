'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Panel from '@/src/components/ui/Panel';
import Toolbar from '@/src/components/ui/Toolbar';
import Badge from '@/src/components/Badge';
import { Table, Thead, Tbody, Th, Td } from '@/src/components/ui/Table';
import { inputCls } from '@/src/components/ui/tokens';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { contentTitles, tutorsClient } from '@/src/components/tutor/tutorData';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';

const COPY = {
  de: {
    tutor: 'Tutor',
    title: 'Abgaben',
    subtitle: 'Abgaben, die auf eine Prüfung warten',
    loading: 'Lädt …',
    groups: (n: number) => `${n} Abgabegruppen`,
    filter: 'Nach Aufgabe filtern',
    allAssignments: 'Alle Aufgaben',
    onlyUngraded: 'Nur unbewertete',
    nothingWaiting: 'Nichts wartet auf eine Prüfung.',
    noSubmissions: 'Noch keine Abgaben.',
    studentOrTeam: 'Studierende oder Team',
    assignment: 'Aufgabe',
    submissions: 'Abgaben',
    latest: 'Letzte Abgabe',
    state: 'Status',
    ungraded: 'Unbewertet',
    graded: 'Bewertet',
    noMembers: 'Diese Abgabegruppe hat keine Mitglieder.',
    openFailed: 'Die Abgabe konnte nicht geöffnet werden.',
  },
  en: {
    tutor: 'Tutor',
    title: 'Submissions',
    subtitle: 'Submissions waiting for a review',
    loading: 'Loading…',
    groups: (n: number) => `${n} submission groups`,
    filter: 'Filter by assignment',
    allAssignments: 'All assignments',
    onlyUngraded: 'Only ungraded',
    nothingWaiting: 'Nothing waiting for a review.',
    noSubmissions: 'No submissions yet.',
    studentOrTeam: 'Student or team',
    assignment: 'Assignment',
    submissions: 'Submissions',
    latest: 'Latest submission',
    state: 'State',
    ungraded: 'Ungraded',
    graded: 'Graded',
    noMembers: 'This submission group has no members.',
    openFailed: 'Could not open the submission',
  },
};

/** The review queue: submission groups with work, oldest waiting first. */
export default function TutorSubmissionsPage() {
  const courseId = useParams().id as string;
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, { label: t.tutor, href: `/courses/${courseId}/tutor` }, t.title);
  const [onlyUngraded, setOnlyUngraded] = useState(true);
  const [contentId, setContentId] = useState('');
  const [opening, setOpening] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  const titles = useResource(() => contentTitles(courseId, language), [courseId, language]);
  const { data, loading, error } = useResource(
    () =>
      tutorsClient.tutorListSubmissionGroupsEndpointTutorsSubmissionGroupsGet({
        courseId,
        courseContentId: contentId || null,
        hasSubmissions: true,
        hasUngradedSubmissions: onlyUngraded ? true : null,
        limit: 500,
      }),
    [courseId, contentId, onlyUngraded],
  );

  const rows = [...(data ?? [])].sort(
    (a, b) => Date.parse(a.latest_submission_at ?? '') - Date.parse(b.latest_submission_at ?? ''),
  );
  const titleOf = (id: string) => titles.data?.get(id) ?? t.assignment;
  const options = [...(titles.data?.entries() ?? [])].sort((a, b) => a[1].localeCompare(b[1]));

  async function open(groupId: string, courseContentId: string) {
    setOpening(groupId);
    setOpenError(null);
    try {
      const group = await tutorsClient.tutorGetSubmissionGroupEndpointTutorsSubmissionGroupsSubmissionGroupIdGet({
        submissionGroupId: groupId,
      });
      const member = group.members?.[0];
      if (!member) throw new Error(t.noMembers);
      router.push(`/courses/${courseId}/tutor/grading/${member.course_member_id}?content=${courseContentId}`);
    } catch (err) {
      setOpenError(err instanceof Error ? err.message : t.openFailed);
      setOpening(null);
    }
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={crumbs} title={t.title} subtitle={t.subtitle} />
        <ScrollArea>
          <ErrorBanner>{error || openError}</ErrorBanner>
          <Panel padding="none">
            <Toolbar className="px-4 py-3 border-b border-rule">
              <h3 className="text-sm font-semibold text-fg">{loading ? t.loading : t.groups(rows.length)}</h3>
              <select
                aria-label={t.filter}
                className={`${inputCls} max-w-xs ml-auto`}
                value={contentId}
                onChange={(e) => setContentId(e.target.value)}
              >
                <option value="">{t.allAssignments}</option>
                {options.map(([id, title]) => (
                  <option key={id} value={id}>{title}</option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-sm text-body">
                <input type="checkbox" checked={onlyUngraded} onChange={(e) => setOnlyUngraded(e.target.checked)} />
                {t.onlyUngraded}
              </label>
            </Toolbar>
            {loading ? (
              <div className="h-40 bg-sunken animate-pulse" />
            ) : rows.length === 0 ? (
              <div className="p-4">
                <EmptyState compact title={onlyUngraded ? t.nothingWaiting : t.noSubmissions} />
              </div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th className="normal-case tracking-normal text-sm">{t.studentOrTeam}</Th>
                    <Th className="normal-case tracking-normal text-sm">{t.assignment}</Th>
                    <Th className="normal-case tracking-normal text-sm text-right">{t.submissions}</Th>
                    <Th className="normal-case tracking-normal text-sm">{t.latest}</Th>
                    <Th className="normal-case tracking-normal text-sm">{t.state}</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {rows.map((g) => (
                    <tr
                      key={g.id}
                      className={`hover:bg-accent-wash/50 cursor-pointer ${opening === g.id ? 'opacity-60' : ''}`}
                      onClick={() => open(g.id, g.course_content_id)}
                    >
                      <Td className="py-2.5 font-medium text-fg">{g.display_name}</Td>
                      <Td className="py-2.5 text-body">{titleOf(g.course_content_id)}</Td>
                      <Td className="py-2.5 text-right tabular-nums">{g.submission_count}</Td>
                      <Td className="py-2.5 text-xs text-muted whitespace-nowrap">{formatDateTime(g.latest_submission_at, language)}</Td>
                      <Td className="py-2.5">
                        {g.has_ungraded_submissions ? <Badge tone="warning">{t.ungraded}</Badge> : <Badge tone="success">{t.graded}</Badge>}
                      </Td>
                    </tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </Panel>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

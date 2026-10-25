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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { listCourseStudents, memberName } from '@/src/components/tutor/tutorData';

const COPY = {
  de: {
    tutor: 'Tutor',
    title: 'Bewertung',
    subtitle: 'Wähle eine Person zum Prüfen und Bewerten aus',
    students: (n: number) => `Studierende (${n})`,
    onlyWaiting: 'Nur mit unbewerteten Abgaben',
    searchPlaceholder: 'Studierende suchen …',
    search: 'Studierende suchen',
    noMatch: 'Keine passenden Studierenden.',
    student: 'Studierende',
    ungraded: 'Unbewertete Abgaben',
    unread: 'Ungelesene Nachrichten',
  },
  en: {
    tutor: 'Tutor',
    title: 'Grading',
    subtitle: 'Choose a student to review and grade',
    students: (n: number) => `Students (${n})`,
    onlyWaiting: 'Only with ungraded submissions',
    searchPlaceholder: 'Search students…',
    search: 'Search students',
    noMatch: 'No students match.',
    student: 'Student',
    ungraded: 'Ungraded submissions',
    unread: 'Unread messages',
  },
};

/** Students of the course, with what is waiting for each; a row opens their grading page. */
export default function TutorGradingPage() {
  const courseId = useParams().id as string;
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, { label: t.tutor, href: `/courses/${courseId}/tutor` }, t.title);
  const [query, setQuery] = useState('');
  const [onlyWaiting, setOnlyWaiting] = useState(false);
  const { data, loading, error } = useResource(() => listCourseStudents(courseId), [courseId]);

  const rows = (data ?? []).filter((s) => {
    if (onlyWaiting && !(s.ungraded_submissions_count ?? 0)) return false;
    if (!query) return true;
    const q = query.toLowerCase();
    return memberName(s, language).toLowerCase().includes(q) || (s.user?.email ?? '').toLowerCase().includes(q);
  });

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={crumbs} title={t.title} subtitle={t.subtitle} />
        <ScrollArea>
          <ErrorBanner>{error}</ErrorBanner>
          <Panel padding="none">
            <Toolbar className="px-4 py-3 border-b border-rule">
              <h3 className="text-sm font-semibold text-fg">{t.students(rows.length)}</h3>
              <label className="ml-auto flex items-center gap-2 text-sm text-body">
                <input type="checkbox" checked={onlyWaiting} onChange={(e) => setOnlyWaiting(e.target.checked)} />
                {t.onlyWaiting}
              </label>
              <input
                className={`${inputCls} max-w-xs`}
                placeholder={t.searchPlaceholder}
                aria-label={t.search}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </Toolbar>
            {loading ? (
              <div className="h-40 bg-sunken animate-pulse" />
            ) : rows.length === 0 ? (
              <div className="p-4"><EmptyState compact title={t.noMatch} /></div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th className="normal-case tracking-normal text-sm">{t.student}</Th>
                    <Th className="normal-case tracking-normal text-sm">{t.ungraded}</Th>
                    <Th className="normal-case tracking-normal text-sm">{t.unread}</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {rows.map((s) => (
                    <tr
                      key={s.id}
                      className="hover:bg-accent-wash/50 cursor-pointer"
                      onClick={() => router.push(`/courses/${courseId}/tutor/grading/${s.id}`)}
                    >
                      <Td className="py-2.5">
                        <span className="font-medium text-fg">{memberName(s, language)}</span>
                        {s.user?.email && <span className="ml-2 text-xs text-subtle">{s.user.email}</span>}
                      </Td>
                      <Td className="py-2.5">
                        {(s.ungraded_submissions_count ?? 0) > 0 ? (
                          <Badge tone="warning">{s.ungraded_submissions_count}</Badge>
                        ) : (
                          <span className="text-xs text-subtle">—</span>
                        )}
                      </Td>
                      <Td className="py-2.5 text-sm text-muted">{s.unread_message_count || '—'}</Td>
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

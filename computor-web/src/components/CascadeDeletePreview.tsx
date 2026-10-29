'use client';

import DescriptionList from './DescriptionList';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatNumber } from '@/src/utils/locale';
import type { CascadeDeleteResult, EntityDeleteCount } from 'types/generated';

/**
 * What a cascade delete will take with it, from the backend's dry run.
 *
 * Shown inside ConfirmDeleteDialog above the type-to-confirm input, so the
 * reader sees the blast radius before they type the name. Only non-zero
 * counts are listed; "Submissions from students" leads because it is the one
 * figure that decides whether the delete is allowed at all.
 *
 * For a course it also says what happens on the git server, in both
 * directions: the template and reference repositories go, the students'
 * repositories are kept. That second line is deliberate — a lecturer deleting
 * a course must not believe they are wiping student work, and must not
 * believe the server is being cleaned up either.
 */
const COUNT_KEYS: (keyof EntityDeleteCount)[] = [
  'student_submissions', 'courses', 'course_families', 'course_members', 'course_groups',
  'course_content_types', 'course_contents', 'submission_groups', 'submission_group_members',
  'submission_artifacts', 'submission_grades', 'submission_reviews', 'results', 'result_artifacts',
  'course_content_deployments', 'deployment_histories', 'course_member_comments', 'messages',
  'example_repositories', 'examples', 'example_versions', 'example_dependencies', 'student_profiles',
];

const COPY = {
  de: {
    labels: {
      student_submissions: 'Abgaben von Studierenden',
      courses: 'Kurse',
      course_families: 'Kursfamilien',
      course_members: 'Kursmitglieder',
      course_groups: 'Kursgruppen',
      course_content_types: 'Inhaltstypen',
      course_contents: 'Aufgaben und Einheiten',
      submission_groups: 'Abgabegruppen',
      submission_group_members: 'Mitglieder von Abgabegruppen',
      submission_artifacts: 'Abgaben (aller Einreichenden)',
      submission_grades: 'Bewertungen',
      submission_reviews: 'Reviews',
      results: 'Testergebnisse',
      result_artifacts: 'Dateien zu Testergebnissen',
      course_content_deployments: 'Bereitstellungen',
      deployment_histories: 'Einträge im Bereitstellungsverlauf',
      course_member_comments: 'Kommentare zu Mitgliedern',
      messages: 'Nachrichten',
      example_repositories: 'Beispiel-Repositories',
      examples: 'Beispiele',
      example_versions: 'Beispielversionen',
      example_dependencies: 'Beispielabhängigkeiten',
      student_profiles: 'Studierendenprofile',
    } as Partial<Record<keyof EntityDeleteCount, string>>,
    alsoDeletes: 'Damit wird auch gelöscht',
    nothingElse: 'Daran hängt nichts weiter.',
    repositories: 'Git-Repositories, die gelöscht werden',
    kept: (n: string) => `Die Repositories der Studierenden bleiben erhalten (${n}).`,
  },
  en: {
    labels: {
      student_submissions: 'Submissions from students',
      courses: 'Courses',
      course_families: 'Course families',
      course_members: 'Course members',
      course_groups: 'Course groups',
      course_content_types: 'Content types',
      course_contents: 'Assignments and units',
      submission_groups: 'Submission groups',
      submission_group_members: 'Submission group members',
      submission_artifacts: 'Submissions (all uploaders)',
      submission_grades: 'Grades',
      submission_reviews: 'Reviews',
      results: 'Test results',
      result_artifacts: 'Test result files',
      course_content_deployments: 'Deployments',
      deployment_histories: 'Deployment history entries',
      course_member_comments: 'Member comments',
      messages: 'Messages',
      example_repositories: 'Example repositories',
      examples: 'Examples',
      example_versions: 'Example versions',
      example_dependencies: 'Example dependencies',
      student_profiles: 'Student profiles',
    } as Partial<Record<keyof EntityDeleteCount, string>>,
    alsoDeletes: 'This will also delete',
    nothingElse: 'Nothing else is attached to it.',
    repositories: 'Git repositories that will be deleted',
    kept: (n: string) => `Student repositories are kept (${n}).`,
  },
};

export default function CascadeDeletePreview({ result }: { result: CascadeDeleteResult }) {
  const language = useUiLanguage();
  const t = COPY[language];
  const counts = result.deleted_counts ?? {};
  const items = COUNT_KEYS.flatMap((key) => {
    const n = counts[key] ?? 0;
    return n > 0 ? [{ term: t.labels[key] ?? key, value: formatNumber(n, language) }] : [];
  });
  const repos = result.git_repositories ?? [];
  const isCourse = result.entity_type === 'course';

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs font-medium text-body mb-1">{t.alsoDeletes}</p>
        {items.length > 0 ? (
          <DescriptionList items={items} />
        ) : (
          <p className="text-sm text-muted">{t.nothingElse}</p>
        )}
      </div>
      {repos.length > 0 && (
        <div>
          <p className="text-xs font-medium text-body mb-1">{t.repositories}</p>
          <ul className="text-xs font-mono text-fg space-y-0.5">
            {repos.map((r) => (
              <li key={r} className="break-all">{r}</li>
            ))}
          </ul>
        </div>
      )}
      {isCourse && (
        <p className="text-sm text-muted">
          {t.kept(formatNumber(result.student_repositories_kept ?? 0, language))}
        </p>
      )}
    </div>
  );
}

'use client';

import DescriptionList from './DescriptionList';
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
const COUNT_LABELS: [keyof EntityDeleteCount, string][] = [
  ['student_submissions', 'Submissions from students'],
  ['courses', 'Courses'],
  ['course_families', 'Course families'],
  ['course_members', 'Course members'],
  ['course_groups', 'Course groups'],
  ['course_content_types', 'Content types'],
  ['course_contents', 'Assignments and units'],
  ['submission_groups', 'Submission groups'],
  ['submission_group_members', 'Submission group members'],
  ['submission_artifacts', 'Submissions (all uploaders)'],
  ['submission_grades', 'Grades'],
  ['submission_reviews', 'Reviews'],
  ['results', 'Test results'],
  ['result_artifacts', 'Test result files'],
  ['course_content_deployments', 'Deployments'],
  ['deployment_histories', 'Deployment history entries'],
  ['course_member_comments', 'Member comments'],
  ['messages', 'Messages'],
  ['example_repositories', 'Example repositories'],
  ['examples', 'Examples'],
  ['example_versions', 'Example versions'],
  ['example_dependencies', 'Example dependencies'],
  ['student_profiles', 'Student profiles'],
];

export default function CascadeDeletePreview({ result }: { result: CascadeDeleteResult }) {
  const counts = result.deleted_counts ?? {};
  const items = COUNT_LABELS.flatMap(([key, label]) => {
    const n = counts[key] ?? 0;
    return n > 0 ? [{ term: label, value: n.toLocaleString() }] : [];
  });
  const repos = result.git_repositories ?? [];
  const isCourse = result.entity_type === 'course';

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs font-medium text-body mb-1">This will also delete</p>
        {items.length > 0 ? (
          <DescriptionList items={items} />
        ) : (
          <p className="text-sm text-muted">Nothing else is attached to it.</p>
        )}
      </div>
      {repos.length > 0 && (
        <div>
          <p className="text-xs font-medium text-body mb-1">Git repositories that will be deleted</p>
          <ul className="text-xs font-mono text-fg space-y-0.5">
            {repos.map((r) => (
              <li key={r} className="break-all">{r}</li>
            ))}
          </ul>
        </div>
      )}
      {isCourse && (
        <p className="text-sm text-muted">
          Student repositories are kept ({(result.student_repositories_kept ?? 0).toLocaleString()}).
        </p>
      )}
    </div>
  );
}

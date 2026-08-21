'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import VisibilitySelect, { type VisibilityValue } from '@/src/components/courses/VisibilitySelect';
import { CourseContentsClient } from '@/src/generated/clients/CourseContentsClient';

const contentsClient = new CourseContentsClient();

/** Blank (or unparseable) means "inherit from the course", i.e. no own limit. */
const parseLimit = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
};

/**
 * Edit one unit or assignment.
 *
 * The only editing surface for a CourseContent in the web app: contents are
 * created through the deployment-file upload, never through a create form, so
 * there is no sibling /create route. `path` is deliberately absent -- moving a
 * content goes through PATCH /course-contents/{id}/move so its descendants
 * move with it, and the backend rejects a path written here.
 */
export default function CourseContentEditPage() {
  const params = useParams();
  const courseId = params.id as string;
  const contentId = params.contentId as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [title, setTitle] = useState('');
  const crumbs = useCourseCrumbs(courseId, { label: 'Assignments', href: `/courses/${courseId}/lecturer/assignments` }, title || 'Content');
  const [description, setDescription] = useState('');
  const [position, setPosition] = useState('');
  const [maxGroupSize, setMaxGroupSize] = useState('');
  const [maxTestRuns, setMaxTestRuns] = useState('');
  const [maxSubmissions, setMaxSubmissions] = useState('');
  const [visible, setVisible] = useState<VisibilityValue>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: content, loading, error: loadError } = useResource(
    () => contentsClient.getCourseContentsCourseContentsIdGet({ id: contentId }),
    [contentId],
    { enabled: canManage },
  );

  // Seed the form once the content loads. Adjusting state during render rather
  // than in an effect matches the sibling edit pages.
  const [seeded, setSeeded] = useState(content);
  if (content && content !== seeded) {
    setSeeded(content);
    setTitle(content.title || '');
    setDescription(content.description || '');
    setPosition(content.position != null ? String(content.position) : '');
    setMaxGroupSize(content.max_group_size != null ? String(content.max_group_size) : '');
    setMaxTestRuns(content.max_test_runs != null ? String(content.max_test_runs) : '');
    setMaxSubmissions(content.max_submissions != null ? String(content.max_submissions) : '');
    setVisible(content.visible ?? null);
  }

  const backHref = `/courses/${courseId}/lecturer/assignments`;

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      const parsedPosition = Number(position.trim());
      await contentsClient.updateCourseContentsCourseContentsIdPatch({
        id: contentId,
        body: {
          title: title.trim() || null,
          description: description.trim() || null,
          position: Number.isFinite(parsedPosition) ? parsedPosition : null,
          max_group_size: parseLimit(maxGroupSize),
          max_test_runs: parseLimit(maxTestRuns),
          max_submissions: parseLimit(maxSubmissions),
          visible,
        },
      });
      router.push(backHref);
    } catch (e) {
      setSaving(false);
      setSaveError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden message="You need lecturer access (or higher) on this course to edit its content." />
    );
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <PageLoading />
      ) : (
        <FormPanel
          breadcrumbs={crumbs}
          title={`Edit ${title || 'content'}`}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(backHref)}
          onSubmit={save}
        >
          <Field label="Title">
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className={inputCls}
            />
          </Field>

          <Field
            label="Student visibility"
            hint="Hiding a unit hides every assignment under it. Students keep their files and their existing tests and submissions either way."
          >
            <VisibilitySelect
              scope="content"
              value={visible}
              onChange={setVisible}
              effective={content?.visible_effective}
            />
          </Field>

          <Field label="Path (immutable here)" hint="Moving content is a separate action, so its descendants move with it.">
            <input value={content?.path || ''} readOnly className={inputCls} />
          </Field>

          <Field label="Position" hint="Orders this content among its siblings.">
            <input
              inputMode="decimal"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className={inputCls}
            />
          </Field>

          <Field label="Max group size" hint="Empty = the course default.">
            <input
              inputMode="numeric"
              value={maxGroupSize}
              onChange={(e) => setMaxGroupSize(e.target.value)}
              placeholder="course default"
              className={inputCls}
            />
          </Field>

          <Field label="Max test runs" hint="Empty = inherit the course-wide default.">
            <input
              inputMode="numeric"
              value={maxTestRuns}
              onChange={(e) => setMaxTestRuns(e.target.value)}
              placeholder="inherit"
              className={inputCls}
            />
          </Field>

          <Field label="Max submissions" hint="Empty = inherit the course-wide default.">
            <input
              inputMode="numeric"
              value={maxSubmissions}
              onChange={(e) => setMaxSubmissions(e.target.value)}
              placeholder="inherit"
              className={inputCls}
            />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}

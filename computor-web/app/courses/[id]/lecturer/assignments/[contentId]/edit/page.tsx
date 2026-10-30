'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import VisibilitySelect, { type VisibilityValue } from '@/src/components/courses/VisibilitySelect';
import LenaDescriptionDraft from '@/src/components/courses/LenaDescriptionDraft';
import LunaAnswer from '@/src/components/student/LunaAnswer';
import { CourseContentsClient } from '@/src/generated/clients/CourseContentsClient';

const contentsClient = new CourseContentsClient();

const COPY = {
  de: {
    assignments: 'Aufgaben',
    content: 'Inhalt',
    contentLower: 'Inhalt',
    saveFailed: 'Speichern fehlgeschlagen',
    forbidden: 'Zum Bearbeiten dieses Inhalts brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    edit: (name: string) => `${name} bearbeiten`,
    title: 'Titel',
    description: 'Beschreibung',
    preview: 'Vorschau',
    visibility: 'Sichtbarkeit für Studierende',
    visibilityHint: 'Wenn du eine Einheit verbirgst, verbirgst du alle Aufgaben darunter. Studierende behalten in beiden Fällen ihre Dateien sowie ihre bisherigen Tests und Abgaben.',
    path: 'Pfad (hier nicht änderbar)',
    pathHint: 'Das Verschieben von Inhalten ist eine eigene Aktion, damit die untergeordneten Inhalte mitwandern.',
    position: 'Position',
    positionHint: 'Legt die Reihenfolge unter den Inhalten derselben Ebene fest.',
    maxGroupSize: 'Maximale Gruppengröße',
    maxGroupSizeHint: 'Leer = Kurs-Standard.',
    courseDefault: 'Kurs-Standard',
    maxTestRuns: 'Maximale Testläufe',
    maxSubmissions: 'Maximale Abgaben',
    inheritHint: 'Leer = kursweiten Standard übernehmen.',
    inherit: 'übernehmen',
  },
  en: {
    assignments: 'Assignments',
    content: 'Content',
    contentLower: 'content',
    saveFailed: 'Save failed',
    forbidden: 'You need lecturer access (or higher) on this course to edit its content.',
    edit: (name: string) => `Edit ${name}`,
    title: 'Title',
    description: 'Description',
    preview: 'Preview',
    visibility: 'Student visibility',
    visibilityHint: 'Hiding a unit hides every assignment under it. Students keep their files and their existing tests and submissions either way.',
    path: 'Path (immutable here)',
    pathHint: 'Moving content is a separate action, so its descendants move with it.',
    position: 'Position',
    positionHint: 'Orders this content among its siblings.',
    maxGroupSize: 'Max group size',
    maxGroupSizeHint: 'Empty = the course default.',
    courseDefault: 'course default',
    maxTestRuns: 'Max test runs',
    maxSubmissions: 'Max submissions',
    inheritHint: 'Empty = inherit the course-wide default.',
    inherit: 'inherit',
  },
};

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
  const t = COPY[useUiLanguage()];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [title, setTitle] = useState('');
  const crumbs = useCourseCrumbs(courseId, { label: t.assignments, href: `/courses/${courseId}/lecturer/assignments` }, title || t.content);
  const [description, setDescription] = useState('');
  // Set once a Lena draft is in the field: a draft is long markdown, so the
  // field grows and shows it rendered until it is saved or discarded.
  const [fromDraft, setFromDraft] = useState(false);
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
      setSaveError(e instanceof Error ? e.message : t.saveFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden message={t.forbidden} />
    );
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <PageLoading />
      ) : (
        <FormPanel
          breadcrumbs={crumbs}
          title={t.edit(title || t.contentLower)}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(backHref)}
          onSubmit={save}
        >
          <Field label={t.title}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label={t.description}>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={fromDraft ? 14 : 3}
              className={inputCls}
            />
          </Field>
          {/* Outside the Field: it labels only a single child control. */}
          {fromDraft && description.trim() && (
            <div className="mt-2 rounded-lg border border-rule bg-canvas p-3">
              <div className="mb-1 text-xs font-medium text-muted">{t.preview}</div>
              <LunaAnswer answer={description} />
            </div>
          )}
          {content && !content.is_submittable && (
            <LenaDescriptionDraft
              contentId={contentId}
              hasDescription={!!description.trim()}
              onUse={(draft) => {
                setDescription(draft);
                setFromDraft(true);
              }}
            />
          )}

          <Field
            label={t.visibility}
            hint={t.visibilityHint}
          >
            <VisibilitySelect
              scope="content"
              value={visible}
              onChange={setVisible}
              effective={content?.visible_effective}
            />
          </Field>

          <Field label={t.path} hint={t.pathHint}>
            <input value={content?.path || ''} readOnly className={inputCls} />
          </Field>

          <Field label={t.position} hint={t.positionHint}>
            <input
              inputMode="decimal"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className={inputCls}
            />
          </Field>

          <Field label={t.maxGroupSize} hint={t.maxGroupSizeHint}>
            <input
              inputMode="numeric"
              value={maxGroupSize}
              onChange={(e) => setMaxGroupSize(e.target.value)}
              placeholder={t.courseDefault}
              className={inputCls}
            />
          </Field>

          <Field label={t.maxTestRuns} hint={t.inheritHint}>
            <input
              inputMode="numeric"
              value={maxTestRuns}
              onChange={(e) => setMaxTestRuns(e.target.value)}
              placeholder={t.inherit}
              className={inputCls}
            />
          </Field>

          <Field label={t.maxSubmissions} hint={t.inheritHint}>
            <input
              inputMode="numeric"
              value={maxSubmissions}
              onChange={(e) => setMaxSubmissions(e.target.value)}
              placeholder={t.inherit}
              className={inputCls}
            />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}

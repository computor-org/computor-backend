'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { CourseFamilyList } from '@/src/generated/types/courses';
import type { GitServerGet } from '@/src/generated/types/common';

const ALL_MODES = ['forgejo', 'gitlab_byo', 'download'];

function CreateInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, canCreateCourse } = usePermissions();
  const canConfigureGit = isAdmin || isOrganizationManager; // listing git servers is registry-admin only

  const [families, setFamilies] = useState<CourseFamilyList[]>([]);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [familyId, setFamilyId] = useState(params.get('familyId') || '');
  const [path, setPath] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [gitEnabled, setGitEnabled] = useState(true);
  const [serverId, setServerId] = useState('');
  const [modes, setModes] = useState<string[]>(['forgejo']);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    (async () => {
      const reqs = [apiFetch(`${API_BASE_URL}/course-families`)];
      if (canConfigureGit) reqs.push(apiFetch(`${API_BASE_URL}/git-servers`));
      const [fRes, sRes] = await Promise.all(reqs);
      if (fRes.ok) {
        const all: CourseFamilyList[] = await fRes.json();
        const creatable = all.filter((f) => canCreateCourse(f.organization_id, f.id));
        setFamilies(creatable);
        if (!familyId && creatable.length === 1) setFamilyId(creatable[0].id);
      }
      if (sRes && sRes.ok) {
        const srv: GitServerGet[] = await sRes.json();
        setServers(srv);
        const def = srv.find((s) => s.type === 'forgejo' && s.managed)?.id ?? srv[0]?.id ?? '';
        setServerId(def);
        setGitEnabled(!!def);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated, canConfigureGit]);

  const mayCreate = useMemo(() => canCreateCourse(), [canCreateCourse]);
  const toggleMode = (m: string) => setModes((ms) => (ms.includes(m) ? ms.filter((x) => x !== m) : [...ms, m]));

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/courses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: path.trim(),
          course_family_id: familyId,
          title: title.trim() || null,
          description: description.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      const course = await res.json();
      // One step: configure git immediately so a course is never left without it.
      if (canConfigureGit && gitEnabled && serverId) {
        const gres = await apiFetch(`${API_BASE_URL}/courses/${course.id}/git`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ delivery: 'git', git_server_id: serverId, student_repo_modes: modes }),
        });
        if (!gres.ok) throw new Error('Course created, but git setup failed: ' + ((await gres.text()) || gres.status));
      }
      router.push(`/courses/${course.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !mayCreate) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have permission to create courses." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Courses', href: '/courses' }, { label: 'New' }]}
        title="New Course"
        error={error}
        submitting={saving}
        disabled={!path.trim() || !familyId}
        submitLabel="Create"
        onCancel={() => router.push('/courses')}
        onSubmit={save}
      >
        <Field label="Course family" required>
          <select value={familyId} onChange={(e) => setFamilyId(e.target.value)} className={inputCls}>
            <option value="">Select a course family…</option>
            {families.map((f) => (
              <option key={f.id} value={f.id}>{f.title || f.path}</option>
            ))}
          </select>
        </Field>
        <Field label="Path (slug)" required>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="algorithms" className={inputCls} />
        </Field>
        <Field label="Title">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Algorithms" className={inputCls} />
        </Field>
        <Field label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>

        {canConfigureGit && servers.length > 0 && (
          <div className="border-t border-gray-200 pt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input type="checkbox" checked={gitEnabled} onChange={(e) => setGitEnabled(e.target.checked)} />
              Set up git now
            </label>
            {gitEnabled && (
              <>
                <Field label="Git server">
                  <select value={serverId} onChange={(e) => setServerId(e.target.value)} className={inputCls}>
                    {servers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name || s.base_url} ({s.type})</option>
                    ))}
                  </select>
                </Field>
                <Field label="Student-repo modes">
                  <div className="flex flex-wrap gap-3">
                    {ALL_MODES.map((m) => (
                      <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700">
                        <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                        {m}
                      </label>
                    ))}
                  </div>
                </Field>
                <p className="text-xs text-gray-400">For a managed Forgejo the student-template repo is created automatically.</p>
              </>
            )}
          </div>
        )}
      </FormPanel>
    </AuthenticatedLayout>
  );
}

export default function CourseCreatePage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><div className="p-6 text-gray-500">Loading…</div></AuthenticatedLayout>}>
      <CreateInner />
    </Suspense>
  );
}

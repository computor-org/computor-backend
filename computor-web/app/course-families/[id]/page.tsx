'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import CourseGitSettingsModal from '@/src/components/CourseGitSettingsModal';
import type { CourseFamilyGet, CourseList } from '@/src/generated/types/courses';
import type { GitServerGet } from '@/src/generated/types/common';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';
const ALL_MODES = ['forgejo', 'gitlab_byo', 'download'];

interface CreateState {
  open: boolean;
  saving: boolean;
  error: string | null;
  path: string;
  title: string;
  description: string;
  gitEnabled: boolean;
  serverId: string;
  modes: string[];
}
const emptyCreate: CreateState = {
  open: false,
  saving: false,
  error: null,
  path: '',
  title: '',
  description: '',
  gitEnabled: true,
  serverId: '',
  modes: ['forgejo'],
};

export default function CourseFamilyDetailPage() {
  const familyId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, canCreateCourse } = usePermissions();
  const canConfigureGit = isAdmin || isOrganizationManager; // listing git servers is registry-admin only

  const [family, setFamily] = useState<CourseFamilyGet | null>(null);
  const [courses, setCourses] = useState<CourseList[]>([]);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [create, setCreate] = useState<CreateState>(emptyCreate);
  const [gitModal, setGitModal] = useState<{ courseId: string; courseLabel: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const reqs = [
        apiFetch(`${API_BASE_URL}/course-families/${familyId}`),
        apiFetch(`${API_BASE_URL}/courses?course_family_id=${familyId}`),
      ];
      if (canConfigureGit) reqs.push(apiFetch(`${API_BASE_URL}/git-servers`));
      const [famRes, courseRes, srvRes] = await Promise.all(reqs);
      if (!famRes.ok) throw new Error('Failed to load course family');
      setFamily(await famRes.json());
      if (courseRes.ok) setCourses(await courseRes.json());
      if (srvRes && srvRes.ok) setServers(await srvRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [familyId, canConfigureGit]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  // Prefer the managed Forgejo as the default git server for new courses.
  const defaultServerId = servers.find((s) => s.type === 'forgejo' && s.managed)?.id ?? servers[0]?.id ?? '';

  function openCreate() {
    setCreate({ ...emptyCreate, open: true, serverId: defaultServerId, gitEnabled: !!defaultServerId });
  }

  const toggleCreateMode = (m: string) =>
    setCreate((c) => ({ ...c, modes: c.modes.includes(m) ? c.modes.filter((x) => x !== m) : [...c.modes, m] }));

  async function handleCreateCourse() {
    setCreate((c) => ({ ...c, saving: true, error: null }));
    try {
      const res = await apiFetch(`${API_BASE_URL}/courses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: create.path.trim(),
          course_family_id: familyId,
          title: create.title.trim() || null,
          description: create.description.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      const course = await res.json();
      // One rush: configure git immediately so the course isn't left without it.
      if (create.gitEnabled && create.serverId) {
        const gres = await apiFetch(`${API_BASE_URL}/courses/${course.id}/git`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ delivery: 'git', git_server_id: create.serverId, student_repo_modes: create.modes }),
        });
        if (!gres.ok) {
          throw new Error('Course created, but git setup failed: ' + ((await gres.text()) || gres.status));
        }
      }
      setCreate(emptyCreate);
      await load();
    } catch (e) {
      setCreate((c) => ({ ...c, saving: false, error: e instanceof Error ? e.message : 'Create failed' }));
    }
  }

  const mayCreateCourse = family ? canCreateCourse(family.organization_id, familyId) : false;

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Link href="/course-families" className="text-sm text-blue-600 hover:underline">
          ← Course Families
        </Link>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{family?.title || family?.path || 'Course Family'}</h1>
            {family && <p className="mt-2 text-gray-600">{family.path}</p>}
          </div>
          {mayCreateCourse && (
            <button onClick={openCreate} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              New Course
            </button>
          )}
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        <h2 className="text-xl font-semibold text-gray-900">
          Courses {!loading && <span className="text-gray-400 font-normal">({courses.length})</span>}
        </h2>
        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : courses.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No courses in this family yet.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {courses.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-4 py-3">
                <Link href={`/courses/${c.id}`} className="min-w-0 group">
                  <div className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-600">
                    {c.title || c.path}
                  </div>
                  <div className="text-xs text-gray-500">{c.path}</div>
                </Link>
                {canConfigureGit && (
                  <button
                    onClick={() => setGitModal({ courseId: c.id, courseLabel: c.title || c.path })}
                    className="text-sm text-blue-600 hover:underline ml-4 whitespace-nowrap"
                  >
                    Git settings
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create course (with git, in one step) */}
      {create.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">New Course</h2>
              {create.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{create.error}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Path (slug) <span className="text-red-500">*</span>
                </label>
                <input value={create.path} onChange={(e) => setCreate((c) => ({ ...c, path: e.target.value }))} placeholder="algorithms" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title</label>
                <input value={create.title} onChange={(e) => setCreate((c) => ({ ...c, title: e.target.value }))} placeholder="Algorithms" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={create.description} onChange={(e) => setCreate((c) => ({ ...c, description: e.target.value }))} rows={2} className={inputCls} />
              </div>

              {canConfigureGit && servers.length > 0 && (
                <div className="border-t border-gray-200 pt-3 space-y-3">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input type="checkbox" checked={create.gitEnabled} onChange={(e) => setCreate((c) => ({ ...c, gitEnabled: e.target.checked }))} />
                    Set up git now
                  </label>
                  {create.gitEnabled && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Git server</label>
                        <select value={create.serverId} onChange={(e) => setCreate((c) => ({ ...c, serverId: e.target.value }))} className={inputCls}>
                          {servers.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name || s.base_url} ({s.type})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Student-repo modes</label>
                        <div className="flex flex-wrap gap-3">
                          {ALL_MODES.map((m) => (
                            <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700">
                              <input type="checkbox" checked={create.modes.includes(m)} onChange={() => toggleCreateMode(m)} />
                              {m}
                            </label>
                          ))}
                        </div>
                      </div>
                      <p className="text-xs text-gray-400">For a managed Forgejo the student-template repo is created automatically.</p>
                    </>
                  )}
                </div>
              )}
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button onClick={() => setCreate(emptyCreate)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Cancel
              </button>
              <button
                onClick={handleCreateCourse}
                disabled={create.saving || !create.path.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {create.saving ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {gitModal && (
        <CourseGitSettingsModal
          courseId={gitModal.courseId}
          courseLabel={gitModal.courseLabel}
          onClose={() => setGitModal(null)}
          onSaved={load}
        />
      )}
    </AuthenticatedLayout>
  );
}

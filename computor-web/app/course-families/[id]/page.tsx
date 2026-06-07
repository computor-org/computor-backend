'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseFamilyGet, CourseList } from '@/src/generated/types/courses';
import type { GitServerGet } from '@/src/generated/types/common';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';
const ALL_MODES = ['forgejo', 'gitlab_byo', 'download'];

interface CourseCreateState {
  open: boolean;
  saving: boolean;
  error: string | null;
  path: string;
  title: string;
  description: string;
}
const emptyCourse: CourseCreateState = { open: false, saving: false, error: null, path: '', title: '', description: '' };

interface GitState {
  open: boolean;
  courseId: string;
  courseLabel: string;
  loading: boolean;
  saving: boolean;
  error: string | null;
  delivery: 'git' | 'download';
  git_server_id: string;
  template_repo: string;
  template_url: string;
  default_branch: string;
  modes: string[];
}
const emptyGit: GitState = {
  open: false,
  courseId: '',
  courseLabel: '',
  loading: false,
  saving: false,
  error: null,
  delivery: 'git',
  git_server_id: '',
  template_repo: '',
  template_url: '',
  default_branch: 'main',
  modes: [],
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
  const [course, setCourse] = useState<CourseCreateState>(emptyCourse);
  const [git, setGit] = useState<GitState>(emptyGit);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [famRes, courseRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/course-families/${familyId}`),
        apiFetch(`${API_BASE_URL}/courses?course_family_id=${familyId}`),
      ]);
      if (!famRes.ok) throw new Error('Failed to load course family');
      setFamily(await famRes.json());
      if (courseRes.ok) setCourses(await courseRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [familyId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  async function handleCreateCourse() {
    setCourse((c) => ({ ...c, saving: true, error: null }));
    try {
      const res = await apiFetch(`${API_BASE_URL}/courses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: course.path.trim(),
          course_family_id: familyId,
          title: course.title.trim() || null,
          description: course.description.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      setCourse(emptyCourse);
      await load();
    } catch (e) {
      setCourse((c) => ({ ...c, saving: false, error: e instanceof Error ? e.message : 'Create failed' }));
    }
  }

  async function openGit(c: CourseList) {
    setGit({ ...emptyGit, open: true, loading: true, courseId: c.id, courseLabel: c.title || c.path });
    try {
      const [bindingRes, serverRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/courses/${c.id}/git`),
        apiFetch(`${API_BASE_URL}/git-servers`),
      ]);
      if (serverRes.ok) setServers(await serverRes.json());
      if (bindingRes.ok) {
        const b = await bindingRes.json();
        setGit((g) => ({
          ...g,
          loading: false,
          delivery: (b.delivery as 'git' | 'download') || 'git',
          git_server_id: b.git_server_id || '',
          template_repo: b.template_repo || '',
          template_url: b.template_url || '',
          default_branch: b.default_branch || 'main',
          modes: b.student_repo_modes || [],
        }));
      } else {
        // 404 = no binding yet; keep defaults.
        setGit((g) => ({ ...g, loading: false }));
      }
    } catch (e) {
      setGit((g) => ({ ...g, loading: false, error: e instanceof Error ? e.message : 'Failed to load git settings' }));
    }
  }

  async function handleSaveGit() {
    setGit((g) => ({ ...g, saving: true, error: null }));
    try {
      const res = await apiFetch(`${API_BASE_URL}/courses/${git.courseId}/git`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delivery: git.delivery,
          git_server_id: git.git_server_id || null,
          template_repo: git.template_repo.trim() || null,
          template_url: git.template_url.trim() || null,
          default_branch: git.default_branch.trim() || 'main',
          student_repo_modes: git.modes,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Save failed (${res.status})`);
      setGit(emptyGit);
    } catch (e) {
      setGit((g) => ({ ...g, saving: false, error: e instanceof Error ? e.message : 'Save failed' }));
    }
  }

  const toggleMode = (m: string) =>
    setGit((g) => ({ ...g, modes: g.modes.includes(m) ? g.modes.filter((x) => x !== m) : [...g.modes, m] }));

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
            <button
              onClick={() => setCourse({ ...emptyCourse, open: true })}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              New Course
            </button>
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
        )}

        <h2 className="text-xl font-semibold text-gray-900">Courses</h2>
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
                  <button onClick={() => openGit(c)} className="text-sm text-blue-600 hover:underline ml-4 whitespace-nowrap">
                    Git settings
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create course modal */}
      {course.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">New Course</h2>
              {course.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{course.error}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Path (slug) <span className="text-red-500">*</span>
                </label>
                <input
                  value={course.path}
                  onChange={(e) => setCourse((c) => ({ ...c, path: e.target.value }))}
                  placeholder="algorithms"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title</label>
                <input
                  value={course.title}
                  onChange={(e) => setCourse((c) => ({ ...c, title: e.target.value }))}
                  placeholder="Algorithms &amp; Data Structures"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={course.description}
                  onChange={(e) => setCourse((c) => ({ ...c, description: e.target.value }))}
                  rows={2}
                  className={inputCls}
                />
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button onClick={() => setCourse(emptyCourse)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Cancel
              </button>
              <button
                onClick={handleCreateCourse}
                disabled={course.saving || !course.path.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {course.saving ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Git settings modal */}
      {git.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Git settings — {git.courseLabel}</h2>
              {git.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{git.error}</div>
              )}
              {git.loading ? (
                <div className="text-gray-500">Loading…</div>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Delivery</label>
                    <select
                      value={git.delivery}
                      onChange={(e) => setGit((g) => ({ ...g, delivery: e.target.value as 'git' | 'download' }))}
                      className={inputCls}
                    >
                      <option value="git">git (fork/clone)</option>
                      <option value="download">download</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Git server (for the template)</label>
                    <select
                      value={git.git_server_id}
                      onChange={(e) => setGit((g) => ({ ...g, git_server_id: e.target.value }))}
                      className={inputCls}
                    >
                      <option value="">— none —</option>
                      {servers.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name || s.base_url} ({s.type})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Template repo</label>
                      <input
                        value={git.template_repo}
                        onChange={(e) => setGit((g) => ({ ...g, template_repo: e.target.value }))}
                        placeholder="owner/repo"
                        className={inputCls}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Default branch</label>
                      <input
                        value={git.default_branch}
                        onChange={(e) => setGit((g) => ({ ...g, default_branch: e.target.value }))}
                        placeholder="main"
                        className={inputCls}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Template clone URL</label>
                    <input
                      value={git.template_url}
                      onChange={(e) => setGit((g) => ({ ...g, template_url: e.target.value }))}
                      placeholder="http://host/owner/repo.git"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Allowed student-repo modes</label>
                    <div className="flex flex-wrap gap-3">
                      {ALL_MODES.map((m) => (
                        <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700">
                          <input type="checkbox" checked={git.modes.includes(m)} onChange={() => toggleMode(m)} />
                          {m}
                        </label>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button onClick={() => setGit(emptyGit)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Cancel
              </button>
              <button
                onClick={handleSaveGit}
                disabled={git.saving || git.loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {git.saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}

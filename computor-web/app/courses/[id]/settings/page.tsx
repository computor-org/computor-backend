'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import CourseGitSettingsModal from '@/src/components/CourseGitSettingsModal';
import type { CourseGet, CourseGitBindingGet, GitServerGet } from 'types/generated';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

export default function CourseSettingsPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  // Course settings expose the git registry binding, which is manager-only.
  const canManage = isAdmin || isOrganizationManager;

  const [course, setCourse] = useState<CourseGet | null>(null);
  const [binding, setBinding] = useState<CourseGitBindingGet | null>(null);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // General-settings form
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('');
  const [savingGeneral, setSavingGeneral] = useState(false);
  const [generalMsg, setGeneralMsg] = useState<string | null>(null);

  const [gitOpen, setGitOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cRes, gRes, sRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/courses/${courseId}`),
        apiFetch(`${API_BASE_URL}/courses/${courseId}/git`),
        apiFetch(`${API_BASE_URL}/git-servers`),
      ]);
      if (!cRes.ok) throw new Error('Failed to load course');
      const c: CourseGet = await cRes.json();
      setCourse(c);
      setTitle(c.title || '');
      setDescription(c.description || '');
      setLanguage(c.language_code || '');
      setBinding(gRes.ok ? await gRes.json() : null);
      if (sRes.ok) setServers(await sRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  async function saveGeneral() {
    setSavingGeneral(true);
    setGeneralMsg(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/courses/${courseId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim() || null,
          description: description.trim() || null,
          language_code: language.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Save failed (${res.status})`);
      setCourse(await res.json());
      setGeneralMsg('Saved.');
    } catch (e) {
      setGeneralMsg(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSavingGeneral(false);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound
          title="Not available"
          message="You do not have access to this course's settings."
          backLink={`/courses/${courseId}`}
          backText="Back to course"
        />
      </AuthenticatedLayout>
    );
  }

  const serverLabel = (id?: string | null) => {
    const s = servers.find((x) => x.id === id);
    return s ? `${s.name || s.base_url} (${s.type})` : id || '—';
  };
  const gitConfigured = binding && binding.delivery;

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-3xl">
        <div>
          <Link href={`/courses/${courseId}`} className="text-sm text-blue-600 hover:underline">
            ← {course?.title || course?.path || 'Course'}
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">Course Settings</h1>
          {course && <p className="mt-1 text-sm text-gray-500 font-mono">{course.path}</p>}
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
        )}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : (
          <>
            {/* General */}
            <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">General</h2>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title</label>
                <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Language code</label>
                  <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="en" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Path (immutable)</label>
                  <input value={course?.path || ''} readOnly className={`${inputCls} bg-gray-50 text-gray-500`} />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={saveGeneral}
                  disabled={savingGeneral}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingGeneral ? 'Saving…' : 'Save'}
                </button>
                {generalMsg && <span className="text-sm text-gray-500">{generalMsg}</span>}
              </div>
            </section>

            {/* Git */}
            <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Git</h2>
                <button
                  onClick={() => setGitOpen(true)}
                  className="px-3 py-1.5 text-sm font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50"
                >
                  {gitConfigured ? 'Edit' : 'Configure'}
                </button>
              </div>
              {gitConfigured ? (
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Delivery</dt>
                    <dd className="text-gray-900">{binding!.delivery}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Git server</dt>
                    <dd className="text-gray-900">{binding!.git_server_id ? serverLabel(binding!.git_server_id) : '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Student-repo modes</dt>
                    <dd className="text-gray-900">{(binding!.student_repo_modes || []).join(', ') || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Template</dt>
                    <dd className="text-gray-900 font-mono text-xs break-all">{binding!.template_repo || '—'}</dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-gray-500">
                  This course has no git configuration. Configure it to enable student repositories.
                </p>
              )}
            </section>
          </>
        )}
      </div>

      {gitOpen && course && (
        <CourseGitSettingsModal
          courseId={courseId}
          courseLabel={course.title || course.path}
          onClose={() => setGitOpen(false)}
          onSaved={load}
        />
      )}
    </AuthenticatedLayout>
  );
}

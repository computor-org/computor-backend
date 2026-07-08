'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import { Field, inputCls } from '@/src/components/FormPanel';
import type { CourseGet, CourseGitBindingGet, CourseGitBindingUpsert, GitServerGet } from 'types/generated';

const coursesClient = new CoursesClient();
const gitServersClient = new GitServersClient();

const ALL_MODES = ['managed', 'external', 'download'];
const MODE_LABELS: Record<string, string> = {
  managed: 'Managed — we host it',
  external: 'External — student-hosted (any provider)',
  download: 'Download — no git',
};

export default function CourseEditPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  // The git binding is registry-backed (manager-only).
  const { canManageHierarchy: canManage } = usePermissions();

  const [course, setCourse] = useState<CourseGet | null>(null);
  const [binding, setBinding] = useState<CourseGitBindingGet | null>(null);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // General form
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('');
  const [savingGeneral, setSavingGeneral] = useState(false);
  const [generalMsg, setGeneralMsg] = useState<string | null>(null);

  // Git binding form
  const [delivery, setDelivery] = useState<'git' | 'download'>('git');
  const [gitServerId, setGitServerId] = useState('');
  const [templateRepo, setTemplateRepo] = useState('');
  const [templateUrl, setTemplateUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [modes, setModes] = useState<string[]>([]);
  const [parentGroupId, setParentGroupId] = useState('');
  const [token, setToken] = useState('');
  const [hasToken, setHasToken] = useState(false);
  const [savingGit, setSavingGit] = useState(false);
  const [gitMsg, setGitMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await coursesClient.getCoursesCoursesIdGet({ id: courseId });
      setCourse(c);
      setTitle(c.title || '');
      setDescription(c.description || '');
      setLanguage(c.language_code || '');
      const srv = await gitServersClient.listGitServersEndpointGitServersGet({}).catch(() => [] as GitServerGet[]);
      setServers(srv);
      // The binding endpoint 404s when a course has none yet — treat as null.
      const b = await coursesClient.getCourseGitBindingEndpointCoursesCourseIdGitGet({ courseId }).catch(() => null);
      setBinding(b);
      if (b && b.delivery) {
        setDelivery(b.delivery === 'download' ? 'download' : 'git');
        setGitServerId(b.git_server_id || '');
        setTemplateRepo(b.template_repo || '');
        setTemplateUrl(b.template_url || '');
        setBranch(b.default_branch || 'main');
        setModes(b.student_repo_modes || []);
        setParentGroupId(b.parent_group_id || '');
        setHasToken(!!b.has_token);
        setToken('');
      } else {
        // No binding yet — default to a managed server + the managed mode.
        setGitServerId(srv.find((s) => s.managed)?.id ?? srv[0]?.id ?? '');
        setModes(['managed']);
      }
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
      const updated = await coursesClient.updateCoursesCoursesIdPatch({
        id: courseId,
        body: {
          title: title.trim() || null,
          description: description.trim() || null,
          language_code: language.trim() || null,
        },
      });
      setCourse(updated);
      setGeneralMsg('Saved.');
    } catch (e) {
      setGeneralMsg(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSavingGeneral(false);
    }
  }

  const toggleMode = (m: string) => setModes((ms) => (ms.includes(m) ? ms.filter((x) => x !== m) : [...ms, m]));

  async function saveGit() {
    setSavingGit(true);
    setGitMsg(null);
    try {
      const selected = servers.find((s) => s.id === gitServerId);
      const body: CourseGitBindingUpsert = {
        delivery,
        git_server_id: gitServerId || null,
        template_repo: templateRepo.trim() || null,
        template_url: templateUrl.trim() || null,
        default_branch: branch.trim() || 'main',
        student_repo_modes: modes,
      };
      // External GitLab carries its own parent group + group token on the course.
      // Only send the token when the field was filled (blank keeps the stored one).
      if (selected?.type === 'gitlab') {
        if (parentGroupId.trim()) body.parent_group_id = parentGroupId.trim();
        if (token.trim()) body.token = token.trim();
      }
      await coursesClient.upsertCourseGitBindingEndpointCoursesCourseIdGitPut({ courseId, body });
      setGitMsg('Saved.');
      await load();
    } catch (e) {
      setGitMsg(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSavingGit(false);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have access to this course's settings." backLink={`/courses/${courseId}`} backText="Back to course" />;
  }

  const serverLabel = (id?: string | null) => {
    const s = servers.find((x) => x.id === id);
    return s ? `${s.name || s.base_url} (${s.type})` : id || '—';
  };
  const gitConfigured = binding && binding.delivery;
  const gitLocked = !!binding?.locked;
  const selectedServer = servers.find((s) => s.id === gitServerId);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: course?.title || course?.path || 'Course', href: `/courses/${courseId}` },
            { label: 'Edit' },
          ]}
          title="Edit course"
          subtitle={course ? <span className="text-sm text-gray-500 font-mono">{course.path}</span> : undefined}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            <div className="max-w-3xl space-y-6">
              {/* General */}
              <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">General</h2>
                <Field label="Title">
                  <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
                </Field>
                <Field label="Description">
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Language code">
                    <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="en" className={inputCls} />
                  </Field>
                  <Field label="Path (immutable)">
                    <input value={course?.path || ''} readOnly className={`${inputCls} bg-gray-50 text-gray-500`} />
                  </Field>
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={saveGeneral} disabled={savingGeneral} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                    {savingGeneral ? 'Saving…' : 'Save'}
                  </button>
                  {generalMsg && <span className="text-sm text-gray-500">{generalMsg}</span>}
                </div>
              </section>

              {/* Git */}
              <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">Git</h2>
                  {gitLocked && (
                    <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-500 rounded inline-flex items-center gap-1">
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      Locked
                    </span>
                  )}
                </div>

                {gitLocked ? (
                  <>
                    <p className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded p-2.5">
                      {binding?.lock_reason || 'This course’s git configuration is locked.'} Changing the server or
                      template would orphan students’ existing repositories, so these settings are read-only.
                    </p>
                    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                      <div><dt className="text-gray-500">Delivery</dt><dd className="text-gray-900">{binding!.delivery}</dd></div>
                      <div><dt className="text-gray-500">Git server</dt><dd className="text-gray-900">{binding!.git_server_id ? serverLabel(binding!.git_server_id) : '—'}</dd></div>
                      <div><dt className="text-gray-500">Student-repo modes</dt><dd className="text-gray-900">{(binding!.student_repo_modes || []).join(', ') || '—'}</dd></div>
                      <div><dt className="text-gray-500">Template</dt><dd className="text-gray-900 font-mono text-xs break-all">{binding!.template_repo || '—'}</dd></div>
                    </dl>
                  </>
                ) : (
                  <>
                    {!gitConfigured && (
                      <p className="text-sm text-gray-500">This course has no git configuration yet. Configure it to enable student repositories.</p>
                    )}
                    <Field label="Delivery">
                      <select value={delivery} onChange={(e) => setDelivery(e.target.value as 'git' | 'download')} className={inputCls}>
                        <option value="git">git (fork/clone)</option>
                        <option value="download">download</option>
                      </select>
                    </Field>
                    <Field label="Git server (for the template)" hint="For a managed server (Forgejo or GitLab), leave the template fields blank — the template repo is created automatically.">
                      <select value={gitServerId} onChange={(e) => setGitServerId(e.target.value)} className={inputCls}>
                        <option value="">— none —</option>
                        {servers.map((s) => (
                          <option key={s.id} value={s.id}>{s.name || s.base_url} ({s.type})</option>
                        ))}
                      </select>
                    </Field>
                    {selectedServer?.type === 'gitlab' && (
                      <>
                        <Field label="GitLab parent group id" hint="The course's own GitLab group is created under this parent group.">
                          <input value={parentGroupId} onChange={(e) => setParentGroupId(e.target.value)} placeholder="12345" className={inputCls} />
                        </Field>
                        <Field label="GitLab group token" hint={hasToken ? 'A token is already stored — enter a new one to replace it.' : 'A group access token scoped to the parent group — stored encrypted on this course, never shown again.'}>
                          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={hasToken ? '•••••••• (stored)' : 'glpat-…'} className={inputCls} />
                        </Field>
                      </>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Template repo">
                        <input value={templateRepo} onChange={(e) => setTemplateRepo(e.target.value)} placeholder="owner/repo" className={inputCls} />
                      </Field>
                      <Field label="Default branch">
                        <input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" className={inputCls} />
                      </Field>
                    </div>
                    <Field label="Template clone URL">
                      <input value={templateUrl} onChange={(e) => setTemplateUrl(e.target.value)} placeholder="auto for managed servers" className={inputCls} />
                    </Field>
                    <Field label="Allowed student-repo modes">
                      <div className="flex flex-wrap gap-3">
                        {ALL_MODES.map((m) => (
                          <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700">
                            <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                            {MODE_LABELS[m] ?? m}
                          </label>
                        ))}
                      </div>
                    </Field>
                    <div className="flex items-center gap-3">
                      <button onClick={saveGit} disabled={savingGit} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                        {savingGit ? 'Saving…' : gitConfigured ? 'Save git settings' : 'Configure git'}
                      </button>
                      {gitMsg && <span className="text-sm text-gray-500">{gitMsg}</span>}
                    </div>
                  </>
                )}
              </section>
            </div>
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import type { GitServerGet } from '@/src/generated/types/common';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';
const ALL_MODES = ['forgejo', 'gitlab_byo', 'download'];

/**
 * Reusable course git-binding editor (reads/writes GET/PUT /courses/{id}/git).
 * Used from the course-family detail and the courses management list. Listing
 * git servers is registry-admin only; for a managed Forgejo the backend
 * auto-provisions the template repo on save.
 */
export default function CourseGitSettingsModal({
  courseId,
  courseLabel,
  onClose,
  onSaved,
}: {
  courseId: string;
  courseLabel: string;
  onClose: () => void;
  onSaved?: () => void;
}) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [delivery, setDelivery] = useState<'git' | 'download'>('git');
  const [serverId, setServerId] = useState('');
  const [templateRepo, setTemplateRepo] = useState('');
  const [templateUrl, setTemplateUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [modes, setModes] = useState<string[]>([]);
  const [locked, setLocked] = useState(false);
  const [lockReason, setLockReason] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [bRes, sRes] = await Promise.all([
          apiFetch(`${API_BASE_URL}/courses/${courseId}/git`),
          apiFetch(`${API_BASE_URL}/git-servers`),
        ]);
        if (!cancelled && sRes.ok) setServers(await sRes.json());
        if (!cancelled && bRes.ok) {
          const b = await bRes.json();
          setDelivery(b.delivery === 'download' ? 'download' : 'git');
          setServerId(b.git_server_id || '');
          setTemplateRepo(b.template_repo || '');
          setTemplateUrl(b.template_url || '');
          setBranch(b.default_branch || 'main');
          setModes(b.student_repo_modes || []);
          setLocked(!!b.locked);
          setLockReason(b.lock_reason || null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load git settings');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  const toggleMode = (m: string) =>
    setModes((ms) => (ms.includes(m) ? ms.filter((x) => x !== m) : [...ms, m]));

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/courses/${courseId}/git`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delivery,
          git_server_id: serverId || null,
          template_repo: templateRepo.trim() || null,
          template_url: templateUrl.trim() || null,
          default_branch: branch.trim() || 'main',
          student_repo_modes: modes,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Save failed (${res.status})`);
      onSaved?.();
      onClose();
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Git settings — {courseLabel}</h2>
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}
          {locked && (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-600">
              {lockReason || 'This course’s git configuration is locked.'} Changing the server or
              template would orphan students’ existing repositories, so it can no longer be edited.
            </div>
          )}
          {loading ? (
            <div className="text-gray-500">Loading…</div>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Delivery</label>
                <select value={delivery} onChange={(e) => setDelivery(e.target.value as 'git' | 'download')} className={inputCls}>
                  <option value="git">git (fork/clone)</option>
                  <option value="download">download</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Git server (for the template)</label>
                <select value={serverId} onChange={(e) => setServerId(e.target.value)} className={inputCls}>
                  <option value="">— none —</option>
                  {servers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name || s.base_url} ({s.type})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-400">
                  For a managed Forgejo, leave the template fields blank — the template repo is created automatically.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Template repo</label>
                  <input value={templateRepo} onChange={(e) => setTemplateRepo(e.target.value)} placeholder="owner/repo" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Default branch</label>
                  <input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" className={inputCls} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Template clone URL</label>
                <input value={templateUrl} onChange={(e) => setTemplateUrl(e.target.value)} placeholder="auto for managed Forgejo" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Allowed student-repo modes</label>
                <div className="flex flex-wrap gap-3">
                  {ALL_MODES.map((m) => (
                    <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700">
                      <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                      {m}
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
        <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving || loading || locked}
            title={locked ? 'Git configuration is locked' : undefined}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

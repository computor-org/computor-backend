'use client';

import { useCallback, useEffect, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useNotify } from '@/src/contexts/NotificationContext';
import { api } from '@/src/utils/api';
import type { PolicyVersionGet, PolicyVersionCreate } from 'types/generated';

type LangRow = { lang: string; text: string; filename?: string };

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm';

function fmtDate(s?: string | null): string {
  return s ? new Date(s).toLocaleString() : '—';
}

export default function PrivacyNoticesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const notify = useNotify();

  const [versions, setVersions] = useState<PolicyVersionGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Publish form
  const [version, setVersion] = useState('');
  const [effectiveFrom, setEffectiveFrom] = useState('');
  const [langs, setLangs] = useState<LangRow[]>([{ lang: 'en', text: '' }]);
  const [publishing, setPublishing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const fetchVersions = useCallback(async () => {
    try {
      const data = await api.get<PolicyVersionGet[]>('/consent/policy-versions');
      setVersions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load policy versions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    fetchVersions();
  }, [authLoading, isAuthenticated, fetchVersions]);

  // The current version = latest already-effective version; anything with a
  // future effective_from is "scheduled".
  const now = Date.now();
  const currentVersion = versions
    .filter((v) => new Date(v.effective_from).getTime() <= now)
    .sort((a, b) => new Date(b.effective_from).getTime() - new Date(a.effective_from).getTime())[0]?.version;

  const addLang = () => setLangs((ls) => [...ls, { lang: '', text: '' }]);
  const removeLang = (i: number) => setLangs((ls) => ls.filter((_, idx) => idx !== i));
  const setLangCode = (i: number, code: string) =>
    setLangs((ls) => ls.map((l, idx) => (idx === i ? { ...l, lang: code } : l)));
  const setLangText = (i: number, text: string) =>
    setLangs((ls) => ls.map((l, idx) => (idx === i ? { ...l, text } : l)));

  const onPickFile = async (i: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const stem = file.name.replace(/\.(md|markdown)$/i, '');
    setLangs((ls) =>
      ls.map((l, idx) => (idx === i ? { ...l, text, filename: file.name, lang: l.lang.trim() || stem } : l)),
    );
    // allow re-picking the same file
    e.target.value = '';
  };

  const filledLangs = langs.filter((l) => l.lang.trim() && l.text.trim());
  const codes = filledLangs.map((l) => l.lang.trim());
  const dupCode = codes.find((c, i) => codes.indexOf(c) !== i);
  const validationError = !version.trim()
    ? 'A version identifier is required (e.g. 2026-07-05).'
    : filledLangs.length === 0
    ? 'Add at least one language with notice text.'
    : dupCode
    ? `Duplicate language code: "${dupCode}".`
    : versions.some((v) => v.version === version.trim())
    ? `Version "${version.trim()}" already exists — versions are append-only.`
    : null;

  const doPublish = async () => {
    setShowConfirm(false);
    setPublishing(true);
    try {
      const texts: Record<string, string> = {};
      for (const l of filledLangs) texts[l.lang.trim()] = l.text;
      const body: PolicyVersionCreate = { version: version.trim(), texts };
      if (effectiveFrom) body.effective_from = new Date(effectiveFrom).toISOString();
      const created = await api.post<PolicyVersionGet>('/consent/policy-versions', body);
      notify(`Published privacy notice version ${created.version}`, 'success');
      setVersion('');
      setEffectiveFrom('');
      setLangs([{ lang: 'en', text: '' }]);
      await fetchVersions();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to publish policy version', 'error');
    } finally {
      setPublishing(false);
    }
  };

  const onClickPublish = () => {
    if (validationError) {
      notify(validationError, 'error');
      return;
    }
    setShowConfirm(true);
  };

  // Access control
  if (!authLoading && !isAdmin) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-red-800">Access Denied</h2>
            <p className="text-sm text-red-600 mt-2">Admin privileges are required to manage privacy notices.</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Privacy Notices' }]}
          title="Privacy Notices"
          subtitle="Publish and review the GDPR consent policy versions that back the consent gate."
        />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea className="space-y-6">
          {/* Warning */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-amber-900 mb-1">Before you publish</h2>
            <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
              <li>Versions are <strong>append-only</strong> — a version can be published once. Bump the version for any change.</li>
              <li>Publishing with an effective date of now <strong>re-gates every user</strong> who hasn’t consented to the new version.</li>
              <li>The VS Code extension has no consent handling yet — unconsented users will get errors there.</li>
            </ul>
          </div>

          {/* Published versions */}
          <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Published versions</h2>
            {loading ? (
              <div className="text-sm text-gray-500">Loading…</div>
            ) : versions.length === 0 ? (
              <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-lg p-6 text-center">
                No privacy notice has been published yet. The consent gate stays inactive until the first version is published.
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg divide-y">
                {versions.map((v) => {
                  const scheduled = new Date(v.effective_from).getTime() > now;
                  const isCurrent = v.version === currentVersion;
                  return (
                    <div key={v.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 flex items-center gap-2">
                          <span className="font-mono">{v.version}</span>
                          {isCurrent && <Badge color="green" pill>current</Badge>}
                          {scheduled && <Badge color="blue" pill>scheduled</Badge>}
                        </div>
                        <div className="text-xs text-gray-500">
                          effective {fmtDate(v.effective_from)} · languages: {(v.languages || []).join(', ') || '—'} · published {fmtDate(v.created_at)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Publish new */}
          <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Publish a new version</h2>

            <div className="flex flex-wrap gap-4 mb-4">
              <div className="flex-1 min-w-[12rem]">
                <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                <input
                  className={inputCls}
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="e.g. 2026-07-05"
                />
              </div>
              <div className="flex-1 min-w-[12rem]">
                <label className="block text-sm font-medium text-gray-700 mb-1">Effective from</label>
                <input
                  type="datetime-local"
                  className={inputCls}
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">Leave empty to become current immediately. A future date schedules it.</p>
              </div>
            </div>

            <label className="block text-sm font-medium text-gray-700 mb-2">Notice text (Markdown, one per language)</label>
            <div className="space-y-4">
              {langs.map((l, i) => (
                <div key={i} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex flex-wrap items-center gap-3 mb-2">
                    <input
                      className="w-28 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                      value={l.lang}
                      onChange={(e) => setLangCode(i, e.target.value)}
                      placeholder="lang (en)"
                      aria-label="Language code"
                    />
                    <label className="px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 cursor-pointer">
                      {l.filename ? `Replace ${l.filename}` : 'Upload .md'}
                      <input type="file" accept=".md,.markdown,text/markdown" className="hidden" onChange={(e) => onPickFile(i, e)} />
                    </label>
                    {langs.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeLang(i)}
                        className="ml-auto text-sm text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
                    rows={8}
                    value={l.text}
                    onChange={(e) => setLangText(i, e.target.value)}
                    placeholder={'# Privacy notice\n\nUpload a .md file or paste the Markdown here…'}
                  />
                </div>
              ))}
            </div>

            <div className="mt-3 flex items-center gap-4">
              <button type="button" onClick={addLang} className="text-sm text-blue-600 hover:underline">
                + Add language
              </button>
            </div>

            <div className="mt-5 flex items-center gap-4">
              <button
                type="button"
                onClick={onClickPublish}
                disabled={publishing || !!validationError}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {publishing ? 'Publishing…' : 'Publish version'}
              </button>
              {validationError && <span className="text-sm text-gray-500">{validationError}</span>}
            </div>
          </div>
        </ScrollArea>

        <ConfirmDialog
          open={showConfirm}
          title="Publish privacy notice"
          message={
            effectiveFrom
              ? `Publish version "${version.trim()}"? It becomes current at the scheduled time; users are re-gated then.`
              : `Publish version "${version.trim()}"? It becomes current immediately and re-gates every user who has not consented to it. This cannot be undone (versions are append-only).`
          }
          confirmLabel="Publish"
          variant="danger"
          onConfirm={doPublish}
          onCancel={() => setShowConfirm(false)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

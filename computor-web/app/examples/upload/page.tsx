'use client';

import { useLecturerCopy } from '@/src/hooks/useLecturerCopy';
import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ApiError } from '@/src/api/client';
import { ExamplesClient } from '@/src/generated/clients/ExamplesClient';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, PageLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import { discoverExamplesInZip, type DiscoveredExample } from '@/src/utils/exampleZip';
import type { ExampleRepositoryList } from 'types/generated';

const examplesClient = new ExamplesClient();
const exampleRepositoriesClient = new ExampleRepositoriesClient();

const DIR_OK = /^[a-zA-Z0-9._-]+$/;

interface UploadRow extends DiscoveredExample {
  status: 'pending' | 'uploading' | 'ok' | 'existing' | 'error';
  message?: string;
}

function UploadInner() {
  const t = useLecturerCopy();
  const router = useRouter();
  const initialRepo = useSearchParam('repository');
  const forcedDirectory = useSearchParam('directory');

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageExamples: canManage } = usePermissions();

  const [repos, setRepos] = useState<ExampleRepositoryList[]>([]);
  const [repoId, setRepoId] = useState(initialRepo);
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [fileName, setFileName] = useState('');
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    let cancelled = false;
    exampleRepositoriesClient.listExampleRepositoriesExampleRepositoriesGet({ limit: 200 })
      .then(all => {
        if (cancelled) return;
        const uploadable = all.filter(r => r.source_type === 'minio' || r.source_type === 's3');
        setRepos(uploadable);
        if (!initialRepo && uploadable.length === 1) setRepoId(uploadable[0].id);
      })
      .catch(() => { if (!cancelled) setError(t('Failed to load repositories')); });
    return () => { cancelled = true; };
  }, [authLoading, isAuthenticated, canManage, initialRepo, t]);

  async function onPickZip(file: File | undefined) {
    if (!file) return;
    setFileName(file.name);
    setParsing(true);
    setParseError(null);
    setRows([]);
    try {
      const discovered = await discoverExamplesInZip(file);
      // "Upload new version" targets a specific directory: when a single example
      // is discovered and a directory is forced, honour it.
      const adjusted =
        forcedDirectory && discovered.length === 1 ? [{ ...discovered[0], directory: forcedDirectory }] : discovered;
      setRows(adjusted.map((d) => ({ ...d, status: 'pending' })));
    } catch {
      setParseError(t('Could not read the zip'));
    } finally {
      setParsing(false);
    }
  }

  async function runUpload() {
    if (!repoId) return;
    setUploading(true);
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (row.status === 'ok' || row.status === 'existing') continue;
      setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, status: 'uploading', message: undefined } : r)));
      try {
        const v = await examplesClient.uploadExampleExamplesUploadPost({
          body: {
            repository_id: repoId,
            directory: row.directory,
            files: row.files,
          },
        });
        setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, status: 'ok', message: `v${v.version_tag ?? ''}` } : r)));
      } catch (e) {
        const exists = e instanceof ApiError && e.errorCode === 'VERSION_001';
        setRows((rs) => rs.map((r, idx) => idx === i ? {
          ...r,
          status: exists ? 'existing' : 'error',
          message: t(exists
            ? 'This version already exists and was kept. Use a new version tag for changed files.'
            : 'Upload failed. Check the example and try again.'),
        } : r));
      }
    }
    setUploading(false);
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t("You do not have access to examples.")} backLink="/examples" backText={t("Back")} />;
  }

  const dirsValid = rows.length > 0 && rows.every((r) => DIR_OK.test(r.directory));
  const allDone = rows.length > 0 && rows.every((r) => r.status === 'ok' || r.status === 'existing' || r.status === 'error');

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <div className="[&>div>div]:flex-wrap [&>div>div>div]:flex-wrap">
          <PageHeader
            breadcrumbs={[{ label: t("Examples"), href: '/examples' }, { label: t("Upload") }]}
            title={t("Upload examples")}
            subtitle={
              <>
                {t('Choose a ZIP file containing one or more examples. Each example needs a meta.yaml file in its folder.')}
              </>
            }
            actions={
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => router.push('/examples')}
                  className="px-4 py-2 text-sm text-muted hover:bg-sunken rounded-lg"
                >
                  {allDone ? t("Done") : t("Cancel")}
                </button>
                <button
                  type="button"
                  onClick={runUpload}
                  disabled={uploading || rows.length === 0 || !dirsValid || !repoId || !rows.some(r => r.status === 'pending' || r.status === 'error')}
                  className="px-4 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-50"
                >
                  {uploading ? t("Uploading…") : `${t('Upload')} ${rows.length || ''}`}
                </button>
              </div>
            }
          />
        </div>

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          <div className="max-w-2xl">
            {allDone && <p role="status" className="mb-4 text-sm text-muted">{t('Uploaded')}: {rows.filter(r => r.status === 'ok').length}. {t('Already exists')}: {rows.filter(r => r.status === 'existing').length}. {t('Failed')}: {rows.filter(r => r.status === 'error').length}.</p>}
            <div className="bg-surface border border-rule rounded-lg p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-body mb-1">{t("Repository")}</label>
                {repos.length === 0 ? (
                  <p className="text-sm text-muted">
                    {t('No uploadable repository.')} {' '}
                    <Link href="/example-repositories/create" className="text-accent-text hover:underline">{t('Create one first')}</Link>.
                  </p>
                ) : (
                  <select
                    value={repoId}
                    onChange={(e) => setRepoId(e.target.value)}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line"
                  >
                    <option value="">{t('Select a repository')}</option>
                    {repos.map((r) => (
                      <option key={r.id} value={r.id}>{r.name === 'Default Examples' ? t('Default Examples') : r.name} ({r.source_type})</option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-body mb-1">{t("Zip file")}</label>
                <label className="inline-flex cursor-pointer rounded-lg bg-accent-wash px-4 py-2 text-sm font-medium text-accent-text focus-within:ring-2 focus-within:ring-accent-line">
                  {t('Choose ZIP file')}
                  <input type="file" accept=".zip,application/zip" onChange={(e) => onPickZip(e.target.files?.[0])} className="sr-only" />
                </label>
                <p className="mt-2 break-words text-sm text-muted">{fileName || t('No file selected')}</p>
              </div>

              {parsing && <div className="text-sm text-muted">{t("Reading zip…")}</div>}
              <ErrorBanner>{parseError}</ErrorBanner>

              {rows.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted">{t('Examples found')}: {rows.length}</div>
                  {rows.map((r, i) => (
                    <div key={i} className="flex flex-wrap items-center gap-3 border border-rule rounded-lg px-3 py-2">
                      <input
                        value={r.directory}
                        disabled={uploading || r.status === 'ok' || r.status === 'existing'}
                        onChange={(e) => setRows((rs) => rs.map((x, idx) => (idx === i ? { ...x, directory: e.target.value } : x)))}
                        className={`min-w-0 basis-full sm:basis-auto flex-1 px-2 py-1 border rounded text-sm font-mono ${DIR_OK.test(r.directory) ? 'border-rule-strong' : 'border-danger-line'}`}
                      />
                      <span className="text-xs text-subtle shrink-0">{t('Files')}: {r.fileCount}</span>
                      <span
                        className={`text-xs break-words text-right ${
                          r.status === 'ok' || r.status === 'existing' ? 'text-success-text' : r.status === 'error' ? 'text-danger-text' : r.status === 'uploading' ? 'text-warn-text' : 'text-subtle'
                        }`}
                        title={r.message}
                      >
                        {r.status === 'pending' ? t("ready") : r.status === 'uploading' ? t("uploading…") : r.status === 'ok' ? `${t('uploaded')} ${r.message ?? ''}` : r.message}
                      </span>
                    </div>
                  ))}
                  {!dirsValid && (
                    <p className="text-xs text-danger-text">{t("Directory names may only contain letters, numbers, dots, dashes and underscores.")}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

export default function ExampleUploadPage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><PageLoading /></AuthenticatedLayout>}>
      <UploadInner />
    </Suspense>
  );
}

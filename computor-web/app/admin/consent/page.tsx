'use client';

import { useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, PageActions } from '@/src/components/ListPageLayout';
import Button from '@/src/components/ui/Button';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import { ConsentClient } from '@/src/generated/clients/ConsentClient';
import type { PolicyVersionCreate } from 'types/generated';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';

const consentClient = new ConsentClient();

type LangRow = { lang: string; text: string; filename?: string };

const inputCls =
  'w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm';

const COPY = {
  de: {
    versionRequired: 'Eine Versionskennung ist erforderlich (z. B. 2026-07-05).',
    addLanguage: 'Füge mindestens eine Sprache mit Text der Datenschutzerklärung hinzu.',
    duplicate: (code: string) => `Doppelter Sprachcode: „${code}“.`,
    exists: (version: string) => `Die Version „${version}“ existiert bereits, Versionen werden nur angehängt.`,
    published: (version: string) => `Version ${version} der Datenschutzerklärung veröffentlicht`,
    publishFailed: 'Die Version konnte nicht veröffentlicht werden',
    denied: 'Zugriff verweigert',
    adminRequired: 'Zum Verwalten der Datenschutzhinweise sind Administratorrechte erforderlich.',
    title: 'Datenschutzhinweise',
    subtitle: 'Veröffentliche und prüfe die DSGVO-Versionen der Datenschutzerklärung, auf denen die Einwilligungsabfrage beruht.',
    beforePublish: 'Bevor du veröffentlichst',
    warnAppendBefore: 'Versionen werden ',
    warnAppendStrong: 'nur angehängt',
    warnAppendAfter: ': Eine Version kann nur einmal veröffentlicht werden. Erhöhe die Version bei jeder Änderung.',
    warnRegateBefore: 'Eine Veröffentlichung mit sofortigem Gültigkeitsdatum ',
    warnRegateStrong: 'fragt jeden Benutzer erneut ab',
    warnRegateAfter: ', der der neuen Version noch nicht zugestimmt hat.',
    warnExtension: 'Die VS-Code-Erweiterung unterstützt noch keine Einwilligung, Benutzer ohne Einwilligung erhalten dort Fehler.',
    publishedVersions: 'Veröffentlichte Versionen',
    loading: 'Wird geladen…',
    none: 'Es wurde noch keine Datenschutzerklärung veröffentlicht. Die Einwilligungsabfrage bleibt inaktiv, bis die erste Version veröffentlicht ist.',
    current: 'aktuell',
    scheduled: 'geplant',
    versionLine: (effective: string, languages: string, created: string) =>
      `gültig ab ${effective} · Sprachen: ${languages} · veröffentlicht ${created}`,
    publishNew: 'Neue Version veröffentlichen',
    version: 'Version',
    versionPlaceholder: 'z. B. 2026-07-05',
    effectiveFrom: 'Gültig ab',
    effectiveHint: 'Leer lassen, damit die Version sofort gilt. Ein Datum in der Zukunft plant sie ein.',
    noticeText: 'Text der Datenschutzerklärung (Markdown, je Sprache einer)',
    langPlaceholder: 'Sprache (en)',
    langAria: 'Sprachcode',
    replace: (name: string) => `${name} ersetzen`,
    upload: '.md hochladen',
    remove: 'Entfernen',
    textPlaceholder: '# Datenschutzerklärung\n\nLade eine .md-Datei hoch oder füge das Markdown hier ein…',
    addLang: '+ Sprache hinzufügen',
    publishing: 'Wird veröffentlicht…',
    publishVersion: 'Version veröffentlichen',
    confirmTitle: 'Datenschutzerklärung veröffentlichen',
    confirmScheduled: (version: string) => `Version „${version}“ veröffentlichen? Sie gilt ab dem geplanten Zeitpunkt, dann werden die Benutzer erneut abgefragt.`,
    confirmNow: (version: string) => `Version „${version}“ veröffentlichen? Sie gilt sofort und fragt jeden Benutzer erneut ab, der ihr noch nicht zugestimmt hat. Das lässt sich nicht rückgängig machen (Versionen werden nur angehängt).`,
    confirmLabel: 'Veröffentlichen',
  },
  en: {
    versionRequired: 'A version identifier is required (e.g. 2026-07-05).',
    addLanguage: 'Add at least one language with notice text.',
    duplicate: (code: string) => `Duplicate language code: "${code}".`,
    exists: (version: string) => `Version "${version}" already exists — versions are append-only.`,
    published: (version: string) => `Published privacy notice version ${version}`,
    publishFailed: 'Failed to publish policy version',
    denied: 'Access Denied',
    adminRequired: 'Admin privileges are required to manage privacy notices.',
    title: 'Privacy notices',
    subtitle: 'Publish and review the GDPR consent policy versions that back the consent gate.',
    beforePublish: 'Before you publish',
    warnAppendBefore: 'Versions are ',
    warnAppendStrong: 'append-only',
    warnAppendAfter: ' — a version can be published once. Bump the version for any change.',
    warnRegateBefore: 'Publishing with an effective date of now ',
    warnRegateStrong: 're-gates every user',
    warnRegateAfter: ' who hasn’t consented to the new version.',
    warnExtension: 'The VS Code extension has no consent handling yet — unconsented users will get errors there.',
    publishedVersions: 'Published versions',
    loading: 'Loading…',
    none: 'No privacy notice has been published yet. The consent gate stays inactive until the first version is published.',
    current: 'current',
    scheduled: 'scheduled',
    versionLine: (effective: string, languages: string, created: string) =>
      `effective ${effective} · languages: ${languages} · published ${created}`,
    publishNew: 'Publish a new version',
    version: 'Version',
    versionPlaceholder: 'e.g. 2026-07-05',
    effectiveFrom: 'Effective from',
    effectiveHint: 'Leave empty to become current immediately. A future date schedules it.',
    noticeText: 'Notice text (Markdown, one per language)',
    langPlaceholder: 'lang (en)',
    langAria: 'Language code',
    replace: (name: string) => `Replace ${name}`,
    upload: 'Upload .md',
    remove: 'Remove',
    textPlaceholder: '# Privacy notice\n\nUpload a .md file or paste the Markdown here…',
    addLang: '+ Add language',
    publishing: 'Publishing…',
    publishVersion: 'Publish version',
    confirmTitle: 'Publish privacy notice',
    confirmScheduled: (version: string) => `Publish version "${version}"? It becomes current at the scheduled time; users are re-gated then.`,
    confirmNow: (version: string) => `Publish version "${version}"? It becomes current immediately and re-gates every user who has not consented to it. This cannot be undone (versions are append-only).`,
    confirmLabel: 'Publish',
  },
};

export default function PrivacyNoticesPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const fmtDate = (s?: string | null) => formatDateTime(s, language);
  const { isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const notify = useNotify();

  const { data, loading, error, reload } = useResource(
    () => consentClient.listPolicyVersionsConsentPolicyVersionsGet({}),
    [],
  );
  const versions = data ?? [];

  // Publish form
  const [version, setVersion] = useState('');
  const [effectiveFrom, setEffectiveFrom] = useState('');
  const [langs, setLangs] = useState<LangRow[]>([{ lang: 'en', text: '' }]);
  const [publishing, setPublishing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

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
    ? t.versionRequired
    : filledLangs.length === 0
    ? t.addLanguage
    : dupCode
    ? t.duplicate(dupCode)
    : versions.some((v) => v.version === version.trim())
    ? t.exists(version.trim())
    : null;

  const doPublish = async () => {
    setShowConfirm(false);
    setPublishing(true);
    try {
      const texts: Record<string, string> = {};
      for (const l of filledLangs) texts[l.lang.trim()] = l.text;
      const body: PolicyVersionCreate = { version: version.trim(), texts };
      if (effectiveFrom) body.effective_from = new Date(effectiveFrom).toISOString();
      const created = await consentClient.publishPolicyVersionConsentPolicyVersionsPost({ body });
      notify(t.published(created.version), 'success');
      setVersion('');
      setEffectiveFrom('');
      setLangs([{ lang: 'en', text: '' }]);
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.publishFailed, 'error');
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
          <div className="bg-danger-wash border border-danger-line rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-danger-text">{t.denied}</h2>
            <p className="text-sm text-danger-text mt-2">{t.adminRequired}</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
        />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          {/* Warning */}
          <div className="bg-warn-wash border border-warn-line rounded-lg p-4">
            <h2 className="text-sm font-semibold text-warn-text mb-1">{t.beforePublish}</h2>
            <ul className="text-sm text-warn-text space-y-1 list-disc list-inside">
              <li>{t.warnAppendBefore}<strong>{t.warnAppendStrong}</strong>{t.warnAppendAfter}</li>
              <li>{t.warnRegateBefore}<strong>{t.warnRegateStrong}</strong>{t.warnRegateAfter}</li>
              <li>{t.warnExtension}</li>
            </ul>
          </div>

          {/* Published versions */}
          <div className="bg-surface rounded-lg shadow border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-4">{t.publishedVersions}</h2>
            {loading ? (
              <div className="text-sm text-muted">{t.loading}</div>
            ) : versions.length === 0 ? (
              <div className="text-sm text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">
                {t.none}
              </div>
            ) : (
              <div className="border border-rule rounded-lg divide-y divide-rule">
                {versions.map((v) => {
                  const scheduled = new Date(v.effective_from).getTime() > now;
                  const isCurrent = v.version === currentVersion;
                  return (
                    <div key={v.id} className="flex items-center justify-between px-4 py-3 gap-4">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg flex items-center gap-2">
                          <span className="font-mono">{v.version}</span>
                          {isCurrent && <Badge color="green" pill>{t.current}</Badge>}
                          {scheduled && <Badge color="blue" pill>{t.scheduled}</Badge>}
                        </div>
                        <div className="text-xs text-muted">
                          {t.versionLine(fmtDate(v.effective_from), (v.languages || []).join(', ') || '—', fmtDate(v.created_at))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Publish new */}
          <div className="bg-surface rounded-lg shadow border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-4">{t.publishNew}</h2>

            <div className="flex flex-wrap gap-4 mb-4">
              <div className="flex-1 min-w-[12rem]">
                <label className="block text-sm font-medium text-body mb-1">{t.version}</label>
                <input
                  className={inputCls}
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder={t.versionPlaceholder}
                />
              </div>
              <div className="flex-1 min-w-[12rem]">
                <label className="block text-sm font-medium text-body mb-1">{t.effectiveFrom}</label>
                <input
                  type="datetime-local"
                  className={inputCls}
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                />
                <p className="text-xs text-muted mt-1">{t.effectiveHint}</p>
              </div>
            </div>

            <label className="block text-sm font-medium text-body mb-2">{t.noticeText}</label>
            <div className="space-y-4">
              {langs.map((l, i) => (
                <div key={i} className="border border-rule rounded-lg p-3">
                  <div className="flex flex-wrap items-center gap-3 mb-2">
                    <input
                      className="w-28 px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm"
                      value={l.lang}
                      onChange={(e) => setLangCode(i, e.target.value)}
                      placeholder={t.langPlaceholder}
                      aria-label={t.langAria}
                    />
                    <label className="px-3 py-2 text-sm font-medium text-accent-text bg-accent-wash rounded-lg hover:bg-accent-wash cursor-pointer">
                      {l.filename ? t.replace(l.filename) : t.upload}
                      <input type="file" accept=".md,.markdown,text/markdown" className="hidden" onChange={(e) => onPickFile(i, e)} />
                    </label>
                    {langs.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeLang(i)}
                        className="ml-auto text-sm text-danger-text hover:underline"
                      >
                        {t.remove}
                      </button>
                    )}
                  </div>
                  <textarea
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg focus:ring-2 focus:ring-accent-line focus:border-accent-line text-sm font-mono"
                    rows={8}
                    value={l.text}
                    onChange={(e) => setLangText(i, e.target.value)}
                    placeholder={t.textPlaceholder}
                  />
                </div>
              ))}
            </div>

            <div className="mt-3 flex items-center gap-4">
              <button type="button" onClick={addLang} className="text-sm text-accent-text hover:underline">
                {t.addLang}
              </button>
            </div>

          </div>
        </ScrollArea>

        {/* The page's one write action — pinned rather than left at the foot of
            the publish form, which sits below a version history of any length. */}
        <PageActions>
          <Button
            onClick={onClickPublish}
            disabled={publishing || !!validationError}
            loading={publishing}
            loadingLabel={t.publishing}
          >
            {t.publishVersion}
          </Button>
          {validationError && <span className="text-sm text-muted">{validationError}</span>}
        </PageActions>

        <ConfirmDialog
          open={showConfirm}
          title={t.confirmTitle}
          message={effectiveFrom ? t.confirmScheduled(version.trim()) : t.confirmNow(version.trim())}
          confirmLabel={t.confirmLabel}
          variant="danger"
          onConfirm={doPublish}
          onCancel={() => setShowConfirm(false)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

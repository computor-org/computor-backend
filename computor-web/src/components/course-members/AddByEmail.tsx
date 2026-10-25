'use client';

import { useState } from 'react';
import ErrorBanner from '@/src/components/ErrorBanner';
import { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import Button from '@/src/components/ui/Button';
import RoleSelect from '@/src/components/course-members/RoleSelect';
import { CourseMemberImportClient } from '@/src/generated/clients/CourseMemberImportClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import type { CourseRoleId } from '@/src/utils/courseRoles';

const importClient = new CourseMemberImportClient();

const COPY = {
  de: {
    addedProvisioning: (email: string) => `${email} wurde hinzugefügt, die Repository-Einrichtung wurde gestartet.`,
    added: (email: string) => `${email} wurde zum Kurs hinzugefügt.`,
    importFailed: 'Import fehlgeschlagen.',
    intro: 'Fügt die Person mit dieser E-Mail-Adresse hinzu und legt das Konto an, falls es noch nicht existiert. Nutze das für Personen, die noch nicht im System sind.',
    email: 'E-Mail',
    givenName: 'Vorname',
    familyName: 'Nachname',
    role: 'Rolle',
    group: 'Gruppe',
    groupHint: 'Optional. Wird angelegt, falls sie noch nicht existiert.',
    adding: 'Wird hinzugefügt …',
    submit: 'Per E-Mail hinzufügen',
  },
  en: {
    addedProvisioning: (email: string) => `${email} added — repository provisioning started.`,
    added: (email: string) => `${email} added to the course.`,
    importFailed: 'Import failed.',
    intro: 'Adds the user with this email, creating the account if it does not exist yet. Use this for people not yet in the system.',
    email: 'Email',
    givenName: 'Given name',
    familyName: 'Family name',
    role: 'Role',
    group: 'Group',
    groupHint: 'Optional. Created if it does not exist yet.',
    adding: 'Adding…',
    submit: 'Add by email',
  },
};

export default function AddByEmail({
  courseId,
  roleOptions,
  defaultRole,
}: {
  courseId: string;
  roleOptions: CourseRoleId[];
  defaultRole: string;
}) {
  const t = COPY[useUiLanguage()];
  const [email, setEmail] = useState('');
  const [givenName, setGivenName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [emailRole, setEmailRole] = useState<string>(defaultRole);
  const [groupTitle, setGroupTitle] = useState('');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);

  async function importByEmail() {
    setImporting(true);
    setImportError(null);
    setImportMsg(null);
    try {
      const res = await importClient.importMemberCourseMemberImportCourseIdPost({
        courseId,
        body: {
          email: email.trim(),
          given_name: givenName.trim() || undefined,
          family_name: familyName.trim() || undefined,
          course_role_id: emailRole,
          course_group_title: groupTitle.trim() || undefined,
          create_missing_group: true,
        },
      });
      if (res.success) {
        setImportMsg(
          res.workflow_id
            ? t.addedProvisioning(email.trim())
            : t.added(email.trim()),
        );
        setEmail('');
        setGivenName('');
        setFamilyName('');
        setGroupTitle('');
      } else {
        setImportError(res.message || t.importFailed);
      }
    } catch (e) {
      setImportError(e instanceof Error ? e.message : t.importFailed);
    } finally {
      setImporting(false);
    }
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        importByEmail();
      }}
      className="bg-surface border border-rule rounded-lg p-6 space-y-4 max-w-lg"
    >
      <p className="text-sm text-muted">
        {t.intro}
      </p>

      <ErrorBanner>{importError}</ErrorBanner>
      {importMsg && (
        <div className="p-3 bg-success-wash border border-success-line rounded text-sm text-success-text">{importMsg}</div>
      )}

      <Field label={t.email} required>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputCls}
          placeholder="person@example.org"
        />
      </Field>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t.givenName}>
          <input value={givenName} onChange={(e) => setGivenName(e.target.value)} className={inputCls} />
        </Field>
        <Field label={t.familyName}>
          <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} className={inputCls} />
        </Field>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t.role} required>
          <RoleSelect
            value={emailRole}
            onChange={(value) => setEmailRole(value)}
            options={roleOptions}
            className={inputCls}
          />
        </Field>
        <Field label={t.group} hint={t.groupHint}>
          <input value={groupTitle} onChange={(e) => setGroupTitle(e.target.value)} className={inputCls} />
        </Field>
      </div>

      <Button
        type="submit"
        disabled={!email.trim()}
        loading={importing}
        loadingLabel={t.adding}
      >
        {t.submit}
      </Button>
    </form>
  );
}

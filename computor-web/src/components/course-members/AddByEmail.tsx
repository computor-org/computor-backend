'use client';

import { useState } from 'react';
import ErrorBanner from '@/src/components/ErrorBanner';
import { Field, inputCls } from '@/src/components/FormPanel';
import RoleSelect from '@/src/components/course-members/RoleSelect';
import { CourseMemberImportClient } from '@/src/generated/clients/CourseMemberImportClient';
import type { CourseRoleId } from '@/src/utils/courseRoles';

const importClient = new CourseMemberImportClient();

export default function AddByEmail({
  courseId,
  roleOptions,
  defaultRole,
}: {
  courseId: string;
  roleOptions: CourseRoleId[];
  defaultRole: string;
}) {
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
            ? `${email.trim()} added — repository provisioning started.`
            : `${email.trim()} added to the course.`,
        );
        setEmail('');
        setGivenName('');
        setFamilyName('');
        setGroupTitle('');
      } else {
        setImportError(res.message || 'Import failed.');
      }
    } catch (e) {
      setImportError(e instanceof Error ? e.message : 'Import failed.');
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
      className="bg-white border border-gray-200 rounded-lg p-6 space-y-4 max-w-lg"
    >
      <p className="text-sm text-gray-500">
        Adds the user with this email, creating the account if it does not exist yet. Use this for people
        not yet in the system.
      </p>

      <ErrorBanner>{importError}</ErrorBanner>
      {importMsg && (
        <div className="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">{importMsg}</div>
      )}

      <Field label="Email" required>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputCls}
          placeholder="person@example.org"
        />
      </Field>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Given name">
          <input value={givenName} onChange={(e) => setGivenName(e.target.value)} className={inputCls} />
        </Field>
        <Field label="Family name">
          <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} className={inputCls} />
        </Field>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Role" required>
          <RoleSelect
            value={emailRole}
            onChange={(value) => setEmailRole(value)}
            options={roleOptions}
            className={inputCls}
          />
        </Field>
        <Field label="Group" hint="Optional. Created if it does not exist yet.">
          <input value={groupTitle} onChange={(e) => setGroupTitle(e.target.value)} className={inputCls} />
        </Field>
      </div>

      <button
        type="submit"
        disabled={importing || !email.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {importing ? 'Adding…' : 'Add by email'}
      </button>
    </form>
  );
}

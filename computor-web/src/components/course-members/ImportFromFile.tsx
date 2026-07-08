'use client';

import { useState } from 'react';
import ErrorBanner from '@/src/components/ErrorBanner';
import RoleSelect from '@/src/components/course-members/RoleSelect';
import { CourseMemberImportClient } from '@/src/generated/clients/CourseMemberImportClient';
import { fileToBase64 } from '@/src/utils/file';
import type { CourseMemberImportRow } from 'types/generated';
import type { CourseRoleId } from '@/src/utils/courseRoles';

const importClient = new CourseMemberImportClient();

export default function ImportFromFile({
  courseId,
  roleOptions,
  defaultRole,
}: {
  courseId: string;
  roleOptions: CourseRoleId[];
  defaultRole: string;
}) {
  const [fileParsing, setFileParsing] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [parsedRows, setParsedRows] = useState<CourseMemberImportRow[]>([]);
  const [rowSel, setRowSel] = useState<Record<number, boolean>>({});
  const [rowRoleFile, setRowRoleFile] = useState<Record<number, string>>({});
  const [rowGroupFile, setRowGroupFile] = useState<Record<number, string>>({});
  const [fileResults, setFileResults] = useState<Record<number, { ok: boolean; message?: string }>>({});
  const [fileImporting, setFileImporting] = useState(false);
  const [fileSummary, setFileSummary] = useState<string | null>(null);

  async function handleFile(file: File) {
    setFileError(null);
    setFileSummary(null);
    setParsedRows([]);
    setFileResults({});
    setFileParsing(true);
    try {
      const res = await importClient.parseMemberFileCourseMemberImportParseCourseIdPost({
        courseId,
        body: { filename: file.name, content_base64: await fileToBase64(file) },
      });
      const rows = res.rows ?? [];
      const sel: Record<number, boolean> = {};
      const roles: Record<number, string> = {};
      const groups: Record<number, string> = {};
      rows.forEach((r, i) => {
        sel[i] = true;
        roles[i] =
          r.course_role_id && roleOptions.includes(r.course_role_id as never)
            ? r.course_role_id
            : defaultRole;
        groups[i] = r.course_group_title ?? '';
      });
      setParsedRows(rows);
      setRowSel(sel);
      setRowRoleFile(roles);
      setRowGroupFile(groups);
      if (!rows.length) setFileError('No members with an email address were found in the file.');
    } catch (e) {
      setFileError(e instanceof Error ? e.message : 'Failed to parse file.');
    } finally {
      setFileParsing(false);
    }
  }

  async function importParsed() {
    setFileImporting(true);
    setFileSummary(null);
    const results: Record<number, { ok: boolean; message?: string }> = {};
    let ok = 0;
    let fail = 0;
    for (let i = 0; i < parsedRows.length; i++) {
      if (!rowSel[i]) continue;
      const r = parsedRows[i];
      try {
        const res = await importClient.importMemberCourseMemberImportCourseIdPost({
          courseId,
          body: {
            email: r.email,
            given_name: r.given_name ?? undefined,
            family_name: r.family_name ?? undefined,
            course_role_id: rowRoleFile[i] ?? defaultRole,
            course_group_title: rowGroupFile[i]?.trim() || undefined,
            create_missing_group: true,
          },
        });
        if (res.success) {
          results[i] = { ok: true };
          ok++;
        } else {
          results[i] = { ok: false, message: res.message ?? 'Failed' };
          fail++;
        }
      } catch (e) {
        results[i] = { ok: false, message: e instanceof Error ? e.message : 'Failed' };
        fail++;
      }
      setFileResults({ ...results });
    }
    setFileImporting(false);
    setFileSummary(`Imported ${ok}${fail ? `, ${fail} failed` : ''}.`);
  }

  const selectedFileCount = parsedRows.filter((_, i) => rowSel[i]).length;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Upload a CSV, JSON, Excel (.xlsx) or Excel-XML student list. Review and adjust the rows, then
        import the ones you want. Existing members are updated rather than duplicated.
      </p>
      <input
        type="file"
        accept=".csv,.tsv,.txt,.json,.xlsx,.xls,.xml"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          e.target.value = '';
        }}
        className="block text-sm text-gray-500 file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-blue-700"
      />

      <ErrorBanner>{fileError}</ErrorBanner>

      {fileParsing ? (
        <div className="text-gray-500 py-8 text-center">Parsing file…</div>
      ) : parsedRows.length > 0 ? (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 w-8" />
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Group</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {parsedRows.map((r, i) => {
                  const res = fileResults[i];
                  const name = `${r.given_name ?? ''} ${r.family_name ?? ''}`.trim() || r.email;
                  return (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-3 py-3">
                        <input
                          type="checkbox"
                          checked={!!rowSel[i]}
                          onChange={(e) => setRowSel((p) => ({ ...p, [i]: e.target.checked }))}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900 text-sm">{name}</div>
                        <div className="text-xs text-gray-500">{r.email}</div>
                      </td>
                      <td className="px-4 py-3">
                        <RoleSelect
                          value={rowRoleFile[i] ?? defaultRole}
                          onChange={(value) => setRowRoleFile((p) => ({ ...p, [i]: value }))}
                          options={roleOptions}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          value={rowGroupFile[i] ?? ''}
                          onChange={(e) => setRowGroupFile((p) => ({ ...p, [i]: e.target.value }))}
                          placeholder="—"
                          className="w-32 px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {res ? (
                          res.ok ? (
                            <span className="text-green-700">Added ✓</span>
                          ) : (
                            <span className="text-red-600" title={res.message}>Failed</span>
                          )
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={importParsed}
              disabled={fileImporting || selectedFileCount === 0}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {fileImporting ? 'Importing…' : `Import ${selectedFileCount} selected`}
            </button>
            {fileSummary && <span className="text-sm text-gray-600">{fileSummary}</span>}
          </div>
        </>
      ) : null}
    </div>
  );
}

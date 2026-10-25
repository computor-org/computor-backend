'use client';

import { useState } from 'react';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import ErrorBanner from '@/src/components/ErrorBanner';
import RoleSelect from '@/src/components/course-members/RoleSelect';
import { CourseMemberImportClient } from '@/src/generated/clients/CourseMemberImportClient';
import { fileToBase64 } from '@/src/utils/file';
import type { CourseMemberImportRow } from 'types/generated';
import type { CourseRoleId } from '@/src/utils/courseRoles';
import { Table, Tbody, Th } from '@/src/components/ui/Table';
import Button from '@/src/components/ui/Button';

const importClient = new CourseMemberImportClient();

const COPY = {
  de: {
    noRows: 'In der Datei wurden keine Mitglieder mit E-Mail-Adresse gefunden.',
    parseFailed: 'Die Datei konnte nicht gelesen werden.',
    failed: 'Fehlgeschlagen',
    summary: (ok: number, fail: number) => `${ok} importiert${fail ? `, ${fail} fehlgeschlagen` : ''}.`,
    intro: 'Lade eine Studierendenliste als CSV, JSON, Excel (.xlsx) oder Excel-XML hoch. Prüfe und passe die Zeilen an und importiere dann die gewünschten. Bestehende Mitglieder werden aktualisiert statt doppelt angelegt.',
    parsing: 'Datei wird gelesen …',
    user: 'Nutzer',
    role: 'Rolle',
    group: 'Gruppe',
    status: 'Status',
    added: 'Hinzugefügt ✓',
    importing: 'Wird importiert …',
    importSelected: (n: number) => `${n} Ausgewählte importieren`,
  },
  en: {
    noRows: 'No members with an email address were found in the file.',
    parseFailed: 'Failed to parse file.',
    failed: 'Failed',
    summary: (ok: number, fail: number) => `Imported ${ok}${fail ? `, ${fail} failed` : ''}.`,
    intro: 'Upload a CSV, JSON, Excel (.xlsx) or Excel-XML student list. Review and adjust the rows, then import the ones you want. Existing members are updated rather than duplicated.',
    parsing: 'Parsing file…',
    user: 'User',
    role: 'Role',
    group: 'Group',
    status: 'Status',
    added: 'Added ✓',
    importing: 'Importing…',
    importSelected: (n: number) => `Import ${n} selected`,
  },
};

export default function ImportFromFile({
  courseId,
  roleOptions,
  defaultRole,
}: {
  courseId: string;
  roleOptions: CourseRoleId[];
  defaultRole: string;
}) {
  const t = COPY[useUiLanguage()];
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
      if (!rows.length) setFileError(t.noRows);
    } catch (e) {
      setFileError(e instanceof Error ? e.message : t.parseFailed);
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
          results[i] = { ok: false, message: res.message ?? t.failed };
          fail++;
        }
      } catch (e) {
        results[i] = { ok: false, message: e instanceof Error ? e.message : t.failed };
        fail++;
      }
      setFileResults({ ...results });
    }
    setFileImporting(false);
    setFileSummary(t.summary(ok, fail));
  }

  const selectedFileCount = parsedRows.filter((_, i) => rowSel[i]).length;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        {t.intro}
      </p>
      <input
        type="file"
        accept=".csv,.tsv,.txt,.json,.xlsx,.xls,.xml"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          e.target.value = '';
        }}
        className="block text-sm text-muted file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-on-accent hover:file:bg-accent-hover"
      />

      <ErrorBanner>{fileError}</ErrorBanner>

      {fileParsing ? (
        <div className="text-muted py-8 text-center">{t.parsing}</div>
      ) : parsedRows.length > 0 ? (
        <>
          <div className="bg-surface border border-rule rounded-lg overflow-hidden">
            <Table>
              <thead className="bg-canvas">
                <tr>
                  <th className="px-3 py-3 w-8" />
                  <Th>{t.user}</Th>
                  <Th>{t.role}</Th>
                  <Th>{t.group}</Th>
                  <Th>{t.status}</Th>
                </tr>
              </thead>
              <Tbody>
                {parsedRows.map((r, i) => {
                  const res = fileResults[i];
                  const name = `${r.given_name ?? ''} ${r.family_name ?? ''}`.trim() || r.email;
                  return (
                    <tr key={i} className="hover:bg-canvas">
                      <td className="px-3 py-3">
                        <input
                          type="checkbox"
                          checked={!!rowSel[i]}
                          onChange={(e) => setRowSel((p) => ({ ...p, [i]: e.target.checked }))}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-fg text-sm">{name}</div>
                        <div className="text-xs text-muted">{r.email}</div>
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
                          className="w-32 px-2 py-1 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
                        />
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {res ? (
                          res.ok ? (
                            <span className="text-success-text">{t.added}</span>
                          ) : (
                            <span className="text-danger-text" title={res.message}>{t.failed}</span>
                          )
                        ) : (
                          <span className="text-subtle">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </Tbody>
            </Table>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={importParsed}
              disabled={selectedFileCount === 0}
              loading={fileImporting}
              loadingLabel={t.importing}
            >
              {t.importSelected(selectedFileCount)}
            </Button>
            {fileSummary && <span className="text-sm text-muted">{fileSummary}</span>}
          </div>
        </>
      ) : null}
    </div>
  );
}

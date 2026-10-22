import JSZip from 'jszip';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';

/**
 * An assignment's instructions in the learner's reading language.
 *
 * The released description archive holds `README.md` plus one file per
 * translation (`README_de.md`, `README_en.md`). The reading language is the
 * learner's explicit profile language, else the course language, else English;
 * the same rule as the VS Code extension and the public reader.
 */

export function resolveContentLanguage(userLanguage?: string | null, courseLanguage?: string | null): string {
  return userLanguage?.trim().toLowerCase() || courseLanguage?.trim().toLowerCase() || 'en';
}

const DESCRIPTION_FILE = /^(?:README|index)(?:_([a-z]{2}))?\.md$/i;

/** The preferred language, then English, then the default document, then any. */
export function pickDescriptionFile(files: string[], preferred: string): string | undefined {
  const candidates = files.flatMap(file => {
    const match = DESCRIPTION_FILE.exec(file);
    return match ? [{ file, language: match[1]?.toLowerCase() }] : [];
  });
  const inLanguage = (language: string) => candidates.find(entry => entry.language === language)?.file;
  return inLanguage(preferred.toLowerCase())
    ?? inLanguage('en')
    ?? candidates.find(entry => entry.language === undefined)?.file
    ?? candidates[0]?.file;
}

const HEADING = /^#\s+(.+?)\s*#*\s*$/m;

export function descriptionHeading(markdown?: string | null): string | undefined {
  return markdown?.match(HEADING)?.[1] || undefined;
}

/** A heading as plain text for a page title: inline math and emphasis markers removed. */
export function plainHeading(heading: string): string {
  return heading.replace(/\$\\pi\$/g, 'π').replace(/\$-\$/g, '–').replace(/[*$]/g, '').trim();
}

// Link reference definitions, HTML comments and blank lines render as nothing.
const INVISIBLE_LINE = /^\s*(?:\[[^\]]+\]:\s+\S.*|<!--.*-->)?\s*$/;

/** Drop the heading the page already shows as its title; keep a later one. */
export function withoutLeadingHeading(markdown: string): string {
  const lines = markdown.split(/\r?\n/);
  for (let index = 0; index < lines.length; index++) {
    if (/^#\s+/.test(lines[index])) {
      lines.splice(index, 1);
      return lines.join('\n');
    }
    if (!INVISIBLE_LINE.test(lines[index])) return markdown;
  }
  return markdown;
}

const UNIT_TITLE = /^(?:Week|Woche)\s+(\d+)$/i;

/** "Week N" and "Woche N" follow the reading language; other titles stay. */
export function localizedUnitTitle(title: string, language: string): string {
  const unit = title.trim().match(UNIT_TITLE);
  if (!unit) return title;
  return language === 'de' ? `Woche ${unit[1]}` : language === 'en' ? `Week ${unit[1]}` : title;
}

export interface StudentDescription {
  markdown: string;
  /** `mediaFiles/...` path -> data URL, for images the description shows. */
  images: Record<string, string>;
}

const IMAGE_TYPES: Record<string, string> = {
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp',
};

/** Read the description out of a released archive; only top-level files and mediaFiles. */
export async function readStudentDescription(archive: ArrayBuffer, language: string): Promise<StudentDescription | null> {
  const zip = await JSZip.loadAsync(archive);
  const safe = Object.values(zip.files).filter(file => {
    const original = (file as JSZip.JSZipObject & { unsafeOriginalName?: string }).unsafeOriginalName ?? file.name;
    return !file.dir && original === file.name && !original.includes('\\')
      && original.split('/').every(part => part && part !== '.' && part !== '..');
  });
  const chosen = pickDescriptionFile(safe.filter(file => !file.name.includes('/')).map(file => file.name), language);
  if (!chosen) return null;
  const markdown = await zip.file(chosen)!.async('string');
  const images: Record<string, string> = {};
  for (const file of safe) {
    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!file.name.startsWith('mediaFiles/') || !IMAGE_TYPES[extension]) continue;
    images[file.name] = `data:${IMAGE_TYPES[extension]};base64,${await file.async('base64')}`;
  }
  return { markdown, images };
}

/** The released description of an assignment, or null when it has none. */
export async function fetchStudentDescription(courseContentId: string, language: string): Promise<StudentDescription | null> {
  const response = await apiFetch(
    `${API_BASE_URL}/students/course-contents/${encodeURIComponent(courseContentId)}/description`,
  );
  if (!response.ok) return null;
  return readStudentDescription(await response.arrayBuffer(), language);
}

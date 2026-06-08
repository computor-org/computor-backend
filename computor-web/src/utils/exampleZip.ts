import JSZip from 'jszip';

/**
 * Client-side discovery of one-or-many examples inside an uploaded .zip.
 *
 * The backend's POST /examples/upload takes a single example as a flat
 * { filename: content } map that must contain a root `meta.yaml`. To support
 * "a zip of one example" *or* "a zip of several examples", we unzip here and
 * discover example roots at most one directory deep (after stripping a common
 * wrapper folder, which is what zipping a folder produces):
 *   - `meta.yaml` at the (stripped) root            -> a single example
 *   - `<dir>/meta.yaml` for each top-level <dir>     -> several examples
 *
 * Encoding contract (mirrors api/examples.py): `meta.yaml` is parsed raw, so it
 * MUST be sent as plain UTF-8 text; every other file is sent base64-encoded,
 * which `_extract_file_bytes` decodes for both binary and text extensions.
 */
export interface DiscoveredExample {
  directory: string;
  /** relative path -> content (meta.yaml as text, others base64) */
  files: Record<string, string>;
  fileCount: number;
}

const DIR_OK = /^[a-zA-Z0-9._-]+$/;

function sanitizeDir(name: string): string {
  const cleaned = name.replace(/[^a-zA-Z0-9._-]+/g, '_').replace(/^[_.]+|_+$/g, '');
  return cleaned && DIR_OK.test(cleaned) ? cleaned : 'example';
}

/** Longest shared leading directory segments across all paths. */
function commonDirPrefix(paths: string[]): string[] {
  if (paths.length === 0) return [];
  const split = paths.map((p) => p.split('/').slice(0, -1)); // drop filename
  let prefix = split[0];
  for (const segs of split.slice(1)) {
    let i = 0;
    while (i < prefix.length && i < segs.length && prefix[i] === segs[i]) i++;
    prefix = prefix.slice(0, i);
    if (prefix.length === 0) break;
  }
  return prefix;
}

async function readContent(entry: JSZip.JSZipObject, relPath: string): Promise<string> {
  // Root meta.yaml must be raw text (the server parses it directly); the rest
  // ride through base64 so binary files survive the JSON transport intact.
  return relPath === 'meta.yaml' ? entry.async('string') : entry.async('base64');
}

export async function discoverExamplesInZip(file: File): Promise<DiscoveredExample[]> {
  const zip = await JSZip.loadAsync(file);
  const entries = Object.values(zip.files).filter((f) => !f.dir);
  if (entries.length === 0) throw new Error('The zip is empty.');

  const prefix = commonDirPrefix(entries.map((e) => e.name));
  const strip = prefix.length;
  // map stripped-relative-path -> zip entry
  const rel = new Map<string, JSZip.JSZipObject>();
  for (const e of entries) {
    const parts = e.name.split('/').slice(strip);
    if (parts.length === 0 || parts[parts.length - 1] === '') continue;
    rel.set(parts.join('/'), e);
  }

  const wrapperName = prefix.length ? prefix[prefix.length - 1] : file.name.replace(/\.zip$/i, '');

  // Case 1: single example — meta.yaml at the stripped root.
  if (rel.has('meta.yaml')) {
    const files: Record<string, string> = {};
    for (const [p, entry] of rel) files[p] = await readContent(entry, p);
    return [{ directory: sanitizeDir(wrapperName), files, fileCount: Object.keys(files).length }];
  }

  // Case 2: several examples — each top-level dir that has a meta.yaml.
  const byDir = new Map<string, Map<string, JSZip.JSZipObject>>();
  for (const [p, entry] of rel) {
    const slash = p.indexOf('/');
    if (slash < 0) continue; // loose file at root with no root meta.yaml — ignore
    const dir = p.slice(0, slash);
    const sub = p.slice(slash + 1);
    if (!byDir.has(dir)) byDir.set(dir, new Map());
    byDir.get(dir)!.set(sub, entry);
  }

  const result: DiscoveredExample[] = [];
  for (const [dir, subFiles] of byDir) {
    if (!subFiles.has('meta.yaml')) continue; // not an example root
    const files: Record<string, string> = {};
    for (const [p, entry] of subFiles) files[p] = await readContent(entry, p);
    result.push({ directory: sanitizeDir(dir), files, fileCount: Object.keys(files).length });
  }

  if (result.length === 0) {
    throw new Error('No meta.yaml found at the zip root or one directory deep.');
  }
  return result.sort((a, b) => a.directory.localeCompare(b.directory));
}

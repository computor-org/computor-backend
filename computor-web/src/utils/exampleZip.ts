import JSZip from 'jszip';
import { load as parseYaml } from 'js-yaml';

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

/**
 * Pull the slug and (test) dependency slugs out of an example's meta.yaml.
 *
 * Mirrors the CLI (`_read_meta_and_dependencies`): the slug falls back to the
 * directory name with `-`/`_` mapped to dots; `testDependencies` may live at the
 * root or under `properties`, and each entry is either a bare slug string or an
 * object with a `slug` field (a missing version means "latest").
 */
function metaSlugAndDeps(dir: string, metaText: string | undefined): { slug: string; deps: string[] } {
  let slug = dir.replace(/[-_]/g, '.');
  const deps: string[] = [];
  if (metaText) {
    let meta: unknown;
    try {
      meta = parseYaml(metaText);
    } catch {
      meta = undefined;
    }
    if (meta && typeof meta === 'object') {
      const m = meta as Record<string, any>;
      if (typeof m.slug === 'string' && m.slug) slug = m.slug;
      let td = m.properties && typeof m.properties === 'object' ? m.properties.testDependencies : undefined;
      if (td == null) td = m.testDependencies;
      if (Array.isArray(td)) {
        for (const item of td) {
          if (typeof item === 'string') deps.push(item);
          else if (item && typeof item === 'object' && typeof item.slug === 'string') deps.push(item.slug);
        }
      }
    }
  }
  return { slug, deps };
}

/**
 * Topologically sort discovered examples so an example another depends on is
 * uploaded first (the backend rejects an upload whose testDependencies aren't
 * yet in the repository). Only dependencies present in this batch are
 * considered; ties and cycles fall back to a stable alphabetical order.
 * Mirrors the CLI's `_toposort_by_dependencies`.
 */
function sortByDependencies(examples: DiscoveredExample[]): DiscoveredExample[] {
  if (examples.length < 2) return examples;

  const nodes = examples.map((e) => ({ e, ...metaSlugAndDeps(e.directory, e.files['meta.yaml']) }));
  const bySlug = new Map<string, (typeof nodes)[number]>();
  for (const n of nodes) bySlug.set(n.slug, n); // last wins, like the CLI

  const indeg = new Map<string, number>();
  const rev = new Map<string, Set<string>>(); // dep slug -> dependent slugs
  for (const n of nodes) {
    rev.set(n.slug, rev.get(n.slug) ?? new Set());
    const inBatch = n.deps.filter((d) => bySlug.has(d) && d !== n.slug);
    indeg.set(n.slug, inBatch.length);
    for (const d of inBatch) {
      rev.set(d, rev.get(d) ?? new Set());
      rev.get(d)!.add(n.slug);
    }
  }

  const cmp = (a: string, b: string) => bySlug.get(a)!.e.directory.localeCompare(bySlug.get(b)!.e.directory);
  const queue = [...bySlug.keys()].filter((s) => (indeg.get(s) ?? 0) === 0).sort(cmp);
  const order: string[] = [];
  while (queue.length) {
    const s = queue.shift()!;
    order.push(s);
    for (const nx of [...(rev.get(s) ?? [])].sort(cmp)) {
      indeg.set(nx, (indeg.get(nx) ?? 0) - 1);
      if ((indeg.get(nx) ?? 0) === 0) {
        queue.push(nx);
        queue.sort(cmp);
      }
    }
  }
  // Cycle (or unreachable) fallback: append remaining slugs in stable order.
  if (order.length < bySlug.size) {
    order.push(...[...bySlug.keys()].filter((s) => !order.includes(s)).sort(cmp));
  }

  const seen = new Set<DiscoveredExample>();
  const result: DiscoveredExample[] = [];
  for (const s of order) {
    const node = bySlug.get(s);
    if (node && !seen.has(node.e)) {
      result.push(node.e);
      seen.add(node.e);
    }
  }
  // Any examples whose slug collided and weren't emitted (kept stable).
  for (const n of nodes) if (!seen.has(n.e)) result.push(n.e);
  return result;
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
  // Upload dependencies before the examples that depend on them.
  return sortByDependencies(result);
}

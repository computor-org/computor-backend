// Compile only reviewed public descriptions and raster media. No runtime fetch.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import yaml from 'js-yaml';

const COURSES = ['python-beginner', 'python-intermediate', 'python-advanced'];
const SEGMENT = /^[a-zA-Z0-9_-]+$/;
const MAX_TEXT = 512 * 1024;
const MAX_MEDIA = 8 * 1024 * 1024;

function readInside(root, relative, limit) {
  const file = path.resolve(root, relative);
  const real = fs.realpathSync(file);
  if (real !== file || !file.startsWith(root + path.sep)) throw Error('Unsafe source path');
  const stat = fs.statSync(file);
  if (!stat.isFile() || stat.size > limit) throw Error('Invalid source file size');
  return fs.readFileSync(file);
}

function readYaml(root, relative) {
  return yaml.load(readInside(root, relative, MAX_TEXT).toString('utf8'), { schema: yaml.JSON_SCHEMA });
}

function rasterMatches(name, bytes) {
  const ext = path.extname(name).toLowerCase();
  if (ext === '.png') return bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
  if (['.jpg', '.jpeg'].includes(ext)) return bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  if (ext === '.gif') return ['GIF87a', 'GIF89a'].includes(bytes.subarray(0, 6).toString());
  if (ext === '.webp') return bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP';
  return false;
}

export function buildPublicLearning(source, destination, revision) {
  if (!/^[0-9a-f]{40}$/.test(revision)) throw Error('An exact source commit is required');
  source = fs.realpathSync(source);
  fs.mkdirSync(destination, { recursive: true });
  const catalog = [];
  for (const slug of COURSES) {
    const manifest = readYaml(source, `courses/${slug}.yaml`);
    if (manifest.visible === false || manifest.archived_at) throw Error('Course is not published');
    const contents = [];
    const materials = {};
    function visit(nodes, ancestors = []) {
      for (const node of [...nodes].sort((a, b) => Number(a.position ?? 0) - Number(b.position ?? 0))) {
        if (node.visible === false || node.archived_at || node.released === false) continue;
        if (!SEGMENT.test(node.path)) throw Error('Invalid course path');
        const parts = [...ancestors, node.path];
        const id = parts.join('.');
        const type = manifest.content_types.find(t => t.slug === node.content_type);
        if (!type) throw Error('Unknown content type');
        const assignment = type.kind === 'assignment';
        let title = node.title ?? (type.kind === 'unit' ? `Week ${node.position}` : node.path.replaceAll('_', ' '));
        let description = node.description ?? null;
        const variants = {};
        const media = new Set();
        if (node.example_identifier) {
          if (!/^[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*$/.test(node.example_identifier)) throw Error('Invalid example identifier');
          const example = `examples/python/${node.example_identifier}`;
          const meta = readYaml(source, `${example}/meta.yaml`);
          title = meta.title;
          description = meta.description ?? null;
          for (const file of fs.readdirSync(path.join(source, example, 'content')).sort()) {
            const match = /^(?:index|README)(?:_(de|en))?\.md$/i.exec(file);
            if (!match) continue;
            const lang = (match[1] ?? meta.language ?? 'de').toLowerCase();
            if (!['de', 'en'].includes(lang)) continue;
            const markdown = readInside(source, `${example}/content/${file}`, MAX_TEXT).toString('utf8');
            if (!variants[lang] || file.startsWith('index')) variants[lang] = markdown;
          }
          if (!Object.keys(variants).length) throw Error(`Missing public description: ${id}`);
          // Include referenced raster images only. SVG/HTML/scripts are never served.
          for (const markdown of Object.values(variants)) {
            for (const match of markdown.matchAll(/mediaFiles\/([a-zA-Z0-9_./ -]+\.(?:png|jpe?g|gif|webp))\b/gi)) {
              const name = match[1];
              if (name.split('/').some(part => !part || part === '.' || part === '..')) throw Error('Unsafe media path');
              if (!fs.existsSync(path.join(source, example, 'content/mediaFiles', name))) {
                console.warn(`Public mirror has no image for ${slug}/${id}/${name}`);
                continue;
              }
              const bytes = readInside(source, `${example}/content/mediaFiles/${name}`, MAX_MEDIA);
              if (!rasterMatches(name, bytes)) throw Error('Media signature does not match its extension');
              const target = path.join(destination, 'media', slug, id, name);
              fs.mkdirSync(path.dirname(target), { recursive: true });
              fs.writeFileSync(target, bytes);
              media.add(name);
            }
          }
        }
        contents.push({ id, title, description, path: id, parent_path: ancestors.join('.') || null,
          depth: ancestors.length, position: Number(node.position ?? 0), kind: type.kind,
          type_title: type.title, is_submittable: assignment });
        materials[id] = { id, course_id: slug, title, description, path: id, kind: type.kind,
          is_submittable: assignment, markdown_variants: variants,
          asset_base_url: `/learning/media/${slug}/${id}/`, media_files: [...media].sort() };
        visit(node.contents ?? [], parts);
      }
    }
    visit(manifest.contents);
    const welcome = contents.find(c => ['welcome', 'start_here', 'introduction'].includes(c.id));
    const course = { id: slug, title: manifest.name, description: manifest.description,
      language_code: 'de', contents, materials, welcome_content_id: welcome?.id ?? null,
      first_exercise_id: contents.find(c => c.is_submittable)?.id ?? null,
      exercise_count: contents.filter(c => c.is_submittable).length,
      unit_count: contents.filter(c => !c.is_submittable).length,
      source_commit: revision };
    fs.mkdirSync(path.join(destination, 'courses'), { recursive: true });
    fs.writeFileSync(path.join(destination, 'courses', `${slug}.json`), JSON.stringify(course));
    catalog.push({ id: slug, title: course.title, description: course.description,
      language_code: 'de', exercise_count: course.exercise_count, unit_count: course.unit_count });
  }
  fs.writeFileSync(path.join(destination, 'catalog.json'), JSON.stringify(catalog));
  fs.writeFileSync(path.join(destination, 'source.json'), JSON.stringify({
    repository: 'https://github.com/computor-org/data-science-python', commit: revision,
    license: 'MIT', course_count: catalog.length,
  }));
  return catalog;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [, , source, destination, revision] = process.argv;
  const catalog = buildPublicLearning(source, destination, revision);
  console.log(`Published ${catalog.length} courses, ${catalog.reduce((n, c) => n + c.exercise_count, 0)} exercises from ${revision}`);
}

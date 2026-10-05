import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildPublicLearning } from './build-public-learning.mjs';

const revision = 'a'.repeat(40);
function fixture(t) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'public-learning-test-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const source = path.join(temp, 'source');
  const output = path.join(temp, 'output');
  const example = path.join(source, 'examples/python/example.first');
  fs.mkdirSync(path.join(source, 'courses'), { recursive: true });
  fs.mkdirSync(path.join(example, 'content/mediaFiles'), { recursive: true });
  fs.writeFileSync(path.join(source, 'LICENSE'), 'MIT License\nCopyright Example Contributors\nPermission notice');
  const manifest = { name: 'Public course', description: 'Course description',
    content_types: [{ slug: 'week', kind: 'unit', title: 'Week' }, { slug: 'task', kind: 'assignment', title: 'Exercise' }],
    contents: [{ path: 'week_1', position: 1, content_type: 'week', contents: [
      { path: 'first', position: 1, content_type: 'task', example_identifier: 'example.first' },
      { path: 'hidden', position: 2, visible: false, content_type: 'task', example_identifier: 'secret.hidden' },
      { path: 'draft', position: 3, released: false, content_type: 'task', example_identifier: 'secret.draft' },
    ] }] };
  function manifests(data) {
    for (const slug of ['python-beginner', 'python-intermediate', 'python-advanced']) {
      fs.writeFileSync(path.join(source, `courses/${slug}.yaml`), JSON.stringify(data));
    }
  }
  manifests(manifest);
  fs.writeFileSync(path.join(example, 'meta.yaml'), JSON.stringify({ title: 'First exercise', language: 'de',
    authors: [{ email: 'PRIVATE-MARKER@example.invalid' }], test: 'PRIVATE-MARKER' }));
  fs.writeFileSync(path.join(example, 'content/index_de.md'), '# Erste Aufgabe\n![Figure](mediaFiles/figure.png)');
  fs.writeFileSync(path.join(example, 'content/index_en.md'), '# First exercise');
  fs.writeFileSync(path.join(example, 'content/solution.md'), 'PRIVATE-MARKER');
  fs.writeFileSync(path.join(source, '.env'), 'PRIVATE-MARKER');
  fs.writeFileSync(path.join(example, 'content/mediaFiles/figure.png'), Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 0]));
  fs.writeFileSync(path.join(example, 'content/mediaFiles/secret.html'), '<script>PRIVATE-MARKER</script>');
  return { source, output, example, manifest, manifests };
}

test('publication selects real course structure, bilingual text and referenced raster media only', t => {
  const f = fixture(t);
  const catalog = buildPublicLearning(f.source, f.output, revision);
  assert.equal(catalog.length, 3);
  const course = JSON.parse(fs.readFileSync(path.join(f.output, 'courses/python-beginner.json')));
  assert.deepEqual(course.contents.map(row => row.id), ['week_1', 'week_1.first']);
  assert.equal(course.materials['week_1.first'].markdown_variants.en, '# First exercise');
  assert.equal(course.source_commit, revision);
  assert.equal(fs.readFileSync(path.join(f.output, 'LICENSE.txt'), 'utf8'),
    'MIT License\nCopyright Example Contributors\nPermission notice');
  const files = fs.readdirSync(f.output, { recursive: true }).filter(name => fs.statSync(path.join(f.output, name)).isFile());
  assert(files.some(name => name.endsWith('figure.png')));
  assert(!files.some(name => /\.env|solution|secret\.html|meta\.yaml/.test(name)));
  for (const file of files) assert(!fs.readFileSync(path.join(f.output, file)).includes('PRIVATE-MARKER'));
  const other = path.join(f.output, '../repeat');
  buildPublicLearning(f.source, other, revision);
  for (const file of files) assert.deepEqual(fs.readFileSync(path.join(f.output, file)), fs.readFileSync(path.join(other, file)));
});

test('symlinked descriptions cannot publish files outside the public source', t => {
  const f = fixture(t);
  fs.unlinkSync(path.join(f.example, 'content/index_en.md'));
  const outside = path.join(f.source, '../secret.md');
  fs.writeFileSync(outside, 'PRIVATE-MARKER');
  fs.symlinkSync(outside, path.join(f.example, 'content/index_en.md'));
  assert.throws(() => buildPublicLearning(f.source, f.output, revision), /Unsafe source path/);
});

test('HTML mislabeled as a PNG fails publication', t => {
  const f = fixture(t);
  fs.writeFileSync(path.join(f.example, 'content/mediaFiles/figure.png'), '<script>alert(1)</script>');
  assert.throws(() => buildPublicLearning(f.source, f.output, revision), /signature/);
});

test('hidden course, traversal identifier and excessive text fail closed', t => {
  const f = fixture(t);
  f.manifests({ ...f.manifest, visible: false });
  assert.throws(() => buildPublicLearning(f.source, f.output, revision), /not published/);
  f.manifest.contents[0].contents[0].example_identifier = '..';
  f.manifests(f.manifest);
  assert.throws(() => buildPublicLearning(f.source, f.output, revision), /identifier/);
  f.manifest.contents[0].contents[0].example_identifier = 'example.first';
  f.manifests(f.manifest);
  fs.writeFileSync(path.join(f.example, 'content/index_en.md'), 'a'.repeat(512 * 1024 + 1));
  assert.throws(() => buildPublicLearning(f.source, f.output, revision), /size/);
  assert.throws(() => buildPublicLearning(f.source, f.output, 'main'), /exact source commit/);
});

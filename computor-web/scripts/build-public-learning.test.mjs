import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildPublicLearning, descriptionVariants } from './build-public-learning.mjs';

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
  const manifest = { path: 'unrelated.native_course', name: 'Public course', description: 'Course description',
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
  assert.equal(course.course_path, f.manifest.path);
  assert(catalog.every(entry => entry.course_path === f.manifest.path));
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

test('a welcome item renders its description in the reader language and is not counted as a unit', t => {
  const f = fixture(t);
  f.manifest.content_types.push({ slug: 'welcome', kind: 'unit', title: 'Start' });
  f.manifest.contents.unshift({ path: 'welcome', position: 0, content_type: 'welcome', title: 'Willkommen',
    description: '<!-- lang: de -->\nHallo **du**.\n\n<!-- lang: en -->\nHello **you**.\n' });
  f.manifests(f.manifest);
  buildPublicLearning(f.source, f.output, revision);
  const course = JSON.parse(fs.readFileSync(path.join(f.output, 'courses/python-beginner.json')));
  assert.equal(course.welcome_content_id, 'welcome');
  assert.deepEqual(course.materials.welcome.markdown_variants, { de: 'Hallo **du**.', en: 'Hello **you**.' });
  assert(!JSON.stringify(course).includes('lang:'));
  assert.equal(course.unit_count, 1);
  const catalog = JSON.parse(fs.readFileSync(path.join(f.output, 'catalog.json')));
  assert.equal(catalog[0].unit_count, 1);
});

test('translated titles and descriptions reach the catalog, the outline and the materials', t => {
  const f = fixture(t);
  f.manifest.title_i18n = { en: 'Public course in English', fr: 'ignored' };
  f.manifest.description_i18n = { en: 'In English', de: ' ' };
  f.manifest.contents[0].title_i18n = { de: 'Woche 1', en: 'Week 1' };
  f.manifests(f.manifest);
  fs.writeFileSync(path.join(f.example, 'meta.yaml'), JSON.stringify({ title: 'First exercise', language: 'de',
    title_i18n: { de: 'Erste Aufgabe', en: 'First exercise' } }));
  buildPublicLearning(f.source, f.output, revision);
  const catalog = JSON.parse(fs.readFileSync(path.join(f.output, 'catalog.json')));
  assert.deepEqual(catalog[0].title_i18n, { en: 'Public course in English' });
  assert.deepEqual(catalog[0].description_i18n, { en: 'In English' });
  const course = JSON.parse(fs.readFileSync(path.join(f.output, 'courses/python-beginner.json')));
  assert.deepEqual(course.title_i18n, { en: 'Public course in English' });
  assert.deepEqual(course.contents[0].title_i18n, { de: 'Woche 1', en: 'Week 1' });
  assert.deepEqual(course.materials['week_1.first'].title_i18n, { de: 'Erste Aufgabe', en: 'First exercise' });
  assert(!('description_i18n' in course.materials['week_1.first']));
});

test('an unmarked item description is Markdown in the course language', () => {
  assert.deepEqual(descriptionVariants('  Nur **deutsch**.\n', 'de'), { de: 'Nur **deutsch**.' });
  assert.deepEqual(descriptionVariants('Common\n<!-- lang: en -->\nEnglish\n<!-- lang: xx -->\nskip', 'de'),
    { en: 'Common\n\nEnglish' });
});


test('course positions order the catalog numerically with nulls last and stable title/id ties', t => {
  const f = fixture(t);
  const slugs = ['python-beginner', 'python-intermediate', 'python-advanced'];
  const cases = [
    { titles: ['Alpha', 'Middle', 'Zulu'], positions: [20, 0.5, -10], order: [2, 1, 0] },
    { titles: ['Alpha', 'Zulu', 'Middle'], positions: [null, -0.5, undefined], order: [1, 0, 2] },
    { titles: ['Zulu', 'Alpha', 'Alpha'], positions: [1, 1, 1], order: [2, 1, 0] },
  ];
  for (const { titles, positions, order } of cases) {
    slugs.forEach((slug, index) => fs.writeFileSync(path.join(f.source, `courses/${slug}.yaml`),
      JSON.stringify({ ...f.manifest, name: titles[index], position: positions[index] })));
    const catalog = buildPublicLearning(f.source, f.output, revision);
    assert.deepEqual(catalog.map(course => course.id), order.map(index => slugs[index]));
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.output, 'catalog.json'))), catalog);
    slugs.forEach((slug, index) => {
      assert.equal(catalog.find(course => course.id === slug).position, positions[index] ?? null);
      const outline = JSON.parse(fs.readFileSync(path.join(f.output, `courses/${slug}.json`)));
      assert.equal(outline.position, positions[index] ?? null);
    });
  }
});

test('course positions reject non-numeric and non-finite values', t => {
  const f = fixture(t);
  for (const position of ['1', true, {}, []]) {
    f.manifests({ ...f.manifest, position });
    assert.throws(() => buildPublicLearning(f.source, f.output, revision), /finite number or null/);
  }
  for (const position of ['1e999', '-1e999']) {
    fs.writeFileSync(path.join(f.source, 'courses/python-beginner.yaml'),
      JSON.stringify({ ...f.manifest, position: 0 }).replace('"position":0', `"position":${position}`));
    assert.throws(() => buildPublicLearning(f.source, f.output, revision), /finite number or null/);
  }
});


test('course paths require the native deployment ltree contract', t => {
  const f = fixture(t);
  for (const coursePath of [undefined, null, '', 'python-beginner', 'Python.beginner', 'python..beginner', '../private']) {
    f.manifests({ ...f.manifest, path: coursePath });
    assert.throws(() => buildPublicLearning(f.source, f.output, revision), /native ltree path/);
  }
});

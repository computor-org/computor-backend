// Build-time only: fetch a pinned public archive, verify before extracting it.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildPublicLearning } from './build-public-learning.mjs';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pin = JSON.parse(fs.readFileSync(path.join(web, 'learning-source.json')));
if (pin.repository !== 'computor-org/data-science-python' || !/^[a-f0-9]{40}$/.test(pin.commit)
  || !/^[a-f0-9]{64}$/.test(pin.archive_sha256)) throw Error('Invalid public source pin');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'computor-public-learning-'));
try {
  const response = await fetch(`https://codeload.github.com/${pin.repository}/tar.gz/${pin.commit}`, {
    redirect: 'error', signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) throw Error('Public source download failed');
  const chunks = [];
  let size = 0;
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > 20 * 1024 * 1024) throw Error('Public source archive exceeds size limit');
    chunks.push(chunk);
  }
  const archive = Buffer.concat(chunks);
  if (createHash('sha256').update(archive).digest('hex') !== pin.archive_sha256) {
    throw Error('Public source archive checksum mismatch');
  }
  const tar = path.join(temp, 'source.tar.gz');
  fs.writeFileSync(tar, archive);
  execFileSync('tar', ['-xzf', tar, '-C', temp]);
  const output = path.join(temp, 'learning');
  const courses = buildPublicLearning(path.join(temp, `data-science-python-${pin.commit}`), output, pin.commit);
  const destination = path.join(web, 'public/learning');
  fs.rmSync(destination, { recursive: true, force: true });
  fs.cpSync(output, destination, { recursive: true });
  console.log(`Regenerated ${courses.length} public courses from ${pin.commit}`);
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}

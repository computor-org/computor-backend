"""Hash learner-owned work and README files; never print source or git remotes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--persona', choices=['qa-returning', 'qa-second'], required=True)
parser.add_argument('--prepare', action='store_true')
args = parser.parse_args()
roots = [p.parent for p in Path('/home/coder/workspace/student').glob('*/.git')
         if p.parent.name.endswith('.' + args.persona)]
if len(roots) != 1:
    raise SystemExit('expected exactly one repository for the selected QA learner')
root = roots[0]
tracked = root / 'itpcp.pgph.py.math_constants/mathc.py'
untracked = root / 'qa-update-preservation.txt'
marker = b'\n# QA course-update preservation sentinel\n'
if args.prepare:
    original = tracked.read_bytes()
    if marker not in original:
        tracked.write_bytes(original + marker)
    if not untracked.exists():
        untracked.write_text('QA learner untracked work must survive course updates.\n')

def git(*argv):
    return subprocess.check_output(['git', '-C', str(root), *argv], text=True).strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if marker not in tracked.read_bytes() or not untracked.is_file():
    raise SystemExit('learner tracked edit and untracked sentinel must exist')
if not git('diff', '--name-only', '--', str(tracked.relative_to(root))):
    raise SystemExit('tracked learner edit must remain uncommitted')
if git('ls-files', '--', untracked.name):
    raise SystemExit('learner sentinel must remain untracked')
readmes = {str(p.relative_to(root)): digest(p) for p in root.rglob('*')
           if p.is_file() and p.name.lower().startswith('readme') and '.git' not in p.parts}
if not readmes:
    raise SystemExit('repository must contain learner README files')
print(json.dumps({'head': git('rev-parse', 'HEAD'), 'tracked_sha256': digest(tracked),
                  'untracked_sha256': digest(untracked), 'readmes': readmes}, sort_keys=True))

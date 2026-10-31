"""Execute the documented read-only TV command against private filesystem fixtures."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / 'docs/development/ROOT-PASSIVE-DIAGNOSTICS.md'


@unittest.skipIf(os.name == 'nt', 'TV diagnostic file modes are POSIX')
class PassiveDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.identifier = 'a' * 32
        self.install = self.root / 'var/lib/clean-your-tv-installation'
        self.worker = self.install / ('request-' + self.identifier) / 'worker.log'
        self.failure = self.root / 'var/lib/clean-your-tv-root/recovery-failure.json'
        self.record(self.identifier)
        self.write(self.worker, 'Traceback (most recent call last):\n'
                   '  File "/private/install_driver.py", line 104, in perform\n'
                   '  File "/private/deploy.py", line 112, in command\n'
                   'subprocess.CalledProcessError: secret-password and private-address\n')
        self.write(self.failure, json.dumps({'phase': 'stock-home', 'reason': 'negative-reply',
                   'luna_reason': 'service-missing', 'attempt': 'private-attempt', 'private': 'secret-password'}))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o600)

    def record(self, identifier):
        self.write(self.install / ('request-' + identifier + '.json'), json.dumps({
            'operation': identifier, 'action': 'install', 'state': 'recovery_required', 'stage': 'root-deploy'}))

    def collect(self, foreign=False):
        doc = DOC.read_text() if DOC.exists() else ''
        match = re.search(r"<<'CYTV_DIAGNOSTIC'\n(.*?)\nCYTV_DIAGNOSTIC", doc, re.S)
        program = match.group(1) if match else ''
        # Only read APIs are exposed. Real file bytes/types/modes are checked;
        # root ownership is modeled because these fixtures run without sudo.
        harness = r'''
const fs=require('fs'),vm=require('vm'),path=require('path');
const fixture=JSON.parse(process.argv[1]),code=JSON.parse(process.argv[2]),foreign=process.argv[3]==='true';
function local(p){if(typeof p!=='string'||p[0]!=='/'||p.includes('..'))throw Error('unexpected-path');return path.join(fixture,p);}
function stat(s){s.uid=foreign&&s.isFile()?123:0;return s;}
const ro={readdirSync:p=>fs.readdirSync(local(p)),lstatSync:p=>stat(fs.lstatSync(local(p))),
 openSync(p,flags){if((flags&3)!==0||!(flags&fs.constants.O_NOFOLLOW))throw Error('not-read-only');return fs.openSync(local(p),flags);},
 fstatSync:fd=>stat(fs.fstatSync(fd)),readSync:fs.readSync.bind(fs),closeSync:fs.closeSync.bind(fs)};
const output=[];
vm.runInNewContext(code,{Buffer,console:{log:s=>output.push(s)},process:{getuid:()=>0},
 require:n=>{if(n==='fs')return ro;if(n==='constants')return require('constants');throw Error('unexpected-module');}});
process.stdout.write(JSON.stringify(output));
'''
        before = {str(p): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}
        run = subprocess.run([os.environ.get('ROOT_DIAGNOSTIC_NODE', 'node'), '-e', harness,
                              json.dumps(str(self.root)), json.dumps(program), str(foreign).lower()],
                             capture_output=True, text=True, check=True)
        output = json.loads(run.stdout)
        self.assertEqual(len(output), 1, 'documented command must emit exactly one bounded JSON summary')
        summary = json.loads(output[0])
        self.assertNotIn('secret-password', run.stdout)
        self.assertNotIn('private-address', run.stdout)
        self.assertNotIn(self.identifier, run.stdout)
        after = {str(p): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}
        self.assertEqual(before, after, 'diagnosis must leave original bytes and modes untouched')
        return summary

    def test_failure_categories_and_worker_frames_exclude_raw_private_text(self):
        got = self.collect()
        self.assertEqual(got['worker']['exception'], 'CalledProcessError')
        self.assertEqual(got['worker']['frames'], ['install_driver.py:perform', 'deploy.py:command'])
        self.assertEqual(got['recovery'], {'phase': 'stock-home', 'reason': 'negative-reply', 'luna_reason': 'service-missing'})
        self.assertEqual(got['operation'], 'one-root-deploy-failure')

    def test_multiple_failed_operations_never_select_a_latest_worker(self):
        self.record('b' * 32)
        got = self.collect()
        self.assertEqual(got['operation'], 'ambiguous')
        self.assertNotIn('worker', got)

    def test_unsafe_or_oversized_files_refuse_without_dumping_content(self):
        for kind in ['symlink', 'hardlink', 'foreign', 'writable', 'oversized']:
            with self.subTest(kind=kind):
                original = self.failure.read_bytes()
                if kind == 'symlink':
                    self.failure.rename(self.failure.with_suffix('.private'))
                    self.failure.symlink_to(self.failure.with_suffix('.private'))
                elif kind == 'hardlink':
                    os.link(self.failure, self.failure.with_suffix('.private'))
                elif kind == 'writable':
                    self.failure.chmod(0o666)
                elif kind == 'oversized':
                    self.failure.write_bytes(b'x' * 4097)
                got = self.collect(foreign=kind == 'foreign')
                self.assertEqual(got['status'], 'unavailable-or-unsafe')
                if self.failure.is_symlink():
                    self.failure.unlink()
                extra = self.failure.with_suffix('.private')
                if extra.exists(): extra.unlink()
                self.write(self.failure, original.decode())

    def test_missing_failure_is_explicit_and_unknown_values_are_not_echoed(self):
        self.failure.unlink()
        self.assertEqual(self.collect()['recovery'], 'missing')
        self.write(self.failure, '{"phase":"secret-password","reason":"unexpected-private-value"}')
        self.assertEqual(self.collect()['recovery'], {})

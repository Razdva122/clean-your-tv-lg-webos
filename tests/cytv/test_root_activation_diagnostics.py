"""Read fixed metadata and bounded log categories without executing retained code."""
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix', 'TV filesystem metadata requires POSIX')
class ActivationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('cytv.root_activation_diagnostics')
        namespace={'__name__':'fixture'}
        exec(self.module.PROGRAM,namespace)
        self.read_snapshot=namespace['snapshot']
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()/'root';self.root.mkdir(mode=0o700)
        self.installed=Path(self.tmp.name).resolve()/'apps';self.installed.mkdir(mode=0o700)
        (self.root/'release.json').write_text('{"version":"0.8.4","secret":"PRIVATE"}')
        app=self.installed/'usr/palm/applications/com.cleanyourtv.root.preview'
        app.mkdir(parents=True);(app/'appinfo.json').write_text('{"id":"com.cleanyourtv.root.preview","version":"0.8.4","secret":"PRIVATE"}')
        self.log=self.root/'emergency.log';self.log.write_text('ValueError: Inactive or stale health context\n');self.log.chmod(0o600)

    def snapshot(self,cursor=None):
        return self.read_snapshot(self.root,self.installed,os.getuid(),cursor)

    def test_versions_and_legacy_refusal_are_observations_not_admission(self):
        result=self.snapshot()
        self.assertEqual(result['runtime_release'],'0.8.4')
        self.assertEqual(result['components'],{'root':'0.8.4'})
        self.assertEqual(result['component_reads']['system_updater'],'missing')
        self.assertEqual(result['health_log'],{'status':'read','scope':'historical-tail','health_refusal':'generic'})
        self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertFalse(any('can_resume' in k for k in result))

    def test_only_new_attempt_events_are_classified_after_cursor(self):
        before=self.snapshot()
        with self.log.open('a') as out:
            out.write(json.dumps({'event':'health-context-rejected','reason':'boot-mismatch','token':'PRIVATE'})+'\n')
            out.write(json.dumps({'event':'emergency-recovery','reason':'supervisor_error','transaction':'PRIVATE'})+'\n')
        result=self.snapshot(before['cursor'])
        self.assertEqual(result['health_log'],{'status':'read','scope':'since-enable','health_refusal':'boot-mismatch','supervisor_error':True})
        self.assertNotIn('PRIVATE',json.dumps(result))
        empty=self.snapshot(result['cursor'])
        self.assertNotIn('health_refusal',empty['health_log'])

    def test_rotation_and_truncation_never_attribute_history_to_new_attempt(self):
        before=self.snapshot()
        self.log.write_text('x\n')
        self.assertEqual(self.snapshot(before['cursor'])['health_log']['scope'],'historical-tail')
        self.log.rename(self.root/'emergency.previous.log')
        self.log.write_text('ValueError: Inactive or stale health context\n');self.log.chmod(0o600)
        self.assertNotEqual(self.log.stat().st_ino,before['cursor']['inode'])
        self.assertEqual(self.snapshot(before['cursor'])['health_log']['scope'],'historical-tail')

    def test_unsafe_symlink_and_hostile_reasons_are_not_exported(self):
        self.log.unlink();self.log.symlink_to(self.root/'release.json')
        self.assertEqual(self.snapshot()['health_log']['status'],'unsafe')
        self.log.unlink();self.log.write_text('{"event":"health-context-rejected","reason":{"password":"PRIVATE"}}\n');self.log.chmod(0o600)
        self.assertNotIn('PRIVATE',json.dumps(self.snapshot()))

    def test_snapshot_is_passive_even_when_retained_modules_would_execute(self):
        marker=self.root/'executed'
        (self.root/'deploy.py').write_text('open('+repr(str(marker))+',"w").write("BAD")')
        before={str(p):p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.snapshot()
        self.assertFalse(marker.exists())
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def test_large_log_append_still_binds_to_enable_window(self):
        self.log.write_text('x'*80000+'\n')
        before=self.snapshot()
        with self.log.open('a') as out:out.write('{"event":"health-context-rejected","reason":"boot-mismatch"}\n')
        result=self.snapshot(before['cursor'])
        self.assertEqual(result['health_log']['scope'],'since-enable')
        self.assertEqual(result['health_log']['health_refusal'],'boot-mismatch')

    def test_partial_baseline_cannot_turn_appended_suffix_into_an_event(self):
        self.log.write_text('not a complete record ')
        before=self.snapshot()
        with self.log.open('a') as out:
            out.write('{"event":"health-context-rejected","reason":"boot-mismatch"}\n')
            out.write('{"event":"emergency-recovery","reason":"supervisor_error"}\n')
        result=self.snapshot(before['cursor'])
        self.assertEqual(result['health_log'],{'status':'read','scope':'since-enable','supervisor_error':True})

    def test_same_size_rewrite_with_changed_metadata_is_historical(self):
        before=self.snapshot();info=self.log.stat();raw=self.log.read_bytes()
        self.log.write_bytes(raw)
        os.utime(self.log,ns=(info.st_atime_ns,info.st_mtime_ns+1000000000))
        self.assertEqual(self.snapshot(before['cursor'])['health_log']['scope'],'historical-tail')

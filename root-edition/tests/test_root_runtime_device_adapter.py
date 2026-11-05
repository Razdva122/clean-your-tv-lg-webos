import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"runtime"))
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import device_adapter as d
from profile_recovery import PAYLOAD
from profile_recovery import prepare, journal_payload
from profile_plan import STOCK, snapshot
from test_root_runtime_profile_plan import response


class DeviceAdapterTests(unittest.TestCase):
    def test_guardian_identity_and_failsafe_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); proc=root/'proc'; process=proc/'123'; process.mkdir(parents=True)
            deadline=time.monotonic()+60
            ready={'pid':123,'transaction':'test','deadline':deadline,'start_ticks':'42'}
            (root/'profile-guardian-ready.json').write_text(json.dumps(ready))
            (root/'profile-guardian-ready.json').chmod(0o600)
            command=b'/usr/bin/python3\0'+str(Path(d.__file__).with_name('guardian_device.py')).encode()+b'\0test\0'
            (process/'cmdline').write_bytes(command)
            (process/'stat').write_text('123 (python3) S '+'0 '*18+'42 0')
            journal={'transaction':'test','deadline':deadline,'state':'pending'}
            with patch.object(d,'STATE',root),patch.object(d,'PROC',proc),patch.object(d,'FAILSAFE',root/'failsafe'):
                self.assertTrue(d.active_guardian(journal))
                (root/'failsafe').touch(); self.assertFalse(d.active_guardian(journal)); (root/'failsafe').unlink()
                (process/'stat').write_text('123 (python3) S '+'0 '*18+'43 0')
                self.assertFalse(d.active_guardian(journal))
                (process/'stat').write_text('123 (python3) S '+'0 '*18+'42 0')
                (process/'cmdline').write_bytes(command.replace(b'test',b'other'))
                self.assertFalse(d.active_guardian(journal))

    def setUp(self):
        uid = patch.object(d, 'EXPECTED_UID', os.geteuid())
        uid.start()
        self.addCleanup(uid.stop)

    def test_atomic_replacement_between_open_and_fstat_retries_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pulse.json'; path.write_text('{"sequence":1}'); path.chmod(0o600)
            real_open=os.open; replaced=[]
            def opening(name, flags, *args, **kwargs):
                fd=real_open(name, flags, *args, **kwargs)
                if Path(name)==path and not replaced:
                    replaced.append(True)
                    new=path.with_suffix('.new'); new.write_text('{"sequence":2}'); new.chmod(0o600)
                    os.replace(new,path)
                return fd
            with patch.object(d.os,'open',side_effect=opening):
                self.assertEqual(d.safe_json(path),{'sequence':2})

    def test_continuous_replacement_is_bounded_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pulse.json'; path.write_text('{}'); path.chmod(0o600)
            real_open=os.open; attempts=[]
            def opening(name, flags, *args, **kwargs):
                fd=real_open(name, flags, *args, **kwargs)
                if Path(name)==path:
                    attempts.append(True)
                    new=path.with_suffix('.new'); new.write_text('{}'); new.chmod(0o600)
                    os.replace(new,path)
                return fd
            with patch.object(d.os,'open',side_effect=opening), self.assertRaisesRegex(ValueError,'repeatedly replaced'):
                d.safe_json(path)
            self.assertEqual(len(attempts),3)

    def test_hardlinked_state_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pulse.json'; path.write_text('{}'); path.chmod(0o600)
            os.link(path,Path(tmp)/'other')
            with self.assertRaises(ValueError): d.safe_json(path)

    def test_missing_journal_performs_no_service_calls(self):
        with tempfile.TemporaryDirectory() as root, patch.object(d, 'STATE', Path(root)), \
                patch.object(d, 'sam_transport') as sam:
            self.assertEqual(d.restore_once(), 'absent')
            sam.assert_not_called()

    def test_inode_conflict_is_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)/'candidate.json'; p.write_bytes(PAYLOAD); p.chmod(0o600)
            st = p.stat()
            with patch.object(d, 'TARGET', p), patch.object(d, 'EXPECTED_UID', os.geteuid()):
                self.assertEqual(d.remove_candidate({'device':st.st_dev,'inode':st.st_ino+1}), 'conflict')
                self.assertTrue(p.exists())
                self.assertEqual(d.remove_candidate({'device':st.st_dev,'inode':st.st_ino}), 'removed')

    def test_symlink_journal_refused(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); (root/'source').write_text('{}')
            (root/'profile-trial.json').symlink_to(root/'source')
            with patch.object(d, 'STATE', root), self.assertRaises(OSError): d.restore_once()

    def test_only_recovery_cli_commands_exist(self):
        with self.assertRaises(ValueError): d.main('begin')
        with self.assertRaises(ValueError): d.main('activate')

    def test_recovers_interrupted_two_link_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); stage=root/'profile-candidate.stage'; target=root/'candidate.json'
            journal=prepare(response(), STOCK)
            stage.write_bytes(journal_payload(journal)); stage.chmod(0o600); os.link(stage,target)
            st=stage.stat()
            journal.update(publication='staged-v1', candidate_identity={'device':st.st_dev,'inode':st.st_ino})
            with patch.object(d,'STATE',root), patch.object(d,'TARGET',target), \
                    patch.object(d,'sam_transport'), patch.object(d,'read',return_value=snapshot(response(),STOCK)):
                d.save(journal)
                self.assertEqual(d.restore_once(),'restored')
            self.assertFalse(stage.exists()); self.assertFalse(target.exists())

    def test_stale_guardian_cannot_restore_new_transaction(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d,'STATE',Path(tmp)), \
                patch.object(d,'sam_transport') as sam:
            journal=prepare(response(),STOCK)
            journal.update(transaction='new',candidate_identity={'device':0,'inode':0})
            d.save(journal)
            self.assertEqual(d.restore_once(expected_transaction='old'),'superseded')
            sam.assert_not_called()
            self.assertEqual(d.safe_json(Path(tmp)/'profile-trial.json')['state'],'pending')

    def test_duplicate_boot_callback_preserves_guarded_trial(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d,'STATE',Path(tmp)), \
                patch.object(d,'active_guardian',return_value=True),patch.object(d.subprocess,'Popen') as spawn:
            journal=prepare(response(),STOCK); d.save(journal)
            self.assertEqual(d.main('boot'),'guarded-trial')
            spawn.assert_not_called()


if __name__ == '__main__': unittest.main()

"""Controller presence must not be reported as a ready Home relay."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node fixture')
class HelperStartup(unittest.TestCase):
    def test_current_controller_without_ready_is_not_success_and_exit_is_reported(self):
        from cytv.helper_startup import PROGRAM
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / 'state'
            state.mkdir()
            proc = root / 'proc/1234'
            proc.mkdir(parents=True)
            (state / 'controller.pid').write_text('1234')
            (proc / 'cmdline').write_bytes(('node\0' + str(root / 'native.js') + '\0').encode())
            generation = 'I' + 'a' * 32
            start = {'event': 'start', 'pid': 1234, 'startupSchema': 1, 'generation': generation}
            log = state / 'controller.log'
            def observe(events, expected=generation):
                log.write_text('\n'.join(json.dumps(e) for e in events) + '\n')
                source = PROGRAM.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome', str(root))
                source = source.replace("'/proc/'", json.dumps(str(root / 'proc') + '/'))
                reply = subprocess.run(['node', '-e', source, expected], capture_output=True, check=True, text=True)
                return json.loads(reply.stdout)
            self.assertEqual(observe([start, {'event': 'worker-start'}])['state'], 'starting')
            failed = observe([start, {'event': 'worker-start'}, {'event': 'worker-exit', 'code': 22}])
            self.assertEqual(failed['state'], 'failed')
            self.assertEqual(failed['relay_exit_code'], 22)
            ready = observe([start, {'event': 'worker-ready', 'homeEnabled': True}])
            self.assertEqual(ready['state'], 'ready')
            self.assertTrue(ready['home_enabled'])
            ready_event = {'event': 'worker-ready', 'homeEnabled': True}
            input_wait = {'event': 'worker', 'message': 'INPUT_WAIT'}
            history = [start, ready_event, input_wait]
            self.assertEqual(observe(history)['state'], 'starting')
            self.assertEqual(observe(history + [ready_event])['state'], 'ready')
            exiting = observe([start, ready_event, {'event': 'worker', 'message': 'EXIT 22'}])
            self.assertEqual(exiting['state'], 'stopped')
            self.assertNotIn('relay_exit_code', exiting)
            (proc / 'cmdline').write_bytes(('node\0/usr/bin/unrelated.js\0' + str(root / 'native.js') + '\0').encode())
            self.assertFalse(observe([start, {'event': 'worker-ready', 'homeEnabled': True}])['controller_running'])
            (proc / 'cmdline').write_bytes(('node\0' + str(root / 'native.js') + '\0').encode())
            cmdline = proc / 'cmdline'
            cmdline.rename(proc / 'saved-cmdline')
            cmdline.mkdir()  # an unreadable cmdline, distinct from a vanished process
            unavailable = observe([start, ready_event])
            self.assertEqual(unavailable['state'], 'unavailable')
            self.assertNotIn('controller_running', unavailable)
            cmdline.rmdir()
            (proc / 'saved-cmdline').rename(cmdline)
            preference = state / 'home-control.json'
            preference.write_text('{"enabled":false}')
            self.assertFalse(observe([start, {'event': 'worker-ready', 'homeEnabled': True}])['home_enabled'])
            preference.write_text('invalid fixture record')
            self.assertEqual(observe([start, {'event': 'worker-ready', 'homeEnabled': True}])['state'], 'unavailable')
            preference.unlink()
            self.assertEqual(observe([dict(start, pid=5678), {'event': 'worker-ready'}])['state'], 'unavailable')
            self.assertEqual(observe([start, {'event': 'worker-ready'}], 'S' + 'b' * 32)['state'], 'generation-changed')
            (state / 'controller.pid').unlink()
            self.assertEqual(observe([start, {'event': 'worker-exit', 'code': 12}])['relay_exit_code'], 12)
            self.assertEqual(observe([start, {'event': 'worker-ready'}])['state'], 'stopped')
            (state / 'blocked').write_text('explicit-stop')
            self.assertEqual(observe([start, {'event': 'worker-exit', 'code': 12}])['state'], 'failed')
            self.assertEqual(observe([start, {'event': 'worker-ready'}])['state'], 'stopped')

    def test_startup_summary_does_not_export_process_or_generation_data(self):
        from cytv.helper_startup import summary
        value = summary({'state': 'failed', 'controller_running': False, 'relay_exit_code': 12,
                         'pid': 1234, 'generation': 'PRIVATE', 'command': 'PRIVATE', 'path': 'PRIVATE'})
        self.assertEqual(value, {'state': 'failed', 'controller_running': False, 'relay_exit_code': 12})
        self.assertNotIn('relay_exit_code', summary({'relay_exit_code': True}))

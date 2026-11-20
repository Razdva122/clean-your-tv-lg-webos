from contextlib import redirect_stdout
import io
import subprocess
import unittest
from unittest.mock import patch

from android.tests import native


class NativeRunnerTests(unittest.TestCase):
    @patch('android.tests.native.subprocess.run')
    def test_default_requires_the_packaged_bridge_result(self, run):
        replay = 'PASS: both editions, single operation, bounded replay, pending prompts and stale answers\n'
        bridge = 'PASS: packaged Python bridge, loopback inspection and synthetic status terminal result\n'
        cases = [(replay, False), (replay + bridge, True)]
        for output, ok in cases:
            with self.subTest(output=output):
                run.return_value = subprocess.CompletedProcess([], 0, stdout=output, stderr='')
                with patch('sys.argv', ['native.py', '--serial', 'emulator-5554']), redirect_stdout(io.StringIO()):
                    if ok:
                        native.main()
                    else:
                        with self.assertRaisesRegex(SystemExit, 'did not report success'):
                            native.main()

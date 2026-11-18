from pathlib import Path
import os
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import update_guard


class GuardTests(unittest.TestCase):
    def test_update_reservation_excludes_activation_and_retains_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            with update_guard.control(root,os.getuid()):pass
            update_guard.reserve('a'*32,root,os.getuid())
            with self.assertRaises(RuntimeError):
                with update_guard.control(root,os.getuid()):pass
            with self.assertRaises(ValueError):update_guard.release('b'*32,root,os.getuid())
            self.assertTrue((root/'update-block.json').exists())
            update_guard.release('a'*32,root,os.getuid())
            with update_guard.control(root,os.getuid()):pass

    def test_existing_or_symlink_reservation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'update-block.json').symlink_to('/etc/hosts')
            with self.assertRaises((ValueError,OSError)):update_guard.reserve('a'*32,root,os.getuid())
            with self.assertRaises(RuntimeError):
                with update_guard.control(root,os.getuid()):pass

    def test_restore_command_remains_available_while_update_blocks_activation(self):
        import importlib.util
        source=Path(__file__).resolve().parents[1]/'runtime/cli.py'
        spec=importlib.util.spec_from_file_location('update_guard_cli',source);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();update_guard.reserve('a'*32,root,os.getuid())
            with patch.object(cli.d,'STATE',root),patch.object(cli.d,'EXPECTED_UID',os.getuid()),patch.object(cli.os,'geteuid',return_value=0):
                with self.assertRaises(RuntimeError):cli.main('enable')
                with patch.object(cli, 'gate_backend') as selected:
                    selected.return_value.execute.return_value = 'restored'
                    self.assertEqual(cli.main('boot'), 'restored')
                    selected.return_value.execute.assert_called_once_with(
                        'restore', root=root, uid=os.getuid())


if __name__=='__main__':unittest.main()

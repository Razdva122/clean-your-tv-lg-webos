"""Fixed internal Root staging; no removable-media paths or firmware allowlists."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import root_staging
from cytv.errors import UserError


class RootStagingTests(unittest.TestCase):
    def test_only_confirmed_ramfs_selects_persistent_staging(self):
        for ramfs in (False, True):
            remote = Mock()
            remote.run.return_value = 'CYTV_ROOT_STAGE_READY'
            with patch('cytv.storage._tmp_is_ramfs', return_value=ramfs), patch.object(root_staging, 'inspect') as inspect, patch('cytv.storage.check'):
                stage = root_staging.create(remote, 'c1-root')
            self.assertRegex(stage, (root_staging.ROOT if ramfs else '/tmp') + r'/cytv-c1-root-[a-f0-9]{32}$')
            self.assertEqual(inspect.call_count, int(ramfs))

    def test_unknown_temporary_type_never_falls_back_to_ram(self):
        for reply in ('', 'PRIVATE', OSError('unavailable')):
            remote = Mock(); remote.run.side_effect = [reply]
            with self.assertRaises(UserError):
                root_staging.create(remote, 'product', required=1024)
            remote.upload.assert_not_called()

    def test_verified_ramfs_decision_survives_later_unavailable_type_probe(self):
        remote = Mock(); remote.__dict__['_cytv_root_ramfs'] = True
        remote.run.return_value = 'CYTV_ROOT_STAGE_READY'
        with patch.object(root_staging, 'inspect'), patch('cytv.storage.check'):
            stage = root_staging.create(remote, 'product')
        self.assertTrue(stage.startswith(root_staging.ROOT+'/'))
        self.assertFalse(any('stat -f' in call.args[0] for call in remote.run.call_args_list))

    def test_missing_capability_proof_stops_before_upload(self):
        remote = Mock()
        remote.run.return_value = ''
        with self.assertRaises(UserError):
            root_staging.inspect(remote)
        remote.upload.assert_not_called()

    def test_unknown_stage_kind_and_cleanup_paths_are_rejected(self):
        for kind in ('../foreign', 'private', 'product;touch x'):
            with self.assertRaises(ValueError):
                root_staging.create(Mock(), kind)
        for base in ('/tmp', root_staging.ROOT):
            self.assertTrue(root_staging.product_path(base+'/cytv-product-'+'a'*32))
        for path in ('/mnt/usb/cytv-product-'+'a'*32, root_staging.ROOT+'/../cytv-product-'+'a'*32, root_staging.ROOT+'/cytv-product-'+'A'*32):
            self.assertFalse(root_staging.product_path(path))

    def test_persistent_retirement_is_inventory_bound_and_legacy_staging_is_kept(self):
        remote = Mock(); remote.run.return_value = 'CYTV_ROOT_STAGE_READY'
        stage = root_staging.ROOT+'/cytv-c1-root-'+'a'*32
        root_staging.retire(remote, stage, {'bundle.json':b'{}'})
        self.assertIn('bundle.json', remote.run.call_args.args[0])
        remote.reset_mock()
        root_staging.retire(remote, '/tmp/cytv-c1-root-'+'a'*32, {'bundle.json':b'{}'})
        remote.run.assert_not_called()
        with self.assertRaises(ValueError):
            root_staging.retire(remote, '/var/lib/foreign', {})

    def test_real_script_refuses_foreign_directory_and_never_changes_its_mode(self):
        # Run the exact JS operation with a temporary test anchor and current UID.
        with tempfile.TemporaryDirectory() as temp:
            anchor = Path(temp)
            root = anchor/'clean-your-tv-root-staging'
            source = root_staging.PROGRAM.replace("'/var/lib'", json.dumps(str(anchor))).replace('uid!==0', 'uid!=='+str(os.getuid())).replace('process.getuid()!==0', 'process.getuid()!=='+str(os.getuid()))
            # The fixture anchor models the protected /var/lib boundary.
            source = source.replace("if(parent==='/')break", "if(parent===anchor)break")
            command = ['node', '-e', source, json.dumps({'root':str(root),'name':'cytv-product-'+'a'*32})]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual((root/('cytv-product-'+'a'*32)).stat().st_mode & 0o777, 0o700)
            nested = root/('cytv-product-'+'a'*32)/'runtime'
            nested.mkdir(mode=0o700)
            guard = nested/'c1-keyfilter-guard'
            guard.write_bytes(b'guardian')
            guard.chmod(0o700)
            root.chmod(0o777)
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(root.stat().st_mode & 0o777, 0o777)

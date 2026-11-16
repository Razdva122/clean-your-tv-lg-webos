"""Root companion data binding, install/readback and rollback fencing."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from updater.package import (
    SCREENSAVER, SCREENSAVER_PREFIX, SCREENSAVER_INFO, archive, members,
    installed_companion, sync_companion, inspect_package,
    APP, PREFIX, INFO, SCREENSAVER_RECIPE,
)


class CompanionDelivery(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.installed = self.root / 'apps'
        self.state = {}
        self.calls = []

    def selected(self, version):
        return version, {
            SCREENSAVER_PREFIX + 'index.html': version.encode(),
            SCREENSAVER_INFO: version.encode(),
        }

    def journal(self, value=None):
        if value is not None:
            self.state['receipt'] = value
        return self.state.get('receipt')

    def apply(self, selected, prior=None, install=None):
        sync_companion(
            self.installed, selected, prior, self.journal, self.root,
            uid=os.getuid(), install=install or self.install, remove=self.remove,
        )

    def install(self, app, ipk, timeout, on_ready):
        self.assertEqual(app, SCREENSAVER)
        on_ready()
        self.calls.append('install')
        files = archive(members(Path(ipk).read_bytes())['data.tar.gz'])
        for name, raw in files.items():
            path = self.installed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return {'completed': True, 'event': {'id': app, 'statusValue': 30, 'details': {
            'packageId': app, 'client': 'com.webos.lunasend-123',
            'ipkFile': '/var/lib/clean-your-tv-installer/cytv-root-install-test/package.ipk',
        }}}

    def remove(self, app, timeout):
        self.assertEqual(app, SCREENSAVER)
        self.calls.append('remove')
        self.assertIsNone(self.state['receipt']['terminal'])
        for name in (SCREENSAVER_PREFIX + 'index.html', SCREENSAVER_INFO):
            path = self.installed / name
            path.unlink()
        (self.installed / SCREENSAVER_PREFIX).rmdir()
        # Vendor may leave an empty package metadata directory.
        return {'completed': True, 'event': {'id': app, 'details': {'state': 'removed'}}}

    def test_upgrade_rollback_and_downgrade_to_release_without_companion(self):
        previous, new = self.selected('0.0.3'), self.selected('0.0.4')
        self.apply(previous)
        self.apply(previous)   # Restart after terminal never sends a second request.
        self.state.clear()
        self.apply(new, previous)
        self.assertTrue(installed_companion(self.installed, new, os.getuid()))
        self.state.clear()
        self.apply(previous, new)
        self.assertTrue(installed_companion(self.installed, previous, os.getuid()))
        self.state.clear()
        self.apply(None, previous)
        self.apply(None, previous)
        self.assertTrue(installed_companion(self.installed, None, os.getuid()))
        self.assertEqual(self.calls, ['install', 'install', 'install', 'remove'])

    def test_unknown_submission_never_replays_or_adopts_new_bytes(self):
        target = self.selected('0.0.3')

        def lost_reply(*args, **kwargs):
            self.install(*args, **kwargs)
            raise RuntimeError('lost vendor reply')

        with self.assertRaisesRegex(RuntimeError, 'lost vendor'):
            self.apply(target, install=lost_reply)
        self.assertTrue(installed_companion(self.installed, target, os.getuid()))
        with self.assertRaisesRegex(ValueError, 'outcome unconfirmed'):
            self.apply(target)
        self.assertEqual(self.calls, ['install'])

    def test_package_preflight_rejects_a_malformed_companion(self):
        from cytv.package import ipk
        version = '0.20.4'
        files = {
            PREFIX + 'appinfo.json': json.dumps({
                'id': APP, 'version': version, 'type': 'web', 'main': 'index.html',
            }).encode(),
            PREFIX + 'index.html': b'Root',
            INFO: json.dumps({
                'id': APP, 'app': APP, 'version': version, 'services': [],
            }).encode(),
            SCREENSAVER_RECIPE: b'{}',
        }
        raw = ipk(APP, version, files)
        descriptor = {
            'version': version, 'size': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
        }
        with self.assertRaisesRegex(ValueError, 'screensaver'):
            inspect_package(raw, descriptor)

    def test_wrong_prior_companion_is_not_replaced(self):
        self.apply(self.selected('0.0.1'))
        self.state.clear()
        with self.assertRaisesRegex(ValueError, 'verified Root baseline'):
            self.apply(self.selected('0.0.4'), self.selected('0.0.3'))
        self.assertEqual(self.calls, ['install'])

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'root-edition'))
from installation import Ownership
from updater.store import Store

spec = importlib.util.spec_from_file_location('homebrew_debloat', ROOT / 'homebrew/debloat.py')
debloat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(debloat)


class HomebrewDebloatTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.owner = Ownership(Store(Path(directory.name).resolve(), uid=os.getuid()))
        self.lease = dict(schema=1, id='a' * 32, owner='product', terminal=True, stage='complete',
                          journal='product-' + 'b' * 32 + '.json')
        with self.owner._lock(create=True):
            self.owner.store.write('operation', self.lease)
        self.device = Mock()
        self.device.inspect.return_value = {'state': 'installed', 'tile_protocol': 1}
        self.values = {'homePromotion': 'on', 'lmt': 'off', 'promotionStreamer': None,
                       'contentRecommendation': 'on'}
        self.writes = []
        self.before_write = lambda key: None

    def invoke(self, uri, payload, timeout):
        self.assertGreater(timeout, 0)
        if uri == 'luna://com.webos.settingsservice/getSystemSettings':
            return {'returnValue': True, 'settings': {k: self.values.get(k) for k in payload['keys']},
                    'unrelated': 'private address'}
        self.assertEqual(uri, 'luna://com.webos.settingsservice/setSystemSettings')
        self.assertEqual(len(payload['settings']), 1)
        key, target = next(iter(payload['settings'].items()))
        self.before_write(key)
        self.writes.append((key, target))
        self.values[key] = target
        return {'returnValue': True}

    def run_action(self, action, *keys):
        return debloat.run(action, list(keys), self.owner, self.device, self.invoke)

    def test_selected_values_are_saved_before_write_and_restored(self):
        self.before_write = lambda key: self.assertIn(key, self.owner.store.read('homebrew-debloat')['settings'])
        applied = self.run_action('debloat', 'homePromotion', 'lmt')
        self.assertEqual(applied['results'], {'homePromotion': 'verified', 'lmt': 'verified'})
        self.assertEqual(applied['settings'], {'homePromotion': {'value': 'off', 'saved': True},
                                               'lmt': {'value': 'on', 'saved': True}})
        self.assertEqual(self.writes, [('homePromotion', 'off'), ('lmt', 'on')])
        self.assertEqual(self.run_action('debloat', 'homePromotion')['results'], {'homePromotion': 'already'})
        self.assertEqual(len(self.writes), 2)
        restored = self.run_action('debloat-restore', 'lmt')
        self.assertEqual(restored['results'], {'lmt': 'restored'})
        self.assertEqual(restored['settings'], {'lmt': {'value': 'off', 'saved': False}})
        self.assertEqual(self.writes[-1], ('lmt', 'off'))
        self.assertEqual(self.values['contentRecommendation'], 'on')
        status = self.run_action('debloat-status')
        self.assertEqual(status['settings']['homePromotion'], {'value': 'off', 'saved': True})
        self.assertEqual(status['settings']['lmt'], {'value': 'off', 'saved': False})
        self.assertNotIn('private address', str(status))

    def test_unreadable_or_unverified_writes_have_distinct_results(self):
        failed = self.run_action('debloat', 'promotionStreamer')
        self.assertEqual(failed['results'], {'promotionStreamer': 'unavailable'})
        self.assertEqual(self.writes, [])
        def rejected(uri, payload, timeout):
            if uri.endswith('/setSystemSettings'):
                err = RuntimeError()
                err.luna = {'reason': 'permission-denied'}
                raise err
            return self.invoke(uri, payload, timeout)
        reply = debloat.run('debloat', ['lmt'], self.owner, self.device, rejected)
        self.assertEqual(reply['results'], {'lmt': 'write-rejected'})
        self.assertEqual(reply['settings']['lmt']['guide'], 'advertising')
        self.assertNotIn('guide', failed['settings']['promotionStreamer'])
        self.assertEqual(self.values['lmt'], 'off')
        self.run_action('debloat', 'lmt')
        restored = debloat.run('debloat-restore', ['lmt'], self.owner, self.device, rejected)
        self.assertEqual(restored['results'], {'lmt': 'restore-rejected'})
        self.assertEqual(restored['settings']['lmt'], {'value': 'on', 'saved': True, 'guide': 'advertising'})

    def test_busy_or_incomplete_product_cannot_change_settings(self):
        with self.owner._lock(create=False):
            self.assertEqual(self.run_action('debloat', 'lmt')['code'], 'busy')
        self.owner.store.write('operation', {**self.lease, 'terminal': False})
        self.assertEqual(self.run_action('debloat', 'lmt')['code'], 'not_available')
        self.assertEqual(self.writes, [])

    def test_invalid_or_corrupt_requests_fail_closed(self):
        for keys in ('lmt;whoami', 'x', 'lmt,lmt', 'lmt,'):
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                debloat.selection('debloat', keys)
        self.owner.store.write('homebrew-debloat', {'schema': 1, 'settings': {'lmt': {'original': 'on', 'target': 'off'}}})
        self.assertEqual(self.run_action('debloat', 'lmt')['code'], 'journal_failed')
        self.assertEqual(self.writes, [])

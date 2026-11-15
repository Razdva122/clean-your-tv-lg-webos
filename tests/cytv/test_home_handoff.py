import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

@unittest.skipUnless(os.name == 'posix', 'TV handoff uses POSIX primitives')
class HomeHandoffTests(unittest.TestCase):
    def setUp(self):
        from cytv.home_handoff import PROGRAM
        self.handoff = {}
        exec(PROGRAM, self.handoff)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.handoff['ROOT'] = self.root
        self.handoff['OWNER'] = os.getuid()
        self.home = '/usr/bin/com.webos.app.home'
        self.source = '/media/developer/apps/usr/palm/applications/test.launcher/launcher'
        self.integration = '/var/lib/test-home'
        self.hook = '/var/lib/webosbrew/init.d/64-test-home'
        self.filter = f'{self.integration}/route.js'
        self.service = 'com.webos.service.testhome'
        self.stock = [{'file': '/usr/lib/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        self.other = {'file': self.filter, 'handler': 'takeover'}
        self.chain = self.stock + [self.other]
        self.file(self.source, 'executable fixture')
        self.file(f'{self.integration}/state.json', json.dumps({
            'enabled': True, 'method': 'executable', 'homeId': 'com.webos.app.home',
            'appDir': self.source.rsplit('/', 1)[0],
        }))
        self.file(f'{self.integration}/boot.sh',
                  f'#!/bin/sh\nHOME_ID=com.webos.app.home\n'
                  f'test -r {self.integration}/state.json || exit 1\n'
                  f'if [ "$1" = boot ]; then mount --bind {self.source} {self.home}; fi\n')
        self.file(f'{self.integration}/lock', '')
        self.file(self.filter, f"lunaCall.send('{self.service}', '/prepare');")
        self.path(self.hook).parent.mkdir(parents=True)
        self.path(self.hook).symlink_to(f'{self.integration}/boot.sh')
        self.unrelated = '/var/lib/webosbrew/init.d/99-keep'
        self.file(self.unrelated, '#!/bin/sh\nexit 0\n')
        self.service_path = f'/var/luna-service2/services.d/{self.service}.service'
        self.manifest = f'/var/luna-service2/manifests.d/{self.service}.json'
        self.file(f'{self.integration}/early', 'helper fixture')
        self.file(self.service_path, f'[D-BUS Service]\nName={self.service}\nExec={self.integration}/early\nType=dynamic\n')
        self.role = f'/var/luna-service2/roles.d/{self.service}.json'
        self.api = f'/var/luna-service2/api-permissions.d/{self.service}.json'
        self.file(self.role, json.dumps({
            'exeName': f'{self.integration}/early', 'allowedNames':[self.service],
            'permissions':[{'service':self.service, 'inbound':['com.webos.starfish.keyfilters'], 'outbound':[]}],
        }))
        self.file(self.api, json.dumps({'all':[self.service + '/prepare']}))
        self.file(self.manifest, json.dumps({
            'id': self.service, 'serviceFiles':[self.service_path],
            'roleFiles':[self.role], 'apiPermissionFiles':[self.api],
        }))
        self.handoff['read_chain'] = lambda: self.chain
        self.handoff['write_chain'] = self.write_chain
        self.handoff['mount_source'] = lambda: (self.source, [], [], 1, 1)
        self.handoff['mountinfo'] = lambda: []
        self.handoff['stock_preview'] = lambda: 'a' * 64
        self.handoff['stock_home'] = lambda: 'a' * 64
        self.handoff['unmount'] = Mock()
        self.handoff['rescan'] = Mock()

    def file(self, path, content):
        target = self.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def path(self, path):
        return self.root / path.lstrip('/')

    def write_chain(self, chain):
        self.chain = chain

    def test_verified_handoff_removes_only_owner_activation_and_restores_stock(self):
        plan = self.handoff['inspect']()
        self.assertEqual(plan['stock_chain'], self.stock)
        self.handoff['apply'](self.handoff['fingerprint'](plan))
        self.assertEqual(self.chain, self.stock)
        self.handoff['unmount'].assert_called_once()
        self.handoff['rescan'].assert_called_once()
        self.assertFalse(self.path(self.hook).is_symlink())
        self.assertFalse(self.path(self.service_path).exists())
        self.assertTrue(self.path(self.unrelated).exists())
        self.assertTrue(self.path(self.source).exists())
        self.assertFalse(self.path(self.integration).exists())
        archive, = self.path(self.handoff['ARCHIVE']).glob('complete-*')
        self.assertTrue((archive / '0' / 'route.js').is_file())

    def test_unclassified_keyfilter_and_changed_plan_do_not_mutate(self):
        plan = self.handoff['inspect']()
        self.chain += [{'file': '/var/lib/other/unknown.js', 'handler': 'other'}]
        with self.assertRaises(ValueError):
            self.handoff['apply'](self.handoff['fingerprint'](plan))
        self.handoff['unmount'].assert_not_called()
        self.assertTrue(self.path(self.hook).is_symlink())
        self.assertTrue(self.path(self.service_path).exists())

    def test_literal_bind_hook_without_provider_state(self):
        self.path(self.hook).unlink()
        self.chain = self.stock
        replacement = '/var/lib/webosbrew/init.d/51-other-launcher'
        self.file(replacement, f'#!/bin/sh\nmount -o bind {self.source} {self.home}\n')
        plan = self.handoff['inspect']()
        self.assertEqual(set(plan['files']), {replacement})
        self.handoff['apply'](self.handoff['fingerprint'](plan))
        self.assertFalse(self.path(replacement).exists())
        self.assertTrue(self.path(self.unrelated).exists())
        self.handoff['unmount'].assert_called_once()
        self.handoff['rescan'].assert_not_called()

    def test_failed_unmount_restores_registrations_and_keyfilters(self):
        plan = self.handoff['inspect']()
        self.handoff['unmount'].side_effect = OSError('busy')
        with self.assertRaises(OSError):
            self.handoff['apply'](self.handoff['fingerprint'](plan))
        self.assertEqual(self.chain, plan['chain'])
        self.assertTrue(self.path(self.hook).is_symlink())
        self.assertTrue(self.path(self.service_path).exists())
        self.assertFalse(self.path(self.handoff['RECEIPT']).exists())

    def test_retry_recovers_interrupted_handoff(self):
        plan = self.handoff['inspect']()
        receipt = self.path(self.handoff['RECEIPT'])
        receipt.parent.mkdir(parents=True, mode=0o700)
        receipt.mkdir(mode=0o700)
        (receipt / 'plan.json').write_text(json.dumps(plan))
        for index, filename in enumerate(plan['files']):
            self.path(filename).rename(receipt / str(index))
        self.chain = self.stock
        self.handoff['mountinfo'] = lambda: [
            (['10', '1', '7:2', '/source', self.home, 'rw'], ['ext4', '/dev/test', 'rw']),
        ]
        self.handoff['recover']()
        self.assertEqual(self.chain, plan['chain'])
        self.assertEqual(self.handoff['fingerprint'](self.handoff['inspect']()),
                         self.handoff['fingerprint'](plan))
        self.handoff['apply'](self.handoff['fingerprint'](plan))
        self.assertEqual(self.chain, self.stock)

    def test_unrelated_root_install_is_untouched(self):
        self.file('/var/lib/clean-your-tv-installation/operation.json', '{}')
        with self.assertRaises(ValueError):
            self.handoff['inspect']()
        self.assertTrue(self.path(self.hook).is_symlink())
        self.handoff['unmount'].assert_not_called()

    def test_retry_finishes_quarantine_when_stock_is_already_uncovered(self):
        plan = self.handoff['inspect']()
        receipt = self.path(self.handoff['RECEIPT'])
        receipt.parent.mkdir(mode=0o700)
        receipt.mkdir(mode=0o700)
        (receipt / 'plan.json').write_text(json.dumps(plan))
        self.path(self.integration).rename(receipt / '0')
        self.assertTrue(self.handoff['recover']())
        self.assertFalse(self.path(self.hook).is_symlink())
        self.assertFalse(self.path(self.service_path).exists())
        self.assertEqual(self.chain, self.stock)
        self.assertFalse(receipt.exists())
        self.handoff['unmount'].assert_not_called()

    def test_hook_comment_alone_does_not_attest_mount_ownership(self):
        self.file(f'{self.integration}/boot.sh',
                  f'#!/bin/sh\n# mount --bind {self.source} {self.home} via state.json at boot\n')
        with self.assertRaises(ValueError):
            self.handoff['inspect']()
        self.assertTrue(self.path(self.hook).is_symlink())

    def test_same_directory_non_home_service_is_not_quarantined(self):
        self.file(self.filter, f"lunaCall.send('{self.service}', '/unrelated');")
        with self.assertRaises(ValueError):
            self.handoff['inspect']()
        self.assertTrue(self.path(self.service_path).exists())
        self.handoff['unmount'].assert_not_called()

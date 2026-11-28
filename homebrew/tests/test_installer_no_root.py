"""No-root Homebrew operation identity and recovery."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cytv import no_root_observer
from cytv.operations import Installer


class OriginalOperationTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('homebrew.no_root'))
        from homebrew import no_root
        self.backend = no_root

    def test_a_lost_worker_claim_keeps_original_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve() / 'operations'
            coordinator = self.backend.Coordinator(folder)
            operation = 'a' * 32
            coordinator.reserve(operation, 'b' * 64, 'c' * 64)
            restarted = self.backend.Coordinator(folder)
            result = restarted.status(operation)
            self.assertEqual(result['state'], 'recovery_required')
            self.assertEqual(result['operation'], operation)
            self.assertEqual(result['stage'], 'reserved')
            self.assertFalse(result['can_resume'])
            self.assertEqual(restarted.status('d' * 32)['state'], 'unknown')
            with self.assertRaises(ValueError):
                restarted.reserve('d' * 32, 'b' * 64, 'c' * 64)
            self.assertEqual(restarted.status()['operation'], operation)

    def test_public_status_excludes_private_worker_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            coordinator.reserve('a' * 32, 'b' * 64, 'c' * 64)
            result = coordinator.status()
            self.assertNotIn('payload_sha256', result)
            self.assertNotIn('candidate_sha256', result)

    def create_snapshot(self, source):
        source.mkdir(mode=0o700)
        files = {}
        for name in ('edition/cytv/tv/boot-proof.js', 'edition/no_root.py', 'edition/edition.py', 'edition/pairing.py',
                     'no-root/payload.json', 'no-root/fallback.png', 'supervisor/bundle.json',
                     'root-updater/bundle.json', 'root-updater/cleanup_tail.js', 'installer-support/lifecycle-gate'):
            path = source / name
            for parent in reversed(path.relative_to(source).parents):
                (source / parent).mkdir(mode=0o700, exist_ok=True)
            raw = name.encode()
            path.write_bytes(raw)
            files[name] = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        manifest = json.dumps({'files': files}).encode()
        (source / 'manifest.json').write_bytes(manifest)
        pin = hashlib.sha256(manifest).hexdigest()
        return pin

    def test_detached_worker_snapshot_keeps_verified_private_ancestors(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            source, destination = folder / 'stage', folder / 'retained'
            pin = self.create_snapshot(source)

            original_mask = os.umask(0o022)
            try:
                self.backend.copy_worker(source, destination, pin)
            finally:
                os.umask(original_mask)
            self.backend.verify_worker(destination, pin)
            (destination / 'edition/no_root.py').write_text('different data')
            with self.assertRaises(ValueError):
                self.backend.verify_worker(destination, pin)

    def test_worker_lock_excludes_a_second_writer_and_status_remains_available(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve() / 'operations'
            first, second = self.backend.Coordinator(folder), self.backend.Coordinator(folder)
            operation = 'a' * 32
            with first.lock(create=True) as owner:
                self.assertIsNotNone(owner)
                first.reserve(operation, 'b' * 64, 'c' * 64)
                with second.lock() as attempt:
                    self.assertIsNone(attempt)
                self.assertEqual(second.status(operation)['state'], 'pending')
            self.assertEqual(second.status(operation)['state'], 'recovery_required')

    def test_full_homebrew_entry_is_preserved_and_light_entry_blocks_setup(self):
        from cytv import package
        from cytv.errors import UserError

        class Tv:
            def luna(self, uri, payload, timeout=30):
                return {'apps': [{'id': package.TILE_APP, 'version': '0.0.0'}]}

            def run(self, _):
                return ''

        profile = {'host': 'localhost', 'edition': 'no-root', 'port': 22, 'connection': 'root-ssh'}
        with tempfile.TemporaryDirectory() as temporary:
            store = self.backend.Store(Path(temporary).resolve())
            installer = Installer(Tv(), store, profile, '.', {}, homebrew_entry=True)
            with patch('cytv.single_tile_setup.installed_role', return_value='homebrew'):
                self.assertEqual(installer.single_tile_source(), {})
                inspection = Installer(Tv(), None, profile, '.', {}, homebrew_entry=True)
                self.assertEqual(inspection.single_tile_source(), {})
            with patch('cytv.single_tile_setup.installed_role', return_value='no-root'):
                with self.assertRaises(UserError):
                    installer.single_tile_source()

    def test_signed_working_generation_can_differ_from_original_setup(self):
        class TvInstaller:
            def helper_state(self, timeout=30):
                return 'uncertain'

        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation = 'a' * 32
            record = coordinator.reserve(operation, 'b' * 64, 'c' * 64)
            record.update(stage='complete', result={'system_updates': True})
            coordinator.write(record)
            installer = TvInstaller()
            installer.store = coordinator.store(operation)
            inventory = {'edition': 'no-root', 'release': 'v2.0.1', 'resolution': '1280x720',
                         'components': [{'name': 'home', 'version': '2.0.1'},
                                        {'name': 'helper', 'version': '2.0.1'}]}
            with (patch.object(self.backend, 'make_installer', return_value=installer),
                  patch.object(self.backend, 'current_setup', return_value=True),
                  patch.object(self.backend, 'working_inventory', return_value=inventory, create=True)):
                status = self.backend.live_status(coordinator, operation)
            self.assertEqual(status['state'], 'complete')
            self.assertEqual(status['result']['working_inventory']['release'], 'v2.0.1')
            self.assertEqual(status['result']['helper_observation'], 'unverified')
            self.assertFalse(status['result']['hardware_verified'])

    def test_fresh_homebrew_setup_cannot_overwrite_existing_ambient(self):
        from cytv import package
        from cytv.errors import UserError

        class Tv:
            def __init__(self, catalogued):
                self.catalogued = catalogued

            def luna(self, uri, payload, timeout=30):
                apps = [package.TILE_APP]
                if self.catalogued:
                    apps.append(package.SCREENSAVER_APP)
                return {'apps': [{'id': app, 'version': '1.0.0'} for app in apps]}

            def run(self, command):
                return 'CYTV_REMAINS' if package.SCREENSAVER_APP in command else ''

        profile = {'host': 'localhost', 'edition': 'no-root', 'port': 22, 'connection': 'root-ssh'}
        with patch('cytv.single_tile_setup.installed_role', return_value='homebrew'):
            for catalogued in (True, False):
                installer = Installer(Tv(catalogued), None, profile, '.', {}, homebrew_entry=True)
                with self.subTest(catalogued=catalogued), self.assertRaises(UserError):
                    installer.require_fresh_single_tile()

    def test_remove_fences_original_worker_and_preserves_the_original_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation, removal, unrelated = 'a' * 32, 'd' * 32, 'e' * 32
            with coordinator.lock(create=True):
                coordinator.reserve(operation, 'b' * 64, 'c' * 64)
                self.assertEqual(self.backend.prepare_remove(coordinator, removal)['state'], 'pending')
            self.assertEqual(self.backend.prepare_remove(coordinator, removal, unrelated)['state'],
                             'recovery_required')
            self.assertIsNone(coordinator.current().get('removal'))
            self.assertEqual(self.backend.prepare_remove(coordinator, removal)['state'], 'removal_ready')
            self.assertEqual(self.backend.prepare_remove(coordinator, removal, operation)['state'],
                             'removal_ready')
            self.assertEqual(self.backend.prepare_remove(coordinator, unrelated)['state'],
                             'recovery_required')
            self.assertEqual(coordinator.status(operation)['code'], 'no-root-removal-pending')
            self.assertFalse(coordinator.resumable(coordinator.current()))

    def test_matching_partial_supervisor_can_continue_when_status_is_incomplete(self):
        class InstallerFixture:
            def __init__(self, store):
                self.store = store
                self.applied = False

            def system_updater_cleanup(self, action):
                if not self.applied:
                    raise ValueError('Incomplete supervisor bootstrap')
                return {'present': True, 'bootstrap_complete': True, 'ownership_verified': True,
                        'disabled': False, 'edition': 'no-root', 'product_schema': 2,
                        'setup_id': original_setup, 'bootstrap_digest': supervisor_pin}

            def enable_system_updates(self):
                pending = self.store.pending(self.profile)
                if pending['diagnostic_id'] != original_setup:
                    raise ValueError('Wrong continuation ID')
                self.applied = True
                self.store.finish(self.profile)

            def helper_state(self, timeout=30):
                return 'stopped'

        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation, supervisor_pin = 'a' * 32, 'd' * 64
            record = coordinator.reserve(operation, 'b' * 64, 'c' * 64)
            record.update(stage='updates', launch_requested=True, activation_cancelled=False)
            coordinator.write(record)
            store = coordinator.store(operation)
            installer = InstallerFixture(store)
            installer.profile = self.backend.PROFILE
            store.begin(installer.profile, 'enable-system-updates', stage='setup', bootstrap_digest=supervisor_pin)
            original_setup = store.pending(installer.profile)['diagnostic_id']
            with (patch.object(self.backend, 'make_installer', return_value=installer),
                  patch.object(self.backend, 'verify_packages')):
                self.backend.perform(coordinator, Path(temporary), record, resume=True)
            self.assertEqual(coordinator.status(operation)['state'], 'complete')

    def test_retirement_preserves_unknown_files_and_other_original_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation = 'a' * 32
            with coordinator.lock(create=True):
                pass
            folder = coordinator.path(operation)
            folder.mkdir(mode=0o700)
            stage = folder / 'payload'
            pin = self.create_snapshot(stage)
            record = dict(schema=1, operation=operation, payload_sha256=pin, candidate_sha256='c' * 64,
                          stage='complete', result={'installed': 'no-root', 'packages_verified': True,
                          'configuration_verified': True, 'system_updates': True})
            coordinator.write(record)
            proof = folder / 'archived-setup.json'
            proof.write_text('original setup proof')
            capsule = coordinator.store(operation).device_dir(self.backend.PROFILE) / ('capsule-' + operation + '.json')
            capsule.write_text('original capsule')
            unknown = stage / 'unknown.json'
            unknown.write_text('keep this')

            result = self.backend.retire_payload(coordinator, operation, pin)
            self.assertEqual(result['code'], 'no-root-payload-retained')
            self.assertTrue((stage / 'edition/no_root.py').is_file())
            self.assertEqual(unknown.read_text(), 'keep this')
            unknown.unlink()

            result = self.backend.retire_payload(coordinator, operation, pin)
            self.assertEqual(result['code'], 'no-root-payload-retired')
            self.assertFalse(stage.exists())
            self.assertEqual(proof.read_text(), 'original setup proof')
            self.assertEqual(capsule.read_text(), 'original capsule')
            self.assertEqual(coordinator.current(), record)

    def test_retirement_reuses_a_verified_removal_after_interrupted_unlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation, removal = 'a' * 32, 'd' * 32
            with coordinator.lock(create=True):
                pass
            folder = coordinator.path(operation)
            folder.mkdir(mode=0o700)
            retiring = folder / 'payload-retiring'
            pin = self.create_snapshot(retiring)
            (retiring / 'edition/no_root.py').unlink()
            record = dict(schema=1, operation=operation, payload_sha256=pin, candidate_sha256='c' * 64,
                          stage='packages', removal=removal)
            coordinator.write(record)

            with patch.object(self.backend, 'removal_completed', return_value=False):
                self.assertEqual(self.backend.retire_payload(coordinator, operation, pin)['state'], 'recovery_required')
                self.assertTrue(retiring.is_dir())
            with patch.object(self.backend, 'removal_completed', return_value=True):
                self.assertEqual(self.backend.retire_payload(coordinator, operation, pin)['code'], 'no-root-payload-retired')
            self.assertFalse(retiring.exists())
            self.assertEqual(coordinator.current(), record)

    def test_reenrollment_requires_current_removal_and_a_matching_fresh_review(self):
        from types import SimpleNamespace
        from cytv.errors import UserError

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            coordinator = self.backend.Coordinator(folder / 'operations')
            old, new, removal = 'a' * 32, 'd' * 32, 'e' * 32
            previous = coordinator.reserve(old, 'b' * 64, 'c' * 64)
            previous.update(stage='complete', removal=removal, result={'system_updates': True})
            coordinator.write(previous)
            original_folder = coordinator.path(old)
            capsule = original_folder / 'original-proof.json'
            capsule.write_text('original evidence')
            archive = original_folder / 'archived-setup.json'
            inspector = SimpleNamespace(_root_handoff={'removal': removal})
            candidate = 'f' * 64
            approved = {'state': 'eligible', 'candidate_sha256': candidate}

            def copy_verified(source, destination, pin):
                self.assertEqual(coordinator.current(), previous)
                destination.mkdir(mode=0o700)

            with (coordinator.lock(create=True),
                  patch.object(self.backend, 'make_installer', return_value=inspector),
                  patch.object(self.backend, 'inspect_candidate', return_value=approved),
                  patch.object(self.backend, 'copy_worker', side_effect=copy_verified),
                  patch.object(self.backend, 'removal_completed', return_value=False) as removed):
                with self.assertRaises(UserError):
                    self.backend.reserve_setup(coordinator, folder, 'b' * 64, new, candidate)
                self.assertEqual(coordinator.current(), previous)
                self.assertFalse(archive.exists())

                removed.return_value = True
                with self.assertRaises(UserError):
                    self.backend.reserve_setup(coordinator, folder, 'b' * 64, new, '9' * 64)
                self.assertEqual(coordinator.current(), previous)
                self.assertFalse(archive.exists())

                inspector._root_handoff = {'removal': '9' * 32}
                with self.assertRaises(UserError):
                    self.backend.reserve_setup(coordinator, folder, 'b' * 64, new, candidate)
                self.assertEqual(coordinator.current(), previous)
                self.assertFalse(archive.exists())

                inspector._root_handoff = {'removal': removal}
                result = self.backend.reserve_setup(coordinator, folder, 'b' * 64, new, candidate)

            self.assertEqual(result['operation'], new)
            self.assertEqual(result['stage'], 'reserved')
            self.assertEqual(coordinator.current(), result)
            self.assertEqual(json.loads(archive.read_text()), previous)
            self.assertEqual(capsule.read_text(), 'original evidence')

    def test_a_previously_archived_setup_id_cannot_be_replayed(self):
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation = 'a' * 32
            coordinator.create_root()
            previous = coordinator.path(operation)
            previous.mkdir(mode=0o700)
            (previous / 'payload').mkdir(mode=0o700)
            (previous / 'archived-setup.json').write_text('previous operation evidence')
            snapshot = coordinator.root / 'snapshot'
            snapshot.mkdir(mode=0o700)

            with patch.object(self.backend, 'verify_worker'):
                with self.assertRaises(ValueError):
                    coordinator.reserve(operation, 'b' * 64, 'c' * 64, snapshot)
            self.assertIsNone(coordinator.current())

    def test_previous_removal_remains_current_only_with_its_exact_clean_fence(self):
        with tempfile.TemporaryDirectory() as temporary:
            product = Path(temporary).resolve()
            removal, target, predecessor, fence = (character * 32 for character in 'defa')
            self.backend.private_write(product / ('homebrew-removal-' + removal + '.json'), json.dumps(
                {'schema': 1, 'operation': removal, 'target': target, 'lease': predecessor}).encode())
            self.backend.private_write(product / ('clean-removal-' + target + '.json'), json.dumps({
                'schema': 1, 'protocol': 'clean-removal-v1', 'operation': target, 'removal': removal,
                'lease': predecessor, 'final_original_lease': predecessor, 'final_fence': fence,
                'state': 'complete', 'stage': 'verified-clean', 'current': True,
                'result': {'removed': True, 'private_cleanup_verified': True,
                           'applications_services_startup_removed': True},
            }).encode())
            lease = {'schema': 1, 'owner': 'clean-removal', 'stage': 'verified-clean', 'terminal': False,
                     'id': fence, 'journal': 'product-' + target + '.json'}
            self.backend.private_write(product / 'operation.json', json.dumps(lease).encode())

            self.assertTrue(self.backend.removal_completed(removal, product))
            self.assertFalse(self.backend.removal_completed('b' * 32, product))
            lease['id'] = predecessor
            self.backend.private_write(product / 'operation.json', json.dumps(lease).encode())
            self.assertFalse(self.backend.removal_completed(removal, product))

    def test_root_removal_without_no_root_receipt_does_not_create_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve() / 'operations'
            coordinator = self.backend.Coordinator(folder)
            self.assertEqual(self.backend.prepare_remove(coordinator, 'd' * 32)['state'], 'unknown')
            self.assertFalse(folder.exists())

    def test_clean_root_recovery_status_offers_only_an_explicit_locked_check(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation = 'a' * 32
            record = coordinator.reserve(operation, 'b' * 64, 'c' * 64)
            record.update(stage='packages')
            coordinator.write(record)
            store = coordinator.store(operation)
            profile = self.backend.PROFILE
            store.begin(profile, 'install', recovery_protocol=no_root_observer.PROTOCOL, capsule_sha256='d' * 64)
            capsule = {'plan': {'root_handoff': {}, 'operation': 'e' * 32, 'action': 'install'}}
            installer = SimpleNamespace(store=store)

            with (patch.object(self.backend, 'make_installer', return_value=installer),
                  patch.object(no_root_observer, 'capsule', return_value=capsule),
                  patch('cytv.root_no_root_handoff.continuation', side_effect=AssertionError('status staged a gate'))):
                status = self.backend.live_status(coordinator, operation)
            self.assertEqual(status['state'], 'recovery_required')
            self.assertTrue(status['can_resume'])

    def test_explicit_handoff_resume_probes_original_and_refuses_unknown_vendor_terminal(self):
        from cytv.errors import UserError

        class ContinuationReached(BaseException):
            pass

        class InstallerFixture:
            def __init__(self, store):
                self.store = store

            def continue_no_root(self, expected):
                self.expected = expected
                raise ContinuationReached

        with tempfile.TemporaryDirectory() as temporary:
            coordinator = self.backend.Coordinator(Path(temporary).resolve() / 'operations')
            operation = 'a' * 32
            record = coordinator.reserve(operation, 'b' * 64, 'c' * 64)
            record.update(stage='packages')
            coordinator.write(record)
            store = coordinator.store(operation)
            profile = self.backend.PROFILE
            store.begin(profile, 'install', recovery_protocol=no_root_observer.PROTOCOL, capsule_sha256='d' * 64)
            pending = store.pending(profile)
            capsule = {'plan': {'root_handoff': {}, 'operation': 'e' * 32, 'action': 'install'}}
            installer = InstallerFixture(store)
            snapshot = {'reservation': 'active', 'configuration': {}, 'slots': [
                {'submission': 'claimed-possibly-submitted', 'terminal': 'none', 'readback': 'not-checked'}
            ]}
            with (coordinator.lock(create=True),
                  patch.object(self.backend, 'make_installer', return_value=installer),
                  patch.object(no_root_observer, 'capsule', return_value=capsule)):
                with patch('cytv.root_no_root_handoff.continuation', return_value='unprepared'):
                    with self.assertRaises(ContinuationReached):
                        self.backend.perform(coordinator, Path(temporary), record, resume=True)
                    self.assertEqual(installer.expected, pending)
                with (patch('cytv.root_no_root_handoff.continuation', return_value='observing'),
                      patch.object(no_root_observer, 'snapshot', return_value=snapshot)):
                    with self.assertRaises(UserError) as blocked:
                        self.backend.perform(coordinator, Path(temporary), record, resume=True)
            self.assertEqual(blocked.exception.reason_code, 'original-terminal-unverified')
            self.assertEqual(store.pending(profile), pending)

    def test_clean_root_handoff_selects_and_preserves_durable_observer_root(self):
        class CleanRootRemote:
            def run(self, command):
                return ''

        profile = {'host': 'localhost', 'edition': 'no-root', 'port': 22, 'connection': 'root-ssh'}
        installer = Installer(CleanRootRemote(), None, profile, '.', {}, homebrew_entry=True)
        stamp = dict(operation='a' * 32, removal='b' * 32, lease='c' * 32)
        installer._root_handoff = stamp
        private = no_root_observer.root_ssh_storage(installer)
        plan = no_root_observer.make_plan('d' * 32, 'e' * 32, 'install',
                                         {'helper.ipk': b'helper', 'launcher.ipk': b'home'},
                                         dict(zip(no_root_observer.APPS, ('1.0.0', '1.0.0'))),
                                         root_ssh=True, private_root=private, root_handoff=stamp)
        self.assertEqual(plan['root_handoff'], stamp)
        self.assertEqual(no_root_observer.private_root(plan), no_root_observer.ROOT_SSH_DISK)

    def test_homebrew_can_request_verified_clean_admission_without_changing_desktop_default(self):
        from cytv.errors import UserError

        def stop_after_admission(*, install, fresh_only):
            raise UserError('fresh' if fresh_only else 'verified clean')

        profile = {'host': 'localhost', 'edition': 'no-root', 'port': 22, 'connection': 'root-ssh'}
        installer = Installer(object(), None, profile, '.', {}, homebrew_entry=True)
        with patch.object(installer, 'preflight', side_effect=stop_after_admission):
            with self.assertRaisesRegex(UserError, 'fresh'):
                installer.check_no_root_alternative()
            with self.assertRaisesRegex(UserError, 'verified clean'):
                installer.check_no_root_alternative(allow_clean_root_handoff=True)

    def test_homebrew_observer_uses_disk_even_when_tmp_is_disk(self):
        class FreshRemote:
            def run(self, _):
                return ''

        profile = {'host': 'localhost', 'edition': 'no-root', 'port': 22, 'connection': 'root-ssh'}
        installer = Installer(FreshRemote(), None, profile, '.', {}, homebrew_entry=True)
        self.assertEqual(no_root_observer.root_ssh_storage(installer, ramfs=False),
                         no_root_observer.ROOT_SSH_DISK)


if __name__ == '__main__':
    unittest.main()

"""CLI recovery authenticates current support before reading a retained capsule."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv import cli, no_root_observer as observer, state


class RecoveryPayloadTests(unittest.TestCase):
    def test_saved_root_ssh_status_and_recovery_can_authenticate_handoff_support(self):
        for command in ('status', 'recover', 'doctor'):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                payload = root / 'payload'
                support = payload / 'installer-support/lifecycle-gate'
                support.parent.mkdir(parents=True)
                support.write_bytes(b'authenticated lifecycle gate fixture')
                cleanup = payload / 'root-updater/cleanup_tail.js'
                cleanup.parent.mkdir()
                cleanup.write_bytes(b'authenticated cleanup fixture')
                (cleanup.parent / 'bundle.json').write_text(json.dumps({'files': {
                    'cleanup_tail.js': hashlib.sha256(cleanup.read_bytes()).hexdigest()}}))
                files = {path.relative_to(payload).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in payload.rglob('*') if path.is_file()}
                (payload / 'payload.json').write_text(json.dumps({'files': files}))
                store = state.Store(root / 'state')
                profile = state.target('192.0.2.10', 'no-root', connection='root-ssh')
                store.save(profile)
                (store.device_dir(profile) / 'known_hosts').write_bytes(b'fixture original trust pin')
                operation = 'a' * 32
                store.begin(profile, 'uninstall', recovery_protocol=observer.PROTOCOL,
                            observer_operation=operation, expected={}, versions={})
                pending = store.pending(profile)
                plan = observer.make_plan(operation, pending['diagnostic_id'], 'remove', {}, {},
                    root_ssh=True, root_handoff={'operation': 'b' * 32, 'removal': 'c' * 32, 'lease': 'd' * 32})
                capsule = dict(schema=1, profile=profile, plan=plan, source=observer.source_for(True),
                               expected={}, artifacts={}, configuration={})
                digest = store.save_capsule(profile, operation, capsule)
                store.checkpoint(profile, capsule_sha256=digest)

                class Remote:
                    def run(self, command, **kwargs):
                        return 'v20.12.2' if command == '/usr/bin/node --version' else ''
                    def close(self): pass

                remote = Remote()
                lines, prompts = [], []
                def answer(prompt):
                    prompts.append(prompt)
                    return 'y' if 'Check recovery options?' in prompt else 'n'
                # Only the TV ownership read and hardware preflight are replaced.
                # Capsule validation, payload hashes and gate_bytes run for real.
                with patch('cytv.root_no_root_handoff.continuation', return_value='unclaimed'), \
                     patch('cytv.operations.Installer.preflight'):
                    result = cli.main([command, '--host', profile['host'], '--edition', 'no-root',
                        '--connection', 'root-ssh', '--language', 'en', '--data-dir', str(root / 'state')],
                        payload_root=payload, connect=lambda *_: remote, ask=answer, write=lines.append)
                self.assertEqual(result, 0, '\n'.join(lines))
                self.assertEqual(getattr(remote, '_cytv_root_handoff_support', None),
                                 ('authenticated cleanup fixture', b'authenticated lifecycle gate fixture'))
                if command == 'recover':
                    self.assertTrue(any('Continue the original No-root operation?' in prompt for prompt in prompts), lines)
                self.assertEqual(store.pending(profile)['capsule_sha256'], digest)

    def test_status_without_pending_support_work_needs_no_payload(self):
        class Remote:
            def run(self, command, **kwargs):
                if command == '/usr/bin/node --version': return 'v20.12.2'
                return 'CYTV_HELPER_IDLE' if 'CYTV_HELPER_IDLE' in command else ''
            def luna(self, *args, **kwargs): return {'apps': []}
            def close(self): pass

        for connection in (None, 'root-ssh'):
            with self.subTest(connection=connection), tempfile.TemporaryDirectory() as temporary:
                profile = state.target('192.0.2.10', 'no-root', connection=connection)
                state.Store(temporary).save(profile)
                lines = []
                argv = ['status', '--host', profile['host'], '--edition', 'no-root',
                        '--data-dir', temporary, '--language', 'en']
                if connection: argv += ['--connection', connection]
                result = cli.main(argv, payload_root=Path(temporary) / 'absent-payload',
                                  connect=lambda *_: Remote(), write=lines.append)
                self.assertEqual(result, 0, '\n'.join(lines))
                self.assertIn('"helper_state": "stopped"', '\n'.join(lines))

"""Legacy choices must preserve recovery and authentication boundaries."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cytv import state
from cytv.errors import UserError


class RuntimeChoices(unittest.TestCase):
    def test_verified_clean_root_removal_can_enter_no_root_preflight_without_python(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote as FixtureRemote
        class Remote(FixtureRemote):
            root=True
            def run(self,command,**kw):
                if 'CYTV_FRESH_ROOT' in command:return 'CYTV_RETAINED_ROOT'
                return super().run(command,**kw)
        remote=Remote();installer=Installer(remote,None,state.target('192.0.2.10','no-root',connection='root-ssh'),'.',{})
        stamp=dict(operation='a'*32,removal='b'*32,lease='c'*32)
        with patch('cytv.root_no_root_handoff.probe',return_value=stamp):
            installer.preflight(install=True)
        self.assertEqual(installer._root_handoff,stamp)
        self.assertFalse(any('python' in call[1] for call in remote.calls if call[0]=='run'))

    def test_direct_no_root_root_ssh_install_cannot_bypass_retained_root_state(self):
        from cytv.operations import Installer
        class Remote:
            root=True
            def run(self, command, **kw):
                return 'CYTV_RETAINED_ROOT'
        installer=Installer(Remote(),None,state.target('192.0.2.10','no-root',connection='root-ssh'),'.',{})
        with self.assertRaisesRegex(UserError,'Previous Root installation needs recovery'):
            installer.preflight(install=True)

    @unittest.skipIf(os.name == 'nt', 'TV shell fixture requires POSIX paths')
    def test_unavailable_vendor_probe_is_a_result_not_an_ssh_failure(self):
        from cytv.root_runtime import VENDOR_PROBE, FRESH_PROBE
        import subprocess
        # These TV paths are absent on the host. Lack of capability is distinct
        # from the SSH command failing or losing the connection.
        result=subprocess.run(['sh','-c',VENDOR_PROBE],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout,'CYTV_VENDOR_UNAVAILABLE')
        with tempfile.TemporaryDirectory() as tmp:
            retained=FRESH_PROBE.replace('/var/lib/clean-your-tv-root ',tmp+' ')
            result=subprocess.run(['sh','-c',retained],capture_output=True,text=True)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout,'CYTV_RETAINED_ROOT')
            package=Path(tmp)/'applications/com.cleanyourtv.root.preview'
            package.mkdir(parents=True)
            retained=FRESH_PROBE.replace('/media/developer/apps/usr/palm',tmp)
            result=subprocess.run(['sh','-c',retained],capture_output=True,text=True)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout,'CYTV_RETAINED_ROOT')

    def test_choice_cancel_yes_flag_and_fallback_preserve_transport(self):
        from cytv.root_runtime import offer
        from cytv.checks import CheckList
        from cytv.terminal import Console
        class Remote:
            root = True
            def run(self, command, **kw):
                return 'v0.12.2' if command == '/usr/bin/node --version' else 'CYTV_FRESH_ROOT'
        for answer in ('', '1', '2'):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as tmp:
                store = state.Store(tmp)
                profile = state.target('192.0.2.10', 'root', 2222, '/private/tmp/example-key')
                store.save(profile)
                state.private_write(store.device_dir(profile)/'known_hosts', b'PINNED-IDENTITY')
                installer = SimpleNamespace(store=store, profile=profile, remote=Remote(), manifest={}, tv_info={},
                                             checks=CheckList(), use_runtime_variant=lambda:None)
                args = SimpleNamespace(non_interactive=False, yes=True)
                if answer == '1':
                    offer(installer, args, lambda _:answer, Console(lambda _:None))
                    self.assertEqual(profile['edition'], 'no-root')
                    self.assertEqual(profile['connection'], 'root-ssh')
                    self.assertEqual(profile['port'], 2222)
                    self.assertEqual((store.device_dir(profile)/'known_hosts').read_bytes(), b'PINNED-IDENTITY')
                else:
                    # No embedded Beta: arbitrary selection cannot choose it; cancel remains default.
                    with self.assertRaises(EOFError):
                        offer(installer, args, lambda _:'', Console(lambda _:None))
                    self.assertEqual(profile['edition'], 'root')
                    self.assertIsNone(store.pending(profile))
                self.assertEqual(installer.tv_info.get('node_version'), '0.12.2')
                self.assertEqual(installer.tv_info.get('node_version_status'), 'read')

    def test_explicit_beta_needs_second_confirmation(self):
        from cytv.root_runtime import offer
        from cytv.checks import CheckList
        from cytv.terminal import Console
        class Remote:
            def run(self, command, **kw):
                return 'v0.12.2' if command == '/usr/bin/node --version' else 'CYTV_FRESH_ROOT'
        for accepted in ('', 'y'):
            with tempfile.TemporaryDirectory() as tmp:
                profile = state.target('192.0.2.10', 'root')
                store = state.Store(tmp)
                selected = []
                installer = SimpleNamespace(store=store, profile=profile, remote=Remote(), tv_info={},
                    manifest={'legacy_root_beta':'legacy-root-beta'}, checks=CheckList(),
                    use_runtime_variant=lambda:selected.append(True))
                answers = iter(['2', accepted])
                if accepted:
                    offer(installer, SimpleNamespace(non_interactive=False), lambda _:next(answers), Console(lambda _:None))
                    self.assertEqual(profile['root_variant'], 'node012-beta')
                    self.assertTrue(selected)
                else:
                    with self.assertRaises(EOFError):
                        offer(installer, SimpleNamespace(non_interactive=False), lambda _:next(answers), Console(lambda _:None))
                    self.assertNotIn('root_variant', profile)
                    self.assertFalse(selected)

    def test_no_root_root_ssh_roundtrips_without_becoming_developer_mode(self):
        profile = state.target('192.0.2.10', 'no-root', connection='root-ssh')
        self.assertEqual(profile['port'], 22)
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            store.save(profile)
            self.assertEqual(store.profiles(), [profile])
            self.assertNotEqual(store.device_dir(profile), store.device_dir(state.target('192.0.2.10', 'no-root', 22)))
        self.assertEqual(state.target(**profile), profile)

    def test_beta_choice_keeps_root_operation_identity(self):
        normal = state.target('192.0.2.10', 'root')
        beta = state.target(**normal, root_variant='node012-beta')
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            store.begin(normal, 'install')
            self.assertEqual(store.pending(beta), store.pending(normal))

    def test_invalid_combinations_are_refused(self):
        for edition, extra in [('no-root', {'root_variant':'node012-beta'}),
                               ('root', {'connection':'root-ssh'}),
                               ('root', {'root_variant':'anything'}),
                               ('no-root', {'connection':'anything'})]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                state.target('192.0.2.10', edition, **extra)

    def test_only_exact_0122_is_eligible_for_beta(self):
        from cytv.root_runtime import alternatives
        for value, expected in [('v0.12.2', ('no-root', 'node012-beta')),
                                ('v0.12.1', ('no-root',)), ('v4.9.1', ('no-root',)),
                                ('v8.12.0', ()), ('v22.1.0', ()), ('', ()),
                                ('v0.12.2\nPRIVATE', ()), ('v0.12.2-extra', ())]:
            with self.subTest(value=value):
                self.assertEqual(alternatives(value), expected)

    def test_other_edition_pending_operation_prevents_choice(self):
        from cytv.root_runtime import require_idle
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            root = state.target('192.0.2.10', 'root')
            other = state.target(root['host'], 'no-root')
            store.save(other)
            store.begin(other, 'install')
            with self.assertRaises(UserError):
                require_idle(store, root)

    def test_root_ssh_uses_root_auth_without_developer_key(self):
        from cytv.transport import SSH
        import paramiko
        profile = state.target('192.0.2.10', 'no-root', connection='root-ssh')
        key = paramiko.RSAKey.generate(1024)
        with tempfile.TemporaryDirectory() as tmp, patch('paramiko.SSHClient') as cls, \
             patch('cytv.transport.developer_key', side_effect=AssertionError('Developer Mode requested')), \
             patch('cytv.transport.root_auth', return_value='root-auth'):
            cls.return_value.get_host_keys.return_value = paramiko.HostKeys()
            remote = SSH.connect(profile, tmp, lambda _: '', lambda *_: True)
            self.assertTrue(remote.root)
            options = cls.return_value.connect.call_args.kwargs
            self.assertEqual(options['username'], 'root')
            self.assertEqual(options['auth_strategy'], 'root-auth')

    def test_root_observer_binds_private_sender_and_safe_staging(self):
        from cytv import no_root_observer as observer
        import json, shlex
        plan = observer.make_plan('a'*32, 'b'*32, 'install',
                                 {'helper.ipk':b'a', 'launcher.ipk':b'b'},
                                 dict(zip(observer.APPS, ['1.0.0', '1.0.0'])), root_ssh=True)
        class Remote:
            root = True
            def run(self, command, **kwargs):
                self.request = json.loads(shlex.split(command)[-1])
                return json.dumps({'operation':'a'*32})
        remote = Remote()
        observer.invoke(remote, plan, 'storage-check')
        self.assertEqual(remote.request['sender'], '/usr/bin/luna-send')
        self.assertEqual(remote.request['root'], '/tmp/.cytv-installer-root')
        self.assertEqual(remote.request['public_root'], '/var/lib/clean-your-tv-installer')
        self.assertIn('/var/lib/clean-your-tv-installer/', json.loads(plan['slots'][0]['request'])['ipkUrl'])
        remote.root = False
        with self.assertRaises(UserError):
            observer.invoke(remote, plan, 'storage-check')


if __name__ == '__main__':
    unittest.main()

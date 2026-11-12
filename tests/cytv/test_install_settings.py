"""Installation choices stay within their edition and use confirmed service writes."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from cytv import install_settings as settings


class SettingsTests(unittest.TestCase):
    def test_initial_switch_value_comes_from_status_without_writes(self):
        for profile, reply, expected in [
            ({'edition':'root'}, {'returnValue':True,'root':True,'blockUpdates':True}, {'block_updates':True}),
            ({'edition':'no-root'}, {'returnValue':True,'state':{'enabled':False}}, {'renewal':False}),
            ({'edition':'root'}, {'returnValue':False}, {}),
            ({'edition':'no-root','connection':'root-ssh'}, {}, {})
        ]:
            remote=MagicMock();remote.luna.return_value=reply
            value=settings.read_current(SimpleNamespace(profile=profile,remote=remote))
            self.assertEqual(value,expected)
            self.assertFalse(any('setConfiguration' in call.args[0] or call.args[0].endswith(('/enable','/disable')) for call in remote.luna.call_args_list))

    def test_appearance_uses_launch_params_without_reinstalling_for_all_modes(self):
        for profile, app in [({'edition':'root'}, 'com.cleanyourtv.root.preview'),
                             ({'edition':'no-root'}, 'com.gathin.tvhome'),
                             ({'edition':'no-root','connection':'root-ssh'}, 'com.gathin.tvhome')]:
            remote = MagicMock()
            remote.luna.return_value = {'returnValue': True}
            installer = SimpleNamespace(remote=remote, profile=profile, tv_info={})
            settings.apply_services(installer, {'theme':'classic','weather':True}, lambda *_:None)
            uri, payload = remote.luna.call_args.args
            self.assertEqual(uri, 'com.webos.applicationManager/launch')
            self.assertEqual(payload['id'], app)
            self.assertEqual(payload['params']['cytvSetup']['theme'], 'classic')
            self.assertEqual(installer.tv_info['installation_settings']['weather'], 'requested-in-home')

    def test_customization_is_requested_only_after_successful_install(self):
        from cytv import cli, debloat
        from cytv.desktop import DesktopConsole
        for install_error, cancel in ((None, None), (None, EOFError), (None, KeyboardInterrupt), (RuntimeError('install failed'), None)):
            with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as cls, patch('cytv.cli.package.verify_payload', return_value={}):
                cls.return_value.install.side_effect = install_error
                cls.return_value.install.return_value = {}
                cls.return_value.version_summary.return_value = []
                questions = []
                def ask(prompt):
                    questions.append(prompt)
                    self.assertTrue(cls.return_value.install.called)
                    self.assertIsNone(install_error)
                    if prompt == debloat.SELECT:
                        return '[]'
                    self.assertEqual(prompt, settings.PROMPT)
                    if cancel:
                        raise cancel
                    return '{}'
                result = cli.main(['install','--host','192.0.2.10','--edition','root','--yes',
                    '--migrate-home','--language','en','--data-dir',tmp], ask=ask,
                    write=DesktopConsole(lambda *_:None), connect=lambda *_:MagicMock(), payload_root=Path(tmp))
                self.assertEqual(result, 0 if install_error is None else 1)
                self.assertEqual(questions, [debloat.SELECT, settings.PROMPT] if install_error is None else [])

    def test_android_off_and_skip_are_explicit_choices_not_dialog_cancellation(self):
        from cytv import i18n
        from cytv.terminal import Console
        self.addCleanup(i18n.set_language, i18n.language_choice())
        i18n.set_language('en')

        class Android(Console):
            frontend = 'android'
            def __init__(self):
                super().__init__(lambda *_: None)
                self.options = []
            def option(self, key, label, detail=''):
                self.options.append(str(key))
        output = Android()
        def ask(prompt):
            options, output.options = output.options, []
            if 'Customize' in prompt:
                self.assertIn('n', options, 'Android must offer a non-cancelling skip')
                return 'y'
            if 'Theme' in prompt:
                return '1'
            if 'auto-renewal' in prompt:
                self.assertIn('0', options)
                self.assertIn('2', options)
                return '0'
            self.assertIn('n', options, 'Android must offer an explicit off choice')
            return 'n'
        result = settings.collect({'edition': 'no-root'}, ask, output)
        self.assertEqual(result, {'theme': 'classic', 'weather': False})

    def test_diagnostics_keep_only_known_setting_results(self):
        from cytv.diagnostic_context import tv_summary
        safe = tv_summary({'installation_settings': {'theme': 'requested-in-home',
            'renewal': 'unconfirmed', 'private': 'PRIVATE', 'weather': 'PRIVATE'}})
        self.assertEqual(safe['installation_settings'], {'theme': 'requested-in-home', 'renewal': 'unconfirmed', 'weather': 'unknown'})

    def test_wrong_mode_and_invalid_values_are_rejected_before_writes(self):
        for profile, value in [
            ({'edition': 'root'}, {'renewal': True}),
            ({'edition': 'no-root', 'connection': 'root-ssh'}, {'renewal': True}),
            ({'edition': 'no-root'}, {'block_updates': True}),
            ({'edition': 'root'}, {'theme': 'external'}),
            ({'edition': 'root'}, {'weather': 1}),
            ({'edition': 'root'}, {'theme': 'ribbon', 'weather': True}),
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                settings.validate(value, profile)

    def test_firmware_change_is_partial_and_read_back(self):
        class Remote:
            root = True
            def __init__(self): self.value = False; self.calls = []
            def luna(self, uri, payload, **kwargs):
                self.calls.append((uri, payload))
                if uri.endswith('/setConfiguration'): self.value = payload['blockUpdates']
                return {'returnValue': True, 'root': True, 'blockUpdates': self.value}
        remote = Remote()
        installer = SimpleNamespace(remote=remote, profile={'edition': 'root'}, tv_info={})
        settings.apply_services(installer, {'block_updates': True}, lambda *_: None)
        self.assertIn(('org.webosbrew.hbchannel.service/setConfiguration', {'blockUpdates': True}), remote.calls)
        self.assertTrue(remote.calls[-1][0].endswith('/getConfiguration'))
        self.assertEqual(installer.tv_info['installation_settings']['block_updates'], 'saved-restart-required')

    def test_unconfirmed_renewal_is_reported_without_retry_or_install_failure(self):
        class Remote:
            def __init__(self): self.calls = []
            def luna(self, uri, payload, **kwargs):
                self.calls.append(uri)
                return {'returnValue': True, 'state': {'enabled': True, 'error': 'schedule-unavailable'}}
        remote = Remote()
        installer = SimpleNamespace(remote=remote, profile={'edition': 'no-root'}, tv_info={})
        output = []
        settings.apply_services(installer, {'renewal': True}, output.append)
        self.assertEqual(len(remote.calls), 1)
        self.assertEqual(installer.tv_info['installation_settings']['renewal'], 'unconfirmed')
        self.assertTrue(output)

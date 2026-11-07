import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/python/android_bridge.py'


class BridgeTests(unittest.TestCase):
    def test_selected_profile_event_preserves_choices_without_identity_paths(self):
        module = self.module()
        class Native:
            def __init__(self): self.events=[]
            def emit(self, raw): self.events.append(json.loads(raw))
        native=Native()
        console=module.AndroidConsole(module.Callbacks(native))
        console.selected_profile({'host':'192.0.2.10','port':2222,'edition':'no-root',
                                  'connection':'root-ssh','identity':'PRIVATE'})
        event=native.events[-1]
        self.assertEqual(event['kind'],'selected-profile')
        self.assertEqual(event['profile']['connection'],'root-ssh')
        self.assertNotIn('PRIVATE',json.dumps(event))
        args=module.arguments(event['profile']|{'language':'en'},'/private/profiles')
        self.assertIn('--connection',args)
        self.assertIn('root-ssh',args)

    def test_uninstall_is_an_explicit_supported_action(self):
        module = self.module()
        args = module.arguments({'host':'192.0.2.10', 'edition':'no-root',
                                 'action':'uninstall', 'language':'en'}, '/private/profiles')
        self.assertEqual(args[0], 'uninstall')
        self.assertNotIn('--yes', args)

    def test_recovery_result_preserves_fixed_disposition_and_verified_cleanup(self):
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
        native = Native()
        console = module.AndroidConsole(module.Callbacks(native))
        console.recovery_plan({'state':'complete','disposition':'clean-removal','verified_clean':True,
                               'summary':'Clean Your TV removal is verified.','next_step':'Other TV apps stay installed.',
                               'private':'PRIVATE-ORIGINAL-RECEIPT'})
        self.assertEqual(native.events[-1]['disposition'], 'clean-removal')
        self.assertTrue(native.events[-1]['verified_clean'])
        self.assertNotIn('PRIVATE', json.dumps(native.events))

    def test_cleanup_details_are_localized_and_never_forward_unknown_codes(self):
        from cytv import i18n
        self.addCleanup(i18n.set_language, 'en')
        i18n.set_language('en')
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
        native = Native()
        console = module.AndroidConsole(module.Callbacks(native))
        console.recovery_plan({'state':'blocked','disposition':'clean-removal',
            'summary':'Removal is still in progress.','next_step':'Continue the remaining cleanup for this TV.',
            'actions':['continue-removal','PRIVATE'], 'reason':'PRIVATE',
            'removal':{'stage':'private-cleanup','reason':'private-cleanup-incomplete','private':'PRIVATE'}})
        event = native.events[-1]
        self.assertEqual(event['stageText'], 'Removing private setup data…')
        self.assertEqual(event['blockerText'], 'Some project files remain. Try again to finish removal.')
        self.assertEqual(event['actions'], ['continue-removal'])
        self.assertNotIn('PRIVATE', json.dumps(event))

    def test_restart_semantics_are_forwarded_without_relying_on_translated_stage(self):
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
        native = Native()
        console = module.AndroidConsole(module.Callbacks(native))
        for value in ({'removal':{'stage':'restart-required'}}, {'restart_required':False,'reason':'restart-required'}):
            console.recovery_plan({'state':'complete','disposition':'clean-removal',
                'removed':True,'verified_clean':True,'summary':'Clean Your TV removal is verified.',
                'next_step':'Try again',**value})
            self.assertIs(native.events[-1].get('restart_required'), True)

    def test_check_events_translate_text_but_preserve_ids_and_status(self):
        from cytv import i18n
        self.addCleanup(i18n.set_language, 'en')
        i18n.set_language('ru')
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
        native = Native()
        console = self.module().AndroidConsole(self.module().Callbacks(native))
        self.assertNotEqual(type(console).check, __import__('cytv.terminal', fromlist=['Console']).Console.check,
                            'Android must emit semantic checks')
        console.check({'id':'ssh', 'label':'SSH connection and sign-in', 'status':'pass', 'detail':''})
        event = native.events[-1]
        self.assertEqual((event['kind'], event['checkId'], event['status']), ('check', 'ssh', 'pass'))
        self.assertNotEqual(event['label'], 'SSH connection and sign-in')
        self.assertNotEqual(event['statusText'], 'Passed')

    def test_recovery_is_explicit_and_emits_safe_plan_and_default_no(self):
        module = self.module()
        args = module.arguments({'host':'192.0.2.10', 'edition':'no-root', 'action':'recover'}, '/private/profiles')
        self.assertEqual(args[0], 'recover')
        self.assertNotIn('--yes', args)
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
            def request(self, raw):
                self.events.append(json.loads(raw)); return 'n'
        native = Native(); callbacks = module.Callbacks(native)
        module.AndroidConsole(callbacks).recovery({'host':'PRIVATE-TARGET'})
        event = native.events[-1]
        self.assertEqual((event['kind'], event['state']), ('recovery-plan', 'review'))
        self.assertNotIn('PRIVATE-TARGET', json.dumps(native.events))
        callbacks.ask('Remove remaining Clean Your TV packages? [y/N]: ')
        self.assertTrue(native.events[-1]['defaultNo'])

    def test_home_observation_choices_are_semantic_and_default_to_skip(self):
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
            def request(self, raw): self.events.append(json.loads(raw)); return '3'
        native = Native(); callbacks = module.Callbacks(native)
        console = module.AndroidConsole(callbacks)
        console.option(1, 'Clean Your TV Home opened')
        console.option(2, 'LG Home opened or Home did not work')
        console.option(3, 'Not tested / skip')
        callbacks.ask('Home button result [3]: ')
        question = native.events[-1]
        self.assertEqual([x['value'] for x in question['options']], ['1','2','3'])
        self.assertEqual(question['defaultChoice'], '3')
        callbacks.ask('Unrelated question [y/N]: ')
        self.assertNotIn('options', native.events[-1])

    def test_failure_help_is_localized_semantic_advice_without_profile_data(self):
        from cytv import i18n
        from cytv.failure_help import for_error
        self.addCleanup(i18n.set_language,'en');i18n.set_language('ru')
        module=self.module()
        class Native:
            def __init__(self):self.events=[]
            def emit(self,raw):self.events.append(json.loads(raw))
        for edition in ('root', 'no-root'):
            with self.subTest(edition=edition):
                native=Native();console=module.AndroidConsole(module.Callbacks(native))
                guide=for_error(TimeoutError('PRIVATE-PASSWORD'),'ssh-connect',
                                {'edition':edition,'host':'PRIVATE-HOST'}, {'action':'install'})
                console.failure_help(guide)
                event=native.events[-1]
                self.assertEqual((event['kind'],event['code']),('failure-help','ssh-timeout'))
                self.assertTrue(event['pending']);self.assertFalse(event['canEditConnection'])
                self.assertNotEqual(event['title'],guide['title'])
                self.assertNotIn('PRIVATE',json.dumps(native.events))

    def test_recovery_failure_advice_keeps_private_data_out_and_offers_only_inspection(self):
        from cytv import cli, state, i18n
        from cytv.errors import TVRejected, UserError
        import tempfile
        self.addCleanup(i18n.set_language, 'en'); i18n.set_language('es')
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
        with tempfile.TemporaryDirectory() as tmp:
            profile = state.target('192.0.2.10', 'no-root', 9923)
            store = state.Store(tmp); store.begin(profile, 'uninstall')
            native = Native(); console = module.AndroidConsole(module.Callbacks(native))
            cli.explain_failure(console, store, profile, 'uninstall', UserError('PRIVATE'))
            guide = next(e for e in native.events if e['kind'] == 'failure-help')
            self.assertEqual(guide['code'], 'removal-not-submitted')
            self.assertEqual(native.events[-1]['state'], 'review')
            self.assertNotIn('PRIVATE', json.dumps(native.events))
            self.assertNotIn('192.0.2.10', json.dumps(native.events))
            # Uncertain operations must expose the blocker, never another review action.
            store.checkpoint(profile, stage='removing')
            native.events.clear()
            error = TVRejected('PRIVATE', {'returnValue': False, 'errorCode': -1}, 'com.webos.appInstallService/status')
            cli.explain_failure(console, store, profile, 'recover', error)
            guide = next(e for e in native.events if e['kind'] == 'failure-help')
            self.assertEqual(guide['code'], 'recovery-status-rejected')
            self.assertFalse(guide['canEditConnection'])
            self.assertFalse(any(e['kind'] == 'recovery-plan' for e in native.events))
            self.assertNotIn('PRIVATE', json.dumps(native.events))

    def test_cli_errors_reach_android_as_error_events(self):
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
        native = Native()
        console = module.AndroidConsole(module.Callbacks(native))
        console.error('Could not complete this step', heading=True)
        console.error('Failure details')
        self.assertEqual([event['kind'] for event in native.events], ['error', 'error'])
        self.assertEqual(native.events[-1]['text'], 'Failure details')

    def module(self):
        self.assertTrue(SOURCE.exists(), 'Android Python adapter is not implemented')
        spec = importlib.util.spec_from_file_location('android_bridge', SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_rejects_invalid_or_unapproved_commands_before_connecting(self):
        module = self.module()
        for request in ({'host': 'bad;cmd', 'edition': 'root'},
                        {'host': '192.168.1.2', 'edition': 'root', 'action': 'force-delete'},
                        {'host': '192.168.1.2', 'edition': 'other'},
                        {'host': '192.168.1.2', 'edition': 'root', 'port': 0}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                module.arguments(request, '/private/profiles')

    def test_diagnostics_command_and_report_export_event(self):
        module = self.module()
        self.assertEqual(module.arguments({'host':'192.168.1.2','edition':'no-root','action':'home-diagnostics'}, '/private/profiles')[0], 'home-diagnostics')
        class Native:
            def __init__(self): self.events=[]
            def emit(self, raw): self.events.append(json.loads(raw))
        with tempfile.TemporaryDirectory() as tmp:
            native=Native();reports=Path(tmp)/'reports';reports.mkdir()
            report=reports/'diagnostic-123456abcdef.json';report.write_text('{}')
            callbacks=module.Callbacks(native,directory=tmp)
            callbacks.write('  '+str(report))
            self.assertEqual(native.events[0],{'kind':'report-ready','name':report.name})
            native.events.clear();other=Path(tmp)/'private.json';other.write_text('{}')
            callbacks.write(str(other))
            self.assertFalse(any(e['kind']=='report-ready' for e in native.events))

    def test_edition_defaults_and_identity_path(self):
        module = self.module()
        args = module.arguments({'host': '192.168.1.2', 'edition': 'no-root'}, '/private/profiles')
        self.assertIn('9922', args)
        self.assertNotIn('--yes', args)
        self.assertNotIn('--non-interactive', args)
        args = module.arguments({'host': '192.168.1.2', 'edition': 'root', 'action': 'restore'}, '/private/profiles', '/private/key')
        self.assertEqual(args[0], 'restore')
        self.assertEqual(args[args.index('--identity') + 1], '/private/key')

    def test_all_desktop_languages_reach_cli_and_unknown_values_are_rejected(self):
        from cytv.i18n import LANGUAGES
        module = self.module()
        for language in LANGUAGES.keys() - {'auto'}:
            args = module.arguments({'host': '192.168.1.2', 'edition': 'root', 'language': language}, '/private/profiles')
            self.assertEqual(args[args.index('--language') + 1], language)
        for language in ('auto', 'unknown', ''):
            with self.assertRaises(ValueError):
                module.arguments({'host': '192.168.1.2', 'edition': 'root', 'language': language}, '/private/profiles')

    def test_translated_secret_requests_retain_semantic_type(self):
        from cytv import i18n
        from cytv.terminal import Console
        module = self.module()
        class Callbacks:
            def __init__(self): self.events = []
            def request(self, value): self.events.append(json.loads(value)); return 'secret'
        native = Callbacks()
        try:
            for language in i18n.LANGUAGES.keys() - {'auto'}:
                i18n.set_language(language)
                for prompt, kind in [('SSH key passphrase: ', 'key'), ('Root SSH password (hidden): ', 'root'), ('Developer Mode passphrase: ', 'developer')]:
                    for text in (prompt, Console(interactive=False).prompt(prompt)):
                        module.Callbacks(native).secret(text)
                        self.assertEqual(native.events[-1]['secretType'], kind)
        finally:
            i18n.set_language('en')

    def test_typed_secret_survives_cli_localization_in_every_locale(self):
        from cytv import cli, i18n
        from cytv.transport import CredentialPrompt
        module = self.module()
        self.addCleanup(i18n.set_language, 'en')
        class Native:
            def __init__(self): self.events = []
            def request(self, raw): self.events.append(json.loads(raw)); return 'PRIVATE-SECRET'
        native = Native()
        def secret(prompt):
            self.assertIsInstance(prompt, CredentialPrompt)
            return module.Callbacks(native).secret(prompt)
        def connect(profile, directory, secret, trust):
            for text, kind in [('SSH key passphrase: ', 'key'), ('Root SSH password (hidden): ', 'root'),
                               ('Developer Mode passphrase: ', 'developer')]:
                secret(CredentialPrompt(text, kind))
            raise EOFError
        with tempfile.TemporaryDirectory() as tmp:
            for language in set(i18n.LANGUAGES) - {'auto'}:
                with self.subTest(language=language):
                    native.events.clear(); output = []
                    code = cli.main(['status', '--host', '192.0.2.10', '--edition', 'root',
                                     '--data-dir', tmp, '--language', language], connect=connect,
                                    secret=secret, write=output.append)
                    self.assertEqual(code, 130)
                    self.assertEqual([e['secretType'] for e in native.events], ['key', 'root', 'developer'])
                    if language != 'en':
                        self.assertNotIn('Root SSH password (hidden)', native.events[1]['text'])
                    self.assertNotIn('PRIVATE-SECRET', json.dumps(native.events) + '\n'.join(output))

    def test_explicit_secret_type_is_authoritative_and_unsupported_types_are_refused(self):
        from cytv.transport import CredentialPrompt
        from unittest.mock import Mock
        native = Mock(); native.request.return_value = 'secret'
        callbacks = self.module().Callbacks(native)
        prompt = CredentialPrompt('Developer Mode passphrase: ', 'root')
        callbacks.secret(prompt)
        self.assertEqual(json.loads(native.request.call_args.args[0])['secretType'], 'root')
        native.reset_mock()
        for kind in ('unknown', '', None):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    CredentialPrompt('hidden', kind)
                prompt.credential_type = kind
                with self.assertRaises(ValueError):
                    callbacks.secret(prompt)
        native.request.assert_not_called()

    def test_progress_events_use_source_messages_before_translation(self):
        from cytv import i18n
        module = self.module()
        class Native:
            def __init__(self): self.events = []
            def emit(self, value): self.events.append(json.loads(value))
        native = Native()
        try:
            for language in i18n.LANGUAGES.keys() - {'auto'}:
                i18n.set_language(language)
                native.events.clear()
                console = module.AndroidConsole(module.Callbacks(native))
                for message in ('Read 18 applications.', 'Installing Home Helper…', 'Configuring Home Helper…'):
                    console(message)
                self.assertEqual([e['stage'] for e in native.events if e['kind'] == 'stage'], [1, 2, 3])
        finally:
            i18n.set_language('en')

    def test_secrets_are_requested_without_echo_and_trust_is_explicit(self):
        module = self.module()
        class Callbacks:
            def __init__(self): self.events = []; self.answers = iter(['sensitive', 'no', 'yes'])
            def emit(self, value): self.events.append(json.loads(value))
            def request(self, value): self.events.append(json.loads(value)); return next(self.answers)
        callbacks = Callbacks()
        adapter = module.Callbacks(callbacks)
        self.assertEqual(adapter.secret('Passphrase:'), 'sensitive')
        self.assertFalse(adapter.trust('SHA256:test', True))
        self.assertTrue(adapter.trust('SHA256:test', True))
        self.assertNotIn('sensitive', json.dumps(callbacks.events))
        self.assertEqual(callbacks.events[0]['kind'], 'secret')
        self.assertEqual(callbacks.events[1]['fingerprint'], 'SHA256:test')

    def test_dispatch_injects_payload_and_does_not_report_cancel_as_success(self):
        module = self.module()
        class Callbacks:
            def __init__(self): self.events = []
            def emit(self, value): self.events.append(json.loads(value))
        callbacks = Callbacks()
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.main', return_value=130) as main:
            module.run(json.dumps({'host': '192.168.1.2', 'edition': 'root'}), tmp, '/payload', '', callbacks)
            self.assertEqual(main.call_args.kwargs['payload_root'], '/payload')
            self.assertEqual(callbacks.events[-1]['kind'], 'finished')
            self.assertEqual(callbacks.events[-1]['code'], 130)

    def test_cancelled_prompt_stops_before_connecting(self):
        module = self.module()
        class Callbacks:
            def request(self, value): return None
        with self.assertRaises(EOFError):
            module.Callbacks(Callbacks()).secret('Passphrase:')

    def test_password_choice_does_not_reuse_an_older_saved_key(self):
        module = self.module()
        profile = {'host': '192.168.1.2', 'edition': 'root', 'port': 22, 'identity': '/older/key'}
        adapter = module.Callbacks(object())
        with patch.object(module.SSH, 'connect') as connect:
            adapter.connect(profile, '/private', lambda _: '', lambda *_: False)
            self.assertNotIn('identity', connect.call_args.args[0])

    def test_cli_verifies_injected_payload_without_using_desktop_directory(self):
        from cytv import cli
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'public.txt').write_bytes(b'public')
            (path / 'payload.json').write_text(json.dumps({'files': {'public.txt': hashlib.sha256(b'public').hexdigest()}}))
            output = []
            with patch('cytv.cli.payload_dir', side_effect=AssertionError('Desktop payload path accessed')):
                code = cli.main(['--check-payload', '--data-dir', str(path / 'profiles'), '--language', 'en'],
                                payload_root=path, write=output.append)
            self.assertEqual(code, 0)
            self.assertIn('Embedded payload verified', '\n'.join(output))


if __name__ == '__main__': unittest.main()

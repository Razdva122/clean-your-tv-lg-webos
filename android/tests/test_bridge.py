import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/python/android_bridge.py'


class BridgeTests(unittest.TestCase):
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
                        {'host': '192.168.1.2', 'edition': 'root', 'action': 'uninstall'},
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
                    module.Callbacks(native).secret(Console(interactive=False).prompt(prompt))
                    self.assertEqual(native.events[-1]['secretType'], kind)
        finally:
            i18n.set_language('en')

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

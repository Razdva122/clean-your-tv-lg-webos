import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/python/android_bridge.py'


class BridgeTests(unittest.TestCase):
    def test_staged_bridge_dispatches_cli_without_checkout_modules(self):
        from android import stage

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(stage.ROOT / 'cytv', root / 'cytv', ignore=shutil.ignore_patterns('__pycache__'))
            for name in ('lgtv.py', 'release-versions.json'):
                shutil.copy2(stage.ROOT / name, root)
            (root / 'build/cytv/payload').mkdir(parents=True)
            (root / 'build/cytv/payload/payload.json').write_text('{}')
            with (patch.object(stage, 'ROOT', root),
                  patch.object(stage, 'verify_payload', return_value={'files': {}}),
                  patch.object(stage.subprocess, 'check_output', return_value='test')):
                stage.main()
            source = root / 'android/app/build/generated/python'
            shutil.copy2(SOURCE, source / SOURCE.name)
            result = subprocess.run([
                sys.executable, '-I', '-c', """
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source))
import android_bridge

code = android_bridge.cli.main(["--version"])
for name, module in sys.modules.items():
    if name in ("android_bridge", "cytv", "lgtv") or name.startswith("cytv."):
        assert Path(module.__file__).resolve().is_relative_to(source), (name, module.__file__)
raise SystemExit(code)
""", str(source)
            ], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r'^cytv \S+\n$')

    def test_storage_retry_rechecks_only_the_failed_read_before_confirming_setup(self):
        import shlex
        from cytv import i18n
        from tests.cytv.test_desktop_recovery import DesktopRecoveryTests

        fixture = DesktopRecoveryTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.store.finish(fixture.profile)
        original_run = fixture.remote.run
        checks = []

        def run(command, **kwargs):
            if command.startswith('unset NODE_OPTIONS NODE_PATH && /usr/bin/node -e '):
                args = shlex.split(command)
                request = json.loads(args[-1]) if args[-1].startswith('{') else {}
                if request.get('command') in ('storage-select', 'storage-check'):
                    checks.append(request['command'])
                    if checks == ['storage-select', 'storage-check']:
                        return 'MALFORMED'
            return original_run(command, **kwargs)

        class Native:
            def __init__(self):
                self.questions = []
                self.errors = []

            def emit(self, raw):
                event = json.loads(raw)
                if event['kind'] == 'error':
                    self.errors.append(event['text'])

            def request(self, raw):
                event = json.loads(raw)
                self.questions.append(event)
                return 'n' if checks == ['storage-select', 'storage-check', 'storage-check'] else 'y'

        fixture.remote.run = run
        bridge = self.module()
        native = Native()
        config = dict(fixture.profile, action='install', language='ru')
        with patch.object(bridge.SSH, 'connect', side_effect=lambda profile, *_args, **_kwargs: fixture.connect(profile)):
            code = bridge.run(json.dumps(config), fixture.root, fixture.payload, '', native)
        retry = next((q for q in native.questions if q.get('reason') == 'storage-preflight-failed'), None)
        self.assertIsNotNone(retry, (checks, native.errors))
        self.assertEqual(retry['actions'], ['retry-storage-check'])
        self.assertEqual(retry['confirmLabel'], i18n.translate('Retry storage check'))
        self.assertNotEqual(retry['confirmLabel'], 'Retry storage check')
        self.assertTrue(retry['defaultNo'])
        self.assertTrue(native.questions[-1]['defaultNo'])
        self.assertEqual(checks, ['storage-select', 'storage-check', 'storage-check'])
        self.assertEqual(fixture.connections, [fixture.profile])
        self.assertEqual(code, 130)
        self.assertIsNone(fixture.store.pending(fixture.profile))
        self.assertEqual(fixture.remote.uploads, {})
        self.assertFalse(any(c[0] == 'luna' and c[1].endswith('/install') for c in fixture.remote.calls))

    def test_submitted_package_check_projects_the_same_reason_and_action_on_both_frontends(self):
        from cytv.desktop import DesktopConsole
        from cytv.recovery import no_root_package_check_plan
        from cytv.state import target

        module = self.module()
        android_events, desktop_events = [], []

        class Native:
            def emit(self, raw):
                android_events.append(json.loads(raw))

        profile = target('192.0.2.10', 'no-root', 2222, connection='root-ssh')
        pending = {'action': 'install', 'recovery_protocol': 'no-root-original-stream-v1'}
        assessment = {'state': 'blocked', 'reason': 'original-terminal-unknown',
                      'actions': ['check', 'retain-evidence']}
        for console in (module.AndroidConsole(module.Callbacks(Native())),
                        DesktopConsole(lambda kind, value: desktop_events.append((kind, value)))):
            self.assertTrue(no_root_package_check_plan(console, profile, pending, assessment))
        desktop = next(value for kind, value in desktop_events if kind == 'recovery-plan')
        for field in ('disposition', 'reason', 'actions'):
            self.assertEqual(android_events[-1][field], desktop[field])
        self.assertEqual(android_events[-1]['disposition'], 'no-root-package-check')
        self.assertNotIn(profile['host'], json.dumps(android_events))

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
        self.assertEqual(native.events[-1].get('removal_action'),
                         {'action':'check','condition':'unverified','requires_change':True})
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
        self.assertEqual(event['stageText'], 'Verifying removal…')
        self.assertEqual(event['blockerText'], 'Final cleanup could not be verified. Review recovery options before continuing.')
        self.assertEqual(event['titleText'], 'Finish Clean Your TV cleanup')
        self.assertTrue(event['waiting'])
        self.assertEqual(event['actions'], ['continue-removal'])
        self.assertEqual(event.get('removal_action'),
                         {'action':'check','condition':'unverified','requires_change':True})
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
            self.assertEqual(native.events[-1].get('removal_action'),
                             {'action':'retry-removal','condition':'restart','requires_change':True})

    def test_current_removal_failure_projects_the_same_advice_on_android_and_desktop(self):
        from cytv import state
        from cytv.desktop import DesktopConsole
        from cytv.recovery import removal_plan
        module = self.module()

        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))

        native = Native()
        android = module.AndroidConsole(module.Callbacks(native))
        events = []
        desktop = DesktopConsole(lambda kind, value: events.append((kind, value)))
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('tv.local', 'root')
            store.request_clean_removal(profile)
            store.checkpoint(profile, stage='restart-required', removal_reason='restart-required')
            for code, expected in (
                    ('ssh-auth-root', {'action':'check','condition':'unverified','requires_change':True}),
                    ('ssh-timeout', {'action':'retry-removal','condition':'transient','requires_change':False})):
                with self.subTest(code=code):
                    for console in (desktop, android):
                        removal_plan(console, store, profile, failure={'code':code})
                    desktop_plan = [value for kind, value in events if kind == 'recovery-plan'][-1]
                    android_plan = native.events[-1]
                    self.assertEqual(desktop_plan.get('removal_action'), expected)
                    self.assertEqual(android_plan.get('removal_action'), expected)
                    self.assertEqual(android_plan.get('reason'), 'removal-recheck-required')
                    self.assertFalse(android_plan['restart_required'])
                    self.assertEqual(store.pending(profile)['stage'], 'restart-required')
                    self.assertEqual(store.pending(profile)['removal_reason'], 'restart-required')
                    self.assertIs(android_plan['connection_failure'], True)

    def test_current_cleanup_failure_replaces_saved_restart_wording(self):
        from cytv import state
        from cytv.errors import UserError
        from cytv.recovery import removal_plan
        module = self.module()

        class Native:
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))

        native = Native()
        console = module.AndroidConsole(module.Callbacks(native))
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('tv.local', 'root')
            store.request_clean_removal(profile)
            store.checkpoint(profile, stage='restart-required', removal_reason='restart-required')
            removal_plan(console, store, profile,
                         error=UserError('PRIVATE', reason_code='cleanup-check-failed'))
            self.assertEqual(store.pending(profile)['stage'], 'restart-required')
        event = native.events[-1]
        self.assertEqual(event['removal_action']['condition'], 'unverified')
        self.assertEqual(event['titleText'], event['summary'])
        self.assertEqual(event['blockerText'], event['nextStep'])
        self.assertFalse(event['restart_required'])
        self.assertIs(event['connection_failure'], False)
        self.assertNotIn('Restart the TV', str(event))
        self.assertNotIn('PRIVATE', str(event))

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
        self.assertIn('check', event['actions'])
        self.assertNotIn('PRIVATE-TARGET', json.dumps(native.events))
        callbacks.ask('Remove remaining Clean Your TV packages? [y/N]: ')
        self.assertTrue(native.events[-1]['defaultNo'])

    def test_root_customization_collects_an_optional_home_name(self):
        from cytv import i18n, install_settings

        bridge = self.module()
        self.addCleanup(i18n.set_language, 'en')
        i18n.set_language('ru')
        scenarios = [([''], None), (['  Cafe\u0301 홈  '], 'Café 홈'),
                     (['x' * 49, 'Home'], 'Home'), (['exit'], 'exit')]
        for names, expected in scenarios:
            with self.subTest(names=names):
                questions = []
                answers = iter(['y', '1', *names, 'n', '0', '0'])

                class Native:
                    def emit(self, raw):
                        pass

                    def request(self, raw):
                        questions.append(json.loads(raw))
                        return next(answers)

                callbacks = bridge.Callbacks(Native())
                console = bridge.AndroidConsole(callbacks)
                settings = install_settings.collect({'edition': 'root'}, console.reader(callbacks.ask), console)
                self.assertEqual(settings, {'theme': 'classic', 'weather': False, **(
                    {'tv_name': expected} if expected is not None else {})})
                self.assertEqual([event['kind'] for event in questions],
                                 ['question', 'question', *(['text'] * len(names)),
                                  'question', 'question', 'question'])
                event = questions[2]
                self.assertEqual(event['text'], 'Название экрана Home')
                self.assertEqual(event['hint'], 'Оставьте поле пустым, чтобы сохранить текущее название.')
                self.assertNotIn('options', event)
                if len(names) > 1:
                    self.assertEqual(questions[3]['error'], i18n.translate(
                        'Home screen name must contain at most 48 characters, without control characters.'))

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
            from cytv import diagnostics, state
            from cytv.errors import TVCommandError
            error=TVCommandError(17)
            error.contract_events=[{'schema':1,'component':'storage','operation':'inspect','phase':'read',
                'field':'apps','expected':'single-regular-file','actual':{'mode':511},'decision':'refuse','count':1}]
            report=diagnostics.create_report(state.Store(Path(tmp)),'status',None,'status',error,{'frontend':'android'})
            self.assertEqual(json.loads(report.read_text())['contract_events'],error.contract_events)
            callbacks=module.Callbacks(native,directory=tmp)
            callbacks.write('  '+str(report))
            self.assertEqual(native.events[0]['kind'], 'report-ready')
            self.assertEqual(native.events[0]['name'], report.name)
            native.events.clear();other=Path(tmp)/'private.json';other.write_text('{}')
            callbacks.write(str(other))
            self.assertFalse(any(e['kind']=='report-ready' for e in native.events))

    def test_failure_report_event_keeps_the_original_failed_step_and_sanitizes_the_draft(self):
        module = self.module()
        events = []

        class Native:
            def emit(self, raw):
                events.append(json.loads(raw))

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'reports'
            folder.mkdir()
            path = folder / 'diagnostic-123456abcdef.json'
            report = {'action': 'doctor', 'edition': 'no-root', 'phase': 'ssh-connect',
                      'reason_code': 'ssh-timeout', 'host': '192.0.2.50',
                      'first_failure': {'action': 'install', 'phase': 'install-packages',
                                        'cytv_version': '1.2.3',
                                        'luna': {'reason': 'FAILED_IPKG_INSTALL'}},
                      'trace': 'private exception'}
            path.write_text(json.dumps(report))
            console = module.AndroidConsole(module.Callbacks(Native(), directory=tmp))
            console.report(path)
            event = next(event for event in events if event['kind'] == 'report-ready')
            self.assertEqual(event['name'], path.name)
            draft = event.get('draft', {})
            self.assertIn('No-root install: install packages', draft.get('title', ''))
            self.assertIn('Observed phase: install-packages', draft['body'])
            self.assertIn('Reason: FAILED_IPKG_INSTALL', draft['body'])
            self.assertIn('Later observation: doctor at ssh-connect (ssh-timeout)', draft['body'])
            for private in (report['host'], report['trace'], str(path)):
                self.assertNotIn(private, json.dumps(event))
            self.assertEqual(json.loads(path.read_text()), report)

            # An unreadable summary leaves the existing file available to export.
            events.clear()
            path.write_text('invalid JSON')
            console.report(path)
            event = next(event for event in events if event['kind'] == 'report-ready')
            self.assertEqual(event, {'kind': 'report-ready', 'name': path.name})

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

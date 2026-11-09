"""Release checks use public metadata only; no TV or real network."""
import io
from http.client import IncompleteRead
import json
import tempfile
import unittest
from unittest.mock import patch

from cytv import cli


class UpdateTests(unittest.TestCase):
    def updates(self):
        from cytv import i18n
        i18n.set_language('en')
        from cytv import installer_update
        return installer_update

    def test_compares_installer_version_not_release_tag(self):
        update = self.updates()
        for version, expected in [('0.15.0', '0.15.0'), ('0.14.0', None), ('0.13.9', None), ('0.9.0', None)]:
            with self.subTest(version=version), patch.object(update, 'urlopen', side_effect=[
                io.BytesIO(json.dumps({'tag_name':'v1.99.0','draft':False,'prerelease':False}).encode()),
                io.BytesIO(json.dumps({'tag':'v1.99.0','versions':{'cytv':version}}).encode())]):
                self.assertEqual(update.latest('0.14.0'), expected)

    def test_invalid_or_unavailable_metadata_is_not_a_successful_check(self):
        update = self.updates()
        for data in [b'[]', b'{}', b'invalid', b'x'*262145,
                     b'{"tag_name":"v1.0.0","prerelease":true,"draft":false}',
                     b'{"tag_name":"https://evil.test","prerelease":false,"draft":false}']:
            with self.subTest(data=data[:60]), patch.object(update, 'urlopen', return_value=io.BytesIO(data)):
                with self.assertRaises(ValueError): update.latest('0.14.0')
        with patch.object(update, 'urlopen', side_effect=OSError('offline')):
            lines=[]
            self.assertTrue(update.offer(lambda _: self.fail('No prompt offline'), cli.Console(lines.append)))
            self.assertIn('Could not check for installer updates.', '\n'.join(lines))

    def test_interrupted_response_or_deeply_nested_json_is_nonblocking(self):
        update=self.updates()
        for failure in [IncompleteRead(b'partial'), RecursionError('nested metadata')]:
            with self.subTest(failure=type(failure).__name__), patch.object(update,'urlopen',side_effect=failure):
                lines=[]
                self.assertTrue(update.offer(lambda _:self.fail('No prompt'),cli.Console(lines.append)))
                self.assertIn('Could not check for installer updates.','\n'.join(lines))

    def test_download_exits_and_only_explicit_second_choice_continues(self):
        update = self.updates()
        for answers, expected, opened in [(['1'], False, True), (['', '2'], True, False), (['2'], True, False)]:
            with self.subTest(answers=answers), patch.object(update, 'latest', return_value='0.15.0'), patch.object(update.webbrowser, 'open', return_value=True) as browser:
                choices=iter(answers)
                self.assertEqual(update.offer(lambda _: next(choices), cli.Console(lambda _: None)), expected)
                self.assertEqual(browser.called, opened)
                if opened: self.assertEqual(browser.call_args.args, ('https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest',))

    def test_uses_bounded_https_requests_and_pins_build_metadata(self):
        update=self.updates()
        with patch.object(update,'urlopen',side_effect=[
                io.BytesIO(b'{"tag_name":"v1.14.0","draft":false,"prerelease":false}'),
                io.BytesIO(b'{"tag":"v1.14.0","versions":{"cytv":"0.15.0"}}')]) as network:
            self.assertEqual(update.latest('0.14.0'),'0.15.0')
            self.assertEqual([call.args[0].full_url for call in network.call_args_list],[
                'https://api.github.com/repos/Razdva122/clean-your-tv-lg-webos/releases/latest',
                'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.14.0/BUILD-INFO.json'])
            for call in network.call_args_list:
                self.assertEqual(call.kwargs['timeout'],3)
                self.assertTrue(call.kwargs['context'].check_hostname)
        for metadata in [b'{"tag":"v1.13.0","versions":{"cytv":"0.15.0"}}',
                         b'{"tag":"v1.14.0","versions":{"cytv":"0.15.0-beta"}}',
                         b'{"tag":"v1.14.0","versions":[]}']:
            with patch.object(update,'urlopen',side_effect=[
                    io.BytesIO(b'{"tag_name":"v1.14.0","draft":false,"prerelease":false}'),io.BytesIO(metadata)]):
                with self.assertRaises(ValueError):update.latest('0.14.0')

    def test_computer_entrypoint_enables_the_shared_check(self):
        with patch('cytv.cli.main',return_value=0) as engine:
            cli.entry()
            self.assertTrue(engine.call_args.kwargs['check_updates'])

    def test_non_install_commands_and_payload_probe_skip_update_gate(self):
        update=self.updates()
        with tempfile.TemporaryDirectory() as directory, patch.object(update,'offer') as offer:
            for command in ['status','recover','doctor']:
                cli.main([command,'--data-dir',directory,'--no-discovery'], ask=lambda _:'q',write=lambda _:None,check_updates=True)
            with patch('cytv.package.verify_payload',return_value={'files':{}}):
                cli.main(['--check-payload','--data-dir',directory],write=lambda _:None,check_updates=True)
            offer.assert_not_called()

    def test_current_version_does_not_prompt(self):
        update=self.updates()
        with patch.object(update, 'latest', return_value=None):
            self.assertTrue(update.offer(lambda _: self.fail('No update prompt'), cli.Console(lambda _:None)))

    def test_cli_gate_prevents_tv_connection_and_skips_pending_recovery(self):
        update=self.updates()
        profile={'host':'192.0.2.1','edition':'root','port':22}
        with tempfile.TemporaryDirectory() as directory, patch('cytv.cli.choose_profile', return_value=profile), patch('cytv.package.verify_payload', side_effect=RuntimeError('stop after gate')) as payload:
            with patch.object(update, 'offer', return_value=False) as offer:
                self.assertEqual(cli.main(['--data-dir',directory], write=lambda _:None, check_updates=True),0)
                payload.assert_not_called()
                offer.assert_called_once()
            with patch('cytv.state.Store.pending', return_value={'action':'install'}), patch.object(update,'offer') as offer:
                cli.main(['--data-dir',directory], ask=lambda _:'q', write=lambda _:None, check_updates=True)
                offer.assert_not_called()

    def test_noninteractive_requires_specific_override_not_yes(self):
        update=self.updates()
        with patch.object(update,'latest',return_value='0.15.0'):
            with self.assertRaises(cli.UserError):
                update.offer(lambda _:self.fail('Never prompt'), cli.Console(lambda _:None), non_interactive=True)
            self.assertTrue(update.offer(lambda _:self.fail('Never prompt'), cli.Console(lambda _:None), non_interactive=True, use_bundled=True))

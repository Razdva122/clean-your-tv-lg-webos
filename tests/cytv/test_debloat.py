import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cytv import debloat, diagnostics
from cytv.state import Store


class DebloatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        profile = {'host': 'tv.local', 'edition': 'root', 'port': 22}
        self.installer = SimpleNamespace(profile=profile, store=Store(self.tmp.name))
        self.record = self.installer.store.device_dir(profile) / 'debloat.json'

    def test_log_uploads_journal_native_values_before_write_and_restore(self):
        from cytv.terminal import Console

        values = {'dbgLogUpload': True, 'faultLogUpload': False}
        def luna(uri, payload, **kwargs):
            self.assertEqual(payload['category'], 'option')
            if uri.endswith('/getSystemSettings'):
                key, = payload['keys']
                return {'returnValue': True, 'settings': {key: values[key]}}
            (key, value), = payload['settings'].items()
            self.assertEqual(key, 'dbgLogUpload')
            self.assertIs(type(value), bool)
            entry = json.loads(self.record.read_text())['settings'][key]
            self.assertIs(entry['original'], True)
            self.assertIs(entry['target'], False)
            values[key] = value
            return {'returnValue': True}

        self.installer.remote = Mock(root=True)
        self.installer.remote.luna.side_effect = luna
        self.assertEqual(debloat.apply(self.installer, list(values)),
                         {'dbgLogUpload': 'verified', 'faultLogUpload': 'already'})
        self.assertIs(values['dbgLogUpload'], False)
        events, output = {}, []
        debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile,
                              lambda _: 'y', Console(output.append), diagnostic=events)
        self.assertEqual(events, {'dbgLogUpload': 'restored'})
        self.assertIn('Debug log uploads to LG — Off → On', ' '.join(output))
        self.assertIs(values['dbgLogUpload'], True)
        self.assertEqual(json.loads(self.record.read_text())['settings'], {})

    def test_root_requires_exact_log_upload_type_and_valid_record(self):
        self.installer.remote = Mock(root=True)
        for value in (None, 0, 1, 'on', 'off', 'true', 'false'):
            with self.subTest(value=value):
                self.installer.remote.luna.reset_mock()
                self.installer.remote.luna.return_value = {'returnValue': True, 'settings': {'faultLogUpload': value}}
                self.assertEqual(debloat.apply(self.installer, ['faultLogUpload']), {'faultLogUpload': 'unavailable'})
                self.assertEqual(self.installer.remote.luna.call_count, 1)
                self.assertFalse(self.record.exists())
        self.record.write_text(json.dumps({'schema': 1, 'settings': {'faultLogUpload': {'original': 1, 'target': 0}}}))
        self.installer.remote.luna.return_value = {'returnValue': True, 'settings': {'faultLogUpload': True}}
        events = {}
        self.assertEqual(debloat.apply(self.installer, ['faultLogUpload'], diagnostic=events),
                         {'faultLogUpload': 'failed'})
        self.assertEqual(events, {'faultLogUpload': 'journal-failed'})

    def test_no_root_log_uploads_use_only_paired_setter_and_verify_native_readback(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = Mock(root=False)
        key = 'dbgLogUpload'
        for file_initial, paired_original, accepted, actual, expected in (
            (None, True, True, False, 'verified'),
            (False, True, True, False, 'verified'),  # stale preference file with target already present
            (True, True, True, False, 'verified'),  # stale preference file after successful set
            (None, True, False, None, 'write-rejected'),
            (None, True, True, True, 'verify-mismatch'),
            (None, True, True, 0, 'verify-unavailable'),
            (False, True, True, None, 'verify-unavailable'),  # stale file is insufficient
            ('off', 'on', None, None, 'unavailable'),
            (None, False, None, None, 'already'),
        ):
            with self.subTest(expected=expected), patch.object(debloat, 'SSAP') as pair, patch.object(debloat.time, 'sleep'):
                self.installer.remote.run.return_value = json.dumps(file_initial)
                values = {'read': paired_original}
                def call(uri, payload, **kwargs):
                    if uri.endswith('/getSystemSettings'):
                        self.assertEqual(payload, {'category': 'option', 'keys': [key]})
                        return {'returnValue': True, 'settings': {key: values['read']}}
                    self.assertEqual(uri, 'ssap://settings/setSystemSettings')
                    self.assertIsNotNone(accepted, 'unexpected write')
                    self.assertEqual(payload['category'], 'option')
                    self.assertIs(payload['settings'][key], False)
                    values['read'] = actual
                    return {'returnValue': accepted}
                pair.return_value.__enter__.return_value.call.side_effect = call
                events = {}
                debloat.apply(self.installer, [key], diagnostic=events)
                self.assertEqual(events, {key: expected})
                self.installer.remote.luna.assert_not_called()

    def test_no_root_restores_upload_with_paired_read_when_file_is_missing(self):
        from cytv.terminal import Console

        self.installer.profile.update(edition='no-root', port=9922)
        record = self.installer.store.device_dir(self.installer.profile) / 'debloat.json'
        record.write_text(json.dumps({'schema': 1, 'settings': {'faultLogUpload': {'original': True, 'target': False}}}))
        self.installer.remote = Mock(root=False)
        self.installer.remote.run.return_value = 'null'
        with patch.object(debloat, 'SSAP') as pair:
            ssap = pair.return_value.__enter__.return_value
            ssap.call.side_effect = [
                {'returnValue': True, 'settings': {'faultLogUpload': value}} for value in (False, False)
            ] + [{'returnValue': True}, {'returnValue': True, 'settings': {'faultLogUpload': True}}]
            events = {}
            debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile,
                                  lambda _: 'y', Console(lambda _: None), diagnostic=events)
            self.assertEqual(events, {'faultLogUpload': 'restored'})
            self.assertEqual(ssap.call.call_args_list[2].args[0], 'ssap://settings/setSystemSettings')
            self.assertIs(ssap.call.call_args_list[2].args[1]['settings']['faultLogUpload'], True)
        self.assertEqual(json.loads(record.read_text())['settings'], {})

    def test_restore_retains_paired_receipt_if_readback_becomes_inaccessible(self):
        from cytv.terminal import Console

        self.installer.profile.update(edition='no-root', port=9922)
        record = self.installer.store.device_dir(self.installer.profile) / 'debloat.json'
        entry = {'original': True, 'target': False}
        record.write_text(json.dumps({'schema': 1, 'settings': {'faultLogUpload': entry}}))
        self.installer.remote = Mock(root=False)
        self.installer.remote.run.return_value = 'true'  # stale original in the file
        with patch.object(debloat, 'SSAP') as pair:
            ssap = pair.return_value.__enter__.return_value
            ssap.call.side_effect = [{'returnValue': True, 'settings': {'faultLogUpload': False}},
                                     {'returnValue': False}]
            events = {}
            debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile,
                                  lambda _: 'y', Console(lambda _: None), diagnostic=events)
            self.assertEqual(events, {'faultLogUpload': 'restore-unavailable'})
            self.assertEqual(ssap.call.call_count, 2)
        self.assertEqual(json.loads(record.read_text())['settings'], {'faultLogUpload': entry})

    def test_promotion_streamer_requires_a_readable_original_before_ssap_write(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = Mock(root=False)
        self.installer.remote.run.side_effect = ['null', '"on"', '"off"']
        with patch.object(debloat, 'SSAP') as pair:
            self.assertEqual(debloat.apply(self.installer, ['promotionStreamer']),
                             {'promotionStreamer': 'unavailable'})
            pair.assert_not_called()
            ssap = pair.return_value.__enter__.return_value
            ssap.call.return_value = {'returnValue': True}
            self.assertEqual(debloat.apply(self.installer, ['promotionStreamer']),
                             {'promotionStreamer': 'verified'})
            ssap.call.assert_called_once_with('ssap://settings/setSystemSettings',
                {'category': 'option', 'settings': {'promotionStreamer': 'off'}}, timeout=8)

    def test_old_session_only_choices_cannot_trigger_a_partial_write(self):
        self.installer.remote = Mock(root=True)
        for key in ('preloadNetflix', 'preloadYouTube', 'preloadBrowser'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                debloat.apply(self.installer, ['promotionStreamer', key])
        self.assertEqual(self.installer.remote.method_calls, [])
        self.assertFalse(self.record.exists())

    def test_known_older_firmware_does_not_offer_the_webos_22_menu_path(self):
        self.assertNotIn('Home Settings', debloat.result_message('homePromotion', 'firmware-blocked'))

    def test_results_distinguish_no_root_write_rejection_from_other_failures(self):
        from cytv.desktop import DesktopConsole

        self.installer.profile['edition'] = 'no-root'
        self.installer.remote = SimpleNamespace(
            root=False, run=lambda command, **kwargs: '"off"' if 'livePlus' in command else 'null')
        for model, firmware, reply, expected in (
            ('55UK7500PSA', '05.50.70', {'returnValue': False}, 'firmware-blocked'),
            ('43UP751C0ZF', '03.53.45', {'returnValue': False}, 'write-rejected'),
            ('43UP751C0ZF', '03.53.45', TimeoutError(), 'failed'),
        ):
            with self.subTest(model=model, reply=reply), patch.object(debloat, 'SSAP') as connect:
                self.installer.tv_info = {'modelName': model, 'firmwareVersion': firmware}
                connect.return_value.__enter__.return_value.call.side_effect = [reply]
                writer = Mock()
                events = {}
                answers = iter(['["homePromotion", "livePlus"]', '1'])
                debloat.run(self.installer, lambda _: next(answers), DesktopConsole(writer), diagnostic=events)
                writer.assert_any_call('debloat-results', {'homePromotion': expected, 'livePlus': 'already'})
                self.assertEqual(events['homePromotion'],
                                 'write-unavailable' if isinstance(reply, Exception) else 'write-rejected')

    def test_manual_steps_are_limited_to_rejected_writes_and_the_selected_setting(self):
        sections = {
            'home-promotions': ('homePromotion', 'contentRecommendation'),
            'screensaver': ('screenSaverAd',), 'viewing': ('livePlus',),
            'advertising': ('adCookie', 'lmt'), 'tips': ('aiNudge',), 'sports': ('sportsAlarm',),
            'live-promotions': ('livePromotion', 'promotionStreamer', 'webOSPromotionVideo'),
            'log-uploads': ('dbgLogUpload', 'faultLogUpload'),
        }
        self.assertTrue(set(debloat.SETTINGS).issubset({key for group in sections.values() for key in group}))
        for lang, filename in (('ru', 'PRIVACY.ru.md'), ('en', 'PRIVACY.md'), ('de', 'PRIVACY.md')):
            with patch.object(debloat, 'resolved_language', return_value=lang):
                for section, keys in sections.items():
                    for key in keys:
                        for status in ('firmware-blocked', 'write-rejected', 'restore-rejected'):
                            with self.subTest(lang=lang, key=key, status=status):
                                self.assertTrue(debloat.privacy_guide(key, status).endswith('/' + filename + '#' + section))
        for status in (*debloat.DIAGNOSTIC_RESULTS, 'failed', 'unverified'):
            if status not in ('write-rejected', 'restore-rejected'):
                self.assertIsNone(debloat.privacy_guide('livePlus', status))
        self.assertIsNone(debloat.privacy_guide('unknown', 'write-rejected'))

    def test_terminal_links_only_the_setting_rejected_by_root(self):
        from cytv.terminal import Console

        self.installer.remote = Mock(root=True)
        self.installer.remote.luna.side_effect = [
            {'returnValue': True, 'settings': {'homePromotion': 'on'}}, {'returnValue': False},
            {'returnValue': True, 'settings': {'contentRecommendation': 'on'}}, TimeoutError(),
        ]
        output = []
        answers = iter(['y', '1', '0', '0', '0', 'y', '1'])
        debloat.run(self.installer, lambda _: next(answers), Console(output.append))
        self.assertEqual([line for line in output if line.startswith('https://')],
                         [debloat.privacy_guide('homePromotion', 'write-rejected')])

    def test_result_states_and_journal_precedes_write(self):
        values = {'homePromotion': 'off', 'screenSaverAd': 'on', 'lmt': 'off'}
        writes = []

        def luna(uri, payload, **kwargs):
            if uri.endswith('/getSystemSettings'):
                key, = payload['keys']
                return {'returnValue': True, 'settings': {key: values.get(key)}}
            (key, wanted), = payload['settings'].items()
            writes.append(key)
            entries = json.loads(self.record.read_text())['settings']
            if key in values:
                self.assertEqual(entries[key]['original'], values[key])
            else:
                self.assertNotIn(key, entries)
            if key == 'lmt':
                return {'returnValue': False}
            if key in values:
                values[key] = wanted
            return {'returnValue': True}

        self.installer.remote = SimpleNamespace(root=True, luna=luna)
        result = debloat.apply(self.installer, ['homePromotion', 'screenSaverAd', 'livePlus', 'lmt'])
        self.assertEqual(result, {'homePromotion': 'already', 'screenSaverAd': 'verified',
                                  'livePlus': 'unverified', 'lmt': 'failed'})
        self.assertEqual(writes, ['screenSaverAd', 'livePlus', 'lmt'])
        self.assertEqual(values['screenSaverAd'], 'off')

    def test_no_root_with_root_ssh_writes_and_verifies_through_luna(self):
        self.installer.profile.update(edition='no-root', connection='root-ssh')
        self.installer.remote = SimpleNamespace(root=True)
        with patch.object(self.installer.remote, 'luna', create=True) as luna, patch.object(debloat, 'SSAP') as connect:
            luna.side_effect = [
                {'returnValue': True, 'settings': {'livePromotion': 'on'}},
                {'returnValue': True},
                {'returnValue': True, 'settings': {'livePromotion': 'off'}},
            ]
            self.assertEqual(debloat.apply(self.installer, ['livePromotion']), {'livePromotion': 'verified'})
            connect.assert_not_called()
            self.assertEqual(luna.call_count, 3)
            self.assertEqual(luna.call_args_list[1].args, (
                debloat.SERVICE + 'setSystemSettings', {'category': 'option', 'settings': {'livePromotion': 'off'}}))

    def test_no_root_reads_files_and_sends_only_selected_key_over_ssap(self):
        replies = iter(['null', '"off"'])
        self.installer.profile['edition'] = 'no-root'
        self.installer.profile['port'] = 9922
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: next(replies))
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.return_value = {'returnValue': True}
            self.assertEqual(debloat.apply(self.installer, ['aiNudge']), {'aiNudge': 'verified'})
            ssap.call.assert_called_once_with('ssap://settings/setSystemSettings',
                                              {'category': 'general', 'settings': {'aiNudge': 'off'}},
                                              timeout=8)
        path = self.installer.store.device_dir(self.installer.profile) / 'debloat.json'
        self.assertFalse(path.exists())

    def test_live_plus_falls_back_to_ssap_read_and_skips_already_correct_value(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: 'null')
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.return_value = {'returnValue': True, 'settings': {'livePlus': 'off'}}
            self.assertEqual(debloat.apply(self.installer, ['livePlus']), {'livePlus': 'already'})
            ssap.call.assert_called_once_with('ssap://settings/getSystemSettings',
                                              {'category': 'option', 'keys': ['livePlus']},
                                              timeout=5)

    def test_no_root_permission_denial_does_not_stop_following_setting(self):
        from cytv.errors import UserError

        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: 'null')
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.side_effect = [UserError('TV permission was denied.'), {'returnValue': True}]
            self.assertEqual(debloat.apply(self.installer, ['aiNudge', 'sportsAlarm']),
                             {'aiNudge': 'failed', 'sportsAlarm': 'unverified'})
            self.assertEqual(ssap.call.call_count, 2)

    def test_failed_settings_pairing_is_reported_for_each_blocked_write(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(
            root=False, run=lambda command, **kwargs: '"off"' if 'livePlus' in command else 'null')
        events = {}
        with patch('websockets.sync.client.connect') as connect:
            socket = connect.return_value
            socket.recv.return_value = json.dumps({'type': 'error', 'error': 'private-pairing-details'})
            result = debloat.apply(self.installer, ['livePlus', 'lmt', 'aiNudge'], diagnostic=events)
        self.assertEqual(result, {'livePlus': 'already', 'lmt': 'failed', 'aiNudge': 'failed'})
        self.assertEqual(events, {'livePlus': 'already', 'lmt': 'pairing-rejected', 'aiNudge': 'pairing-rejected'})
        socket.send.assert_called_once()

    def test_write_rejection_and_readback_failures_are_distinct_in_reports(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(
            root=False, run=lambda command, **kwargs: 'null' if 'sportsAlarm' in command else '"on"')
        socket = Mock()
        socket.recv.side_effect = [
            json.dumps({'type': 'registered', 'payload': {'client-key': 'private-settings-key'}}),
            json.dumps({'id': 'cytv_1', 'type': 'error', 'error': 'private-response'}),
            json.dumps({'id': 'cytv_2', 'payload': {'returnValue': True}}),
            json.dumps({'id': 'cytv_3', 'payload': {'returnValue': True}}),
        ]
        events = {}
        with patch('websockets.sync.client.connect', return_value=socket), patch.object(debloat.time, 'sleep'):
            result = debloat.apply(self.installer, ['homePromotion', 'aiNudge', 'sportsAlarm'], diagnostic=events)
        self.assertEqual(result, {'homePromotion': 'failed', 'aiNudge': 'failed', 'sportsAlarm': 'unverified'})
        for action, phase in (('install', 'install-complete'), ('debloat', 'debloat')):
            with self.subTest(action=action):
                path = diagnostics.create_report(
                    self.installer.store, action, self.installer.profile, phase,
                    tv_info={'debloat': {**events, 'private-key': 'verified', 'livePlus': 'private-value'}})
                report = path.read_text()
                self.assertEqual(json.loads(report)['debloat'], {
                    'homePromotion': 'write-rejected', 'aiNudge': 'verify-mismatch', 'sportsAlarm': 'verify-unavailable',
                })
                self.assertNotIn('private-', report)

    def test_maintenance_restores_one_saved_setting_without_touching_others(self):
        from cytv.terminal import Console

        entries = {key: {'original': 'on', 'target': 'off'} for key in ('homePromotion', 'sportsAlarm')}
        self.installer.remote = Mock(root=True)
        for decision, replies, expected, keep in (
            ('n', ['off'], None, True),
            ('y', ['off', 'off', False], 'restore-rejected', True),
            ('y', ['off', 'off', TimeoutError()], 'restore-failed', True),
            ('y', ['off', 'off', True, 'on'], 'restored', False),
            (None, ['on'], 'restore-already', False),
        ):
            with self.subTest(decision=decision, replies=replies):
                self.record.write_text(json.dumps({'schema': 1, 'settings': entries}))
                answers = iter(['2'] + ([decision] if decision else []))
                values = iter(replies)
                def luna(uri, payload, **kwargs):
                    value = next(values)
                    if uri.endswith('/getSystemSettings'):
                        self.assertEqual(payload, {'category': 'general', 'keys': ['sportsAlarm']})
                        return {'returnValue': True, 'settings': {'sportsAlarm': value}}
                    self.assertEqual(payload, {'category': 'general', 'settings': {'sportsAlarm': 'on'}})
                    if isinstance(value, Exception):
                        raise value
                    return {'returnValue': value}
                self.installer.remote.luna.side_effect = luna
                log, events = [], {}
                debloat.run(self.installer, lambda _: next(answers), Console(log.append),
                            maintenance=True, diagnostic=events)
                self.assertEqual([line for line in log if line.startswith('https://')],
                                 [debloat.privacy_guide('sportsAlarm', expected)] if expected == 'restore-rejected' else [])
                self.assertEqual(list(values), [])
                self.assertEqual(events, {'sportsAlarm': expected} if expected else {})
                saved = json.loads(self.record.read_text())['settings']
                self.assertEqual(saved, entries if keep else {'homePromotion': entries['homePromotion']})

    def test_restore_requires_consent_and_keeps_unverified_entries(self):
        from cytv.terminal import Console

        entries = {
            'homePromotion': {'original': 'on', 'target': 'off'},
            'screenSaverAd': {'original': 'on', 'target': 'off'},
            'livePlus': {'original': 'on', 'target': 'off'},
            'sportsAlarm': {'original': 'on', 'target': 'off'},
        }
        self.record.write_text(json.dumps({'schema': 1, 'settings': entries}))
        values = {'homePromotion': 'off', 'screenSaverAd': 'on', 'sportsAlarm': 'off'}
        writes = []

        def luna(uri, payload, **kwargs):
            if uri.endswith('/getSystemSettings'):
                key, = payload['keys']
                return {'returnValue': True, 'settings': {key: values.get(key)}}
            (key, wanted), = payload['settings'].items()
            writes.append((key, wanted))
            if key == 'sportsAlarm':
                return {'returnValue': False}
            values[key] = wanted
            return {'returnValue': True}

        self.installer.remote = SimpleNamespace(root=True, luna=luna)
        output = []
        console = Console(output.append)
        def decline(_):
            preview = ' '.join(output)
            self.assertIn('Sponsored tiles — Off → On', preview)
            self.assertIn('Sports notifications — Off → On', preview)
            self.assertIn('Screen saver ads — Already at the saved original value', preview)
            self.assertIn('Live Plus — Could not read the current value', preview)
            self.assertEqual(writes, [])
            return ''

        debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile, decline, console)
        self.assertEqual(writes, [])
        self.assertEqual(json.loads(self.record.read_text())['settings'], entries)

        def accept(_):
            # An unreadable setting that becomes readable after the preview
            # was never included in the user's confirmation.
            values['livePlus'] = 'off'
            return 'y'

        debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile, accept, console)
        self.assertEqual(writes, [('homePromotion', 'on'), ('sportsAlarm', 'on')])
        self.assertEqual(json.loads(self.record.read_text())['settings'],
                         {key: entries[key] for key in ('livePlus', 'sportsAlarm')})
        self.assertIn('Restored and verified', ' '.join(output))
        self.assertIn('Could not read the current value', ' '.join(output))

    def test_root_domain_blocking_reads_before_and_after_one_explicit_write(self):
        from cytv.desktop import DesktopConsole
        write = DesktopConsole(lambda *args: None)
        self.installer.remote = Mock(root=True)
        def reply(state):
            return {'returnValue':True, 'root':True, 'result':{'returnValue':True, 'result':state}}
        self.installer.remote.luna.side_effect = [reply('off'), reply('on'), reply('on')]
        self.assertTrue(debloat.offer_domain_blocking(self.installer, lambda label:'1', write))
        calls = self.installer.remote.luna.call_args_list
        self.assertEqual([call.args[1] for call in calls],
                         [{'domainBlocking':'status'}, {'domainBlocking':'on'}, {'domainBlocking':'status'}])

    def test_domain_blocking_does_not_write_on_skip_or_other_edition(self):
        from cytv.desktop import DesktopConsole
        write = DesktopConsole(lambda *args: None)
        self.installer.remote = Mock(root=True)
        self.installer.remote.luna.return_value = {
            'returnValue': True, 'root': True, 'result': {'returnValue': True, 'result': 'off'}}
        self.assertFalse(debloat.offer_domain_blocking(self.installer, lambda label:'', write))
        self.installer.remote.luna.assert_called_once()
        self.installer.remote.luna.reset_mock()
        self.installer.profile['edition'] = 'no-root'
        self.assertFalse(debloat.offer_domain_blocking(self.installer, self.fail, write))
        self.installer.remote.luna.assert_not_called()

    def test_restore_uses_ssap_for_saved_developer_mode_profile(self):
        self.installer.profile.update(edition='no-root', port=9922)
        record = self.installer.store.device_dir(self.installer.profile) / 'debloat.json'
        record.write_text(json.dumps({'schema': 1, 'settings': {
            'livePlus': {'original': 'on', 'target': 'off'},
        }}))
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: 'null')
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.side_effect = [
                {'returnValue': True, 'settings': {'livePlus': 'off'}},
                {'returnValue': True, 'settings': {'livePlus': 'off'}},
                {'returnValue': True},
                {'returnValue': True, 'settings': {'livePlus': 'on'}},
            ]
            from cytv.terminal import Console
            debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile, lambda _: 'y', Console(lambda _: None))
            self.assertEqual(ssap.call.call_args_list[2].args, (
                'ssap://settings/setSystemSettings', {'category': 'option', 'settings': {'livePlus': 'on'}}))
        self.assertEqual(json.loads(record.read_text())['settings'], {})

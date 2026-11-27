"""First-time TV pairing and the private inventory handoff."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import socket
import struct
import unittest
from unittest.mock import patch

from homebrew import pairing


def prompt(request='register_0'):
    return {'id': request, 'type': 'response', 'payload': {'pairingType': 'PROMPT', 'returnValue': True}}


def registration(key='fixture-key', request='register_0'):
    return {'id': request, 'type': 'registered', 'payload': {'client-key': key}}


def response(request, payload):
    return {'id': 'cytv_' + str(request), 'type': 'response', 'payload': payload}


class TVSocket:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []
        self.closed = False

    def send(self, data):
        self.requests.append(json.loads(data))

    def recv(self, *, timeout):
        try:
            return json.dumps(next(self.replies))
        except StopIteration:
            raise TimeoutError('private transport detail') from None

    def close(self):
        self.closed = True


class TVPairingTests(unittest.TestCase):
    def setUp(self):
        contexts = ExitStack()
        self.addCleanup(contexts.close)
        self.local_ipv4 = contexts.enter_context(patch.object(pairing, '_local_ipv4', return_value='192.0.2.5'))
        self.connect = contexts.enter_context(patch('websockets.sync.client.connect'))
        self.output = StringIO()
        contexts.enter_context(redirect_stdout(self.output))
        contexts.enter_context(redirect_stderr(self.output))

    def test_preflight_checks_fixed_port_without_sending_a_pairing_request(self):
        self.assertTrue(callable(getattr(pairing, 'available', None)))
        with patch.object(socket, 'socket') as create:
            probe = create.return_value.__enter__.return_value
            self.assertTrue(pairing.available())
            create.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
            probe.settimeout.assert_called_once_with(1)
            probe.bind.assert_called_once_with(('192.0.2.5', 0))
            probe.connect.assert_called_once_with(('192.0.2.5', 3001))
            probe.send.assert_not_called()
            create.return_value.__exit__.assert_called_once()
            probe.connect.side_effect = ConnectionRefusedError('private transport detail')
            self.assertFalse(pairing.available())
        self.connect.assert_not_called()
        self.assertEqual(self.output.getvalue(), '')

    def test_key_requires_owner_prompt_then_stays_with_shared_inventory(self):
        socket = TVSocket([
            {'id': 'unrelated', 'type': 'error', 'error': 'private transport detail'},
            prompt(), registration(),
            response(1, {'returnValue': True, 'launchPoints': [{'id': 'app.alpha', 'title': 'Alpha'}]}),
            response(2, {'returnValue': True, 'devices': [{'appId': 'input.one', 'label': 'Input 1'}]}),
            response(3, {'returnValue': True, 'apps': [{'id': 'com.webos.app.livetv', 'title': 'Live TV'}]}),
        ])
        self.connect.return_value = socket
        with patch('cytv.tv.private_write', side_effect=AssertionError('must not write a separate keyfile')):
            inventory, key = pairing.collect(b'fallback')
        self.assertEqual(key, 'fixture-key')
        self.assertEqual([app['id'] for app in inventory['apps']], ['com.webos.app.livetv', 'app.alpha'])
        self.assertEqual(inventory['inputs'], [{'appId': 'input.one', 'label': 'Input 1'}])
        self.assertEqual(self.output.getvalue(), '')
        self.assertTrue(socket.closed)
        self.connect.assert_called_once()
        self.assertEqual(self.connect.call_args.args, ('wss://192.0.2.5:3001',))
        self.assertIsNone(self.connect.call_args.kwargs['proxy'])
        self.assertTrue(getattr(self.connect.call_args.kwargs.get('logger'), 'disabled', False))
        self.assertEqual(self.connect.call_args.kwargs['source_address'], ('192.0.2.5', 0))
        self.assertEqual(socket.requests[0], {
            'id': 'register_0', 'type': 'register', 'payload': {
                'forcePairing': False, 'pairingType': 'PROMPT', 'manifest': {
                    'manifestVersion': 1, 'appVersion': '1.1', 'permissions': [
                        'READ_APP_STATUS', 'READ_RUNNING_APPS', 'READ_POWER_STATE', 'CONTROL_POWER',
                        'READ_INSTALLED_APPS', 'READ_INPUT_DEVICE_LIST',
                    ],
                },
            },
        })
        self.assertEqual([request['uri'] for request in socket.requests[1:]], [
            'ssap://com.webos.applicationManager/listLaunchPoints', 'ssap://tv/getExternalInputList',
            'ssap://com.webos.applicationManager/listApps',
        ])

    def test_invalid_or_unapproved_registration_never_reads_inventory(self):
        cases = [
            ([registration()], 'pairing-unavailable'),
            ([prompt('unrelated'), registration()], 'pairing-unavailable'),
            ([prompt(), registration(request='unrelated')], 'pairing-timeout'),
            ([prompt(), registration('')], 'pairing-unavailable'),
            ([prompt(), registration('x' * 1025)], 'pairing-unavailable'),
            ([prompt(), registration('🖥' * 400)], 'pairing-unavailable'),
            ([prompt(), {'id': 'register_0', 'type': 'registered', 'payload': []}], 'pairing-unavailable'),
            ([prompt(), {'id': 'register_0', 'type': 'error', 'error': 'private refusal'}], 'pairing-rejected'),
            ([prompt(), {'id': 'register_0', 'type': 'response', 'payload': {'returnValue': False}}], 'pairing-rejected'),
            ([prompt()], 'pairing-timeout'),
        ]
        for index, (replies, expected) in enumerate(cases):
            with self.subTest(expected=expected, index=index):
                socket = TVSocket(replies)
                self.connect.reset_mock(return_value=True)
                self.connect.return_value = socket
                with self.assertRaises(pairing.PairingError) as caught:
                    pairing.collect(b'fallback')
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(str(caught.exception), expected)
                self.assertEqual(len(socket.requests), 1)
                self.assertTrue(socket.closed)
                self.connect.assert_called_once()
        self.assertEqual(self.output.getvalue(), '')

    def test_missing_inputs_need_existing_clean_install_policy(self):
        for allow in (False, True):
            with self.subTest(allow=allow):
                points = {'returnValue': True, 'launchPoints': [{'id': 'example.app', 'title': 'Example'}]}
                socket = TVSocket([
                    prompt(), registration(), response(1, points),
                    {'id': 'cytv_2', 'type': 'error', 'error': '401 insufficient permissions'},
                    response(3, {'returnValue': True, 'apps': []}), response(4, points),
                ])
                self.connect.return_value = socket
                if allow:
                    inventory, _ = pairing.collect(b'fallback', allow_missing_inputs=lambda: True)
                    self.assertEqual(inventory['inputs'], [])
                    self.assertEqual(socket.requests[-1]['uri'], 'ssap://com.webos.applicationManager/listLaunchPoints')
                else:
                    with self.assertRaises(pairing.PairingError) as caught:
                        pairing.collect(b'fallback', allow_missing_inputs=lambda: False)
                    self.assertEqual(caught.exception.code, 'inventory-unavailable')
                self.assertTrue(socket.closed)

    def test_missing_local_endpoint_never_connects(self):
        self.local_ipv4.side_effect = OSError('private network information')
        with self.assertRaises(pairing.PairingError) as caught:
            pairing.collect(b'fallback')
        self.assertEqual(caught.exception.code, 'pairing-unavailable')
        self.assertEqual(str(caught.exception), 'pairing-unavailable')
        self.connect.assert_not_called()


@unittest.skipUnless(os.name == 'posix', 'Linux interface selection uses fcntl')
class TVNetworkTests(unittest.TestCase):
    def test_chooses_assigned_ipv4_from_active_local_interface(self):
        interfaces = {'lo': (0x9, ''), 'down': (0, ''), 'linklocal': (1, '169.254.1.1'),
                      'vpn': (0x11, ''), 'eth0': (1, '192.0.2.5')}

        def read(_, request, data):
            flags, address = interfaces[data[:16].split(b'\0', 1)[0].decode()]
            if request == 0x8913:
                return data[:16] + struct.pack('H', flags) + bytes(22)
            self.assertEqual(request, 0x8915)
            return data[:20] + socket.inet_aton(address) + bytes(16)

        with patch('fcntl.ioctl', side_effect=read), patch.object(
            socket, 'if_nameindex', return_value=list(enumerate(interfaces, 1))
        ), patch.object(socket, 'socket'):
            self.assertEqual(pairing._local_ipv4(), '192.0.2.5')


if __name__ == '__main__':
    unittest.main()

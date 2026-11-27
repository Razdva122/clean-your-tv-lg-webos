import errno
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cytv import diagnostics, state


class DoctorMrcuTests(unittest.TestCase):
    def test_report_keeps_only_verified_observations(self):
        from cytv.diagnostic_context import tv_summary
        for probe, expected in (
            ({'state': 'unique', 'home': True, 'back': False, 'path': 'private'},
             {'state': 'unique', 'home': True, 'back': False}),
            ({'state': 'unique', 'home': 1, 'back': True}, {'state': 'unavailable'}),
            ({'state': 'missing', 'home': True}, {'state': 'missing'}),
            ('private', {'state': 'unavailable'}),
        ):
            with self.subTest(probe=probe), tempfile.TemporaryDirectory() as tmp:
                path = diagnostics.create_report(state.Store(tmp), 'doctor', None, 'doctor',
                                                 tv_info={'root_mrcu_probe': probe})
                self.assertEqual(json.loads(path.read_text())['tv']['root_mrcu_probe'], expected)
                self.assertNotIn('private', str(json.loads(path.read_text())['tv']))
        self.assertNotIn('root_mrcu_probe', tv_summary({}))

    @unittest.skipUnless(os.name == 'posix', 'TV probe uses Linux ioctls')
    def test_probe_queries_only_name_and_advertised_bits(self):
        import fcntl
        from cytv.doctor_mrcu import PROBE
        for names, keys, expected in (
            (['other'], (), 'missing'),
            (['remote', 'remote'], (), 'ambiguous'),
            (['other', 'remote'], (773, 412), 'unique 1 1'),
            (['remote'], (412,), 'unique 0 1'),
            (['remote'], (773,), 'unique 1 0'),
            (['remote'], (), 'unique 0 0'),
            (['remote', 'denied'], (), 'unavailable'),
            (['stale'], (), 'missing'),
            (['stale'] * 9 + ['remote'] + ['stale'] * 10, (773, 412), 'unique 1 1'),
            (['remote', 'registered'], (773, 412), 'unavailable'),
            (['remote', 'no-registry'], (773, 412), 'unavailable'),
        ):
            with self.subTest(names=names, keys=keys):
                def open_event(path, flags):
                    self.assertEqual(flags, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
                    index = int(os.path.basename(path)[5:])
                    if names[index] == 'denied':
                        raise PermissionError(errno.EACCES, 'private')
                    if names[index] in ('stale', 'registered', 'no-registry'):
                        raise OSError(errno.ENXIO, 'private')
                    return index + 10

                def device_node(path):
                    if path.startswith('/sys/dev/char/13:'):
                        index = int(path.rsplit(':', 1)[1]) - 64
                        if names[index] == 'registered':
                            return SimpleNamespace(st_mode=stat.S_IFLNK)
                        raise FileNotFoundError(errno.ENOENT, 'private')
                    index = int(os.path.basename(path)[5:])
                    return SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=os.makedev(13, 64 + index))

                def sysfs(path):
                    if path == '/sys/dev/char' and 'no-registry' not in names:
                        return SimpleNamespace(st_mode=stat.S_IFDIR)
                    raise FileNotFoundError(errno.ENOENT, 'private')

                def query(fd, request, buf, mutate=True):
                    if request == 0x81004506:
                        name = b'LGE M-RCU - Builtin [0]' if names[fd - 10] == 'remote' else b'private'
                        buf[:len(name)] = name
                    else:
                        self.assertEqual(request, 0x80804521)
                        self.assertEqual(names[fd - 10], 'remote')
                        for key in keys:
                            buf[key // 8] |= 1 << (key % 8)
                    return 0

                with patch('os.listdir', return_value=['event'+str(i) for i in range(len(names))]), \
                     patch('os.open', side_effect=open_event), patch('os.close') as close, \
                     patch('os.fstat', return_value=SimpleNamespace(st_mode=stat.S_IFCHR)), \
                     patch('os.lstat', side_effect=device_node), patch('os.stat', side_effect=sysfs), \
                     patch.object(fcntl, 'ioctl', side_effect=query), patch('builtins.print') as output:
                    exec(PROBE, {})
                output.assert_called_once_with(expected)
                self.assertCountEqual([call.args[0] for call in close.call_args_list],
                                      [10+i for i, name in enumerate(names) if name in ('other', 'remote')])

    def test_root_doctor_saves_observation_even_if_home_preflight_fails(self):
        from cytv import cli, doctor_mrcu
        from tests.cytv.test_operations import Remote

        class DoctorRemote(Remote):
            def run(self, command, data=None, timeout=30):
                if data == doctor_mrcu.PROBE.encode():
                    observations.append((command, timeout))
                    return 'unique 1 0'
                return super().run(command, data, timeout)

            def close(self):
                pass

        for profile_readable in (True, False):
            with self.subTest(profile_readable=profile_readable), tempfile.TemporaryDirectory() as tmp:
                observations = []
                remote = DoctorRemote()
                if not profile_readable:
                    remote.luna = Mock(return_value={'returnValue': False})
                with patch('cytv.operations.Installer.status', return_value={'device': {}}):
                    code = cli.main(['doctor', '--report', '--host', '192.0.2.55', '--edition', 'root',
                                     '--data-dir', tmp], write=lambda _: None, connect=lambda *args: remote)
                self.assertEqual(code, 0 if profile_readable else 2)
                self.assertEqual(observations, [('/usr/bin/python3 -I -B -', 5)])
                path, = Path(tmp, 'reports').glob('*.json')
                report = json.loads(path.read_text())
                self.assertEqual(report['tv']['root_mrcu_probe'], {'state': 'unique', 'home': True, 'back': False})
                self.assertFalse(remote.uploads)
                self.assertFalse(remote.installed)

    def test_transport_failure_and_untrusted_output(self):
        from cytv.doctor_mrcu import observe
        remote = Mock()
        for result in ('unique 1 0', 'private', TimeoutError('private')):
            remote.run.side_effect = [result]
            expected = {'state': 'unique', 'home': True, 'back': False} if result == 'unique 1 0' else {'state': 'unavailable'}
            self.assertEqual(observe(remote, 'python'), expected)

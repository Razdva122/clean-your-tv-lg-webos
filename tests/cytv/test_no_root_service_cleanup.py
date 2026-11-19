"""EF950V ownership replay; package-manager mutations stay outside the SDK UID."""
import json
import os
from pathlib import Path
import shutil
import signal
import time
import unittest

from cytv import package


@unittest.skipUnless(os.name != 'nt' and getattr(os, 'getuid', lambda: -1)() == 0
                     and shutil.which('node'), 'exact ownership replay needs Linux root and Node')
class EF950ServiceCleanup(unittest.TestCase):
    def test_install_remove_fresh_install_remove_with_protected_services(self):
        from multiprocessing import Pipe
        from tests.cytv.test_no_root_simple_removal import SimpleRemoval
        case = SimpleRemoval()
        case.setUp()
        self.addCleanup(case.doCleanups)
        (case.root / 'proc').mkdir()
        base = case.root / 'developer/apps/usr/palm'
        apps = case.cleanup.APPS[:2]
        services = ('com.local.nativehome.service', 'com.gathin.tvhome.renewal')
        artifacts = [package.ipk(app, '1.0.0', {
            'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': '1.0.0'}).encode(),
            'usr/palm/services/' + service + '/service.js': b'// fixture service\n',
        }) for app, service in zip(apps, services)]

        def install_packages(service_owner=(0, 0)):
            for artifact in artifacts:
                for name, data in package.data_files(artifact).items():
                    destination = case.root / 'developer/apps' / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(data)
            helper_state = base / 'applications' / apps[0] / 'state'
            helper_state.mkdir(exist_ok=True)
            for folder, _, _ in os.walk(base):
                os.chown(folder, 0, 0)
                Path(folder).chmod(0o775)
            os.chown(helper_state, 5999, 5000)
            for service in services:
                os.chown(base / 'services' / service, *service_owner)

        install_packages()
        for folder, _, files in os.walk(case.root):
            if Path(folder) == base or base in Path(folder).parents:
                continue
            os.chown(folder, 5755, 5000)
            for name in files:
                os.chown(Path(folder) / name, 5755, 5000)
        client, server = Pipe()
        self.addCleanup(client.close)
        self.addCleanup(server.close)
        pid = os.fork()
        if pid == 0:
            os.setsid()
            server.close()
            try:
                os.setgroups([44, 505, 509, 777])
                os.setgid(5000)
                os.setuid(5755)
                self.assertEqual((os.getuid(), os.getgid(), os.getgroups()),
                                 (5755, 5000, [44, 505, 509, 777]))
                original = case.remote.luna
                def luna(uri, payload, **options):
                    if uri.endswith('/dev/remove'):
                        client.send(('remove', payload['id']))
                        self.assertEqual(client.recv(), 'done')
                    return original(uri, payload, **options)
                case.remote.luna = luna
                for cycle in range(2):
                    case.remote.apps = set(apps)
                    self.assertFalse(os.access(base / 'services', os.W_OK))
                    result = case.remove()
                    self.assertTrue(result['verified_clean'])
                    self.assertTrue(result['empty_helper_dirs_retained'])
                    self.assertTrue(result['empty_service_dirs_retained'])
                    self.assertIsNone(case.store.pending(case.profile))
                    for service in services:
                        leaf = base / 'services' / service
                        self.assertEqual(list(leaf.iterdir()), [])
                        self.assertEqual((leaf.stat().st_uid, leaf.stat().st_gid, leaf.stat().st_mode & 0o777), ((0, 0, 0o775) if cycle == 0 else (5999, 5000, 0o775)))
                    if cycle == 0:
                        case.store.begin(case.profile, 'install')
                        client.send(('install', None))
                        self.assertEqual(client.recv(), 'done')
                        case.store.finish(case.profile)
                client.send(('finished', None))
            except BaseException:
                import traceback
                traceback.print_exc()
                os._exit(1)
            os._exit(0)
        client.close()
        try:
            while server.poll(30):
                command, app = server.recv()
                if command == 'finished':
                    break
                if command == 'install':
                    install_packages((5999, 5000))
                else:
                    # The privileged vendor removes package files, but leaves
                    # its service directory behind. SDK cleanup cannot rmdir it.
                    shutil.rmtree(base / 'applications' / app)
                    if app == apps[0]:
                        leaf = base / 'applications' / app / 'state'
                        leaf.mkdir(parents=True)
                        leaf.parent.chmod(0o775)
                        leaf.chmod(0o775)
                        os.chown(leaf, 5999, 5000)
                    service = services[apps.index(app)]
                    (base / 'services' / service / 'service.js').unlink()
                server.send('done')
        except EOFError:
            pass
        finally:
            server.close()  # Unblock a fixture child waiting for a vendor reply.
            deadline = time.monotonic() + 5
            while True:
                waited, status = os.waitpid(pid, os.WNOHANG)
                if waited:
                    break
                if time.monotonic() >= deadline:
                    os.killpg(pid, signal.SIGKILL)
                    _, status = os.waitpid(pid, 0)
                    break
                time.sleep(0.01)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)

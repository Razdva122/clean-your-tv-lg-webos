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
        self.run_owned_service_cycle()

    def test_terminal_services_finish_after_verified_restart_with_opaque_process(self):
        self.run_owned_service_cycle(opaque=True)

    def test_terminal_restart_with_inherited_install_history(self):
        self.run_owned_service_cycle(opaque=True, inherited=True)

    def test_failed_home_startup_then_vendor_owned_web_process_removal(self):
        self.run_owned_service_cycle(package_runtimes=True)

    def test_stalled_controller_after_install_is_stopped_by_package_manager(self):
        self.run_owned_service_cycle(package_runtimes=True, stalled_controller=True)

    def test_first_postboot_pass_completes_new_terminals_in_both_install_cycles(self):
        self.run_owned_service_cycle(opaque=True, first_postboot=True)

    def run_owned_service_cycle(self, *, opaque=False, inherited=False, package_runtimes=False, stalled_controller=False, first_postboot=False):
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
            shutil.rmtree(case.root / 'proc/987654', ignore_errors=True)
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
            if first_postboot:
                history = case.root / 'developer/.cytv-installer/operations' / ('a' * 32)
                history.mkdir(parents=True, exist_ok=True)
                process = case.root / 'proc/987654'
                process.mkdir(exist_ok=True)
                (process / 'cmdline').write_bytes(b'/usr/bin/node\0-e\0opaque\0')
            if package_runtimes:
                (helper_state / 'controller.log').write_text(json.dumps({
                    'event': 'start', 'pid': 987649, 'startupSchema': 1, 'generation': 'I' + 'a' * 32}) + '\n' +
                    json.dumps({'event': 'worker-start'} if stalled_controller else {'event': 'worker-exit', 'code': 22}) + '\n')
                if stalled_controller:
                    (helper_state / 'controller.pid').write_text('987649')
                    process = case.root / 'proc/987649'
                    process.mkdir(exist_ok=True)
                    (process / 'cmdline').write_bytes(('node\0' + str(base / 'applications' / apps[0] / 'native.js') + '\0').encode())
                process = case.root / 'proc/987650'
                process.mkdir(exist_ok=True)
                (process / 'cmdline').write_bytes(b'/usr/bin/WebProcess\0com.gathin.tvhome\0')

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
                    if inherited and not case.store.pending(case.profile):
                        case.store.begin(case.profile, 'install')
                    self.assertFalse(os.access(base / 'services', os.W_OK))
                    if package_runtimes:
                        import subprocess
                        from cytv.helper_startup import PROGRAM
                        source = PROGRAM.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome',
                                                 str(base / 'applications' / apps[0]))
                        source = source.replace("'/proc/'", json.dumps(str(case.root / 'proc') + '/'))
                        observed = subprocess.run(['node', '-e', source, 'I' + 'a' * 32],
                                                  check=True, capture_output=True, text=True)
                        startup = json.loads(observed.stdout)
                        self.assertEqual(startup['state'], 'starting' if stalled_controller else 'failed')
                        if not stalled_controller:
                            self.assertEqual(startup['relay_exit_code'], 22)
                        self.assertEqual(startup['controller_running'], stalled_controller)
                    result = case.remove()
                    if opaque:
                        self.assertTrue(result['restart_required'])
                        self.assertEqual(case.store.pending(case.profile).get('removals', {}),
                                         {} if first_postboot else {app: 'terminal' for app in apps})
                        from cytv import diagnostics
                        report = json.loads(diagnostics.create_report(case.store, 'uninstall', case.profile, 'uninstall').read_text())
                        evidence = report['removal']['restart_evidence']
                        self.assertTrue(evidence['opaque_interpreter'])
                        self.assertFalse(evidence['kernel_changed'])
                        case.reboot()
                        if cycle:
                            case.remote.boot = '33333333-3333-3333-3333-333333333333'
                        result = case.remove()
                    self.assertTrue(result['verified_clean'], result)
                    self.assertTrue(result['empty_helper_dirs_retained'])
                    self.assertTrue(result['empty_service_dirs_retained'])
                    self.assertIsNone(case.store.pending(case.profile))
                    if opaque:
                        completed = case.store.diagnostic_removal['cleanup_restart_evidence']
                        self.assertTrue(completed['kernel_changed'])
                        self.assertEqual(completed['decision'], 'completed')
                        if first_postboot:
                            self.assertTrue(completed['all_targets_terminal'])
                            self.assertTrue(completed['project_catalog_absent'])
                            self.assertTrue(completed['allow_opaque'])
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
                    if package_runtimes:
                        if app == apps[1]:
                            shutil.rmtree(case.root / 'proc/987650')
                        if stalled_controller and app == apps[0]:
                            shutil.rmtree(case.root / 'proc/987649')
                    if opaque and app == apps[-1]:
                        process = case.root / 'proc/987654'
                        process.mkdir(exist_ok=True)
                        (process / 'cmdline').write_bytes(b'/usr/bin/node\0-e\0opaque\0')
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

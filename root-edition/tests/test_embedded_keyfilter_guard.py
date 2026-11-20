"""Exercise the shared guardian against an embedded compositor Home target."""
import os
import shutil
import subprocess
import unittest

import test_keyfilter_guard as fixture

BOOT, TOKEN = fixture.BOOT, fixture.TOKEN


@unittest.skipUnless(os.name == 'posix' and shutil.which('cc'), 'POSIX compiler required')
class EmbeddedKeyfilterGuardTests(unittest.TestCase):
    setUp = fixture.KeyfilterGuardTests.setUp
    tearDown = fixture.KeyfilterGuardTests.tearDown
    run_guard = fixture.KeyfilterGuardTests.run_guard
    spawn = fixture.KeyfilterGuardTests.spawn
    armed = fixture.KeyfilterGuardTests.armed
    finish = fixture.KeyfilterGuardTests.finish

    def config(self, header='CYTV-QML-KEYFILTER-1'):
        compositor = self.root / 'compositor'
        if not compositor.exists():
            compositor.write_bytes(b'LG compositor executable'.ljust(52, b'\0'))
            compositor.chmod(0o700)
        info = compositor.stat()
        config = self.root / 'state/config'
        config.write_text(
            f'{header}\ntoken {TOKEN}\nboot {BOOT}\ndev {info.st_dev}\n'
            f'ino {info.st_ino}\nsize {info.st_size}\nmtime_ns {info.st_mtime_ns}\n'
        )
        config.chmod(0o600)

    def test_embedded_target_is_verified_without_a_native_home_file(self):
        (self.root / 'home').unlink()
        result, status = self.run_guard('--status')
        self.assertEqual(status, 0)
        self.assertTrue(result['stock_verified'])
        self.assertEqual(result['state'], 'stock')

    def test_embedded_restore_closes_only_the_owned_root_app(self):
        result, status = self.run_guard('--restore')
        self.assertEqual(status, 0)
        self.assertTrue(result['stopped'])
        self.assertTrue(result['stock_verified'])
        calls = (self.root / 'luna-calls').read_text().splitlines()
        self.assertEqual(len(calls), 1)
        self.assertIn('closeByAppId', calls[0])
        self.assertIn('com.cleanyourtv.root.preview', calls[0])
        self.assertNotIn('com.webos.app.home', calls[0])

    def test_embedded_identity_drift_refuses_the_stock_proof(self):
        (self.root / 'compositor').write_bytes(b'changed compositor'.ljust(53, b'\0'))
        result, _ = self.run_guard('--status')
        self.assertFalse(result['stock_verified'])
        self.assertFalse(result['healthy'])

    def test_separate_native_home_drift_does_not_change_the_compositor_proof(self):
        (self.root / 'home').write_bytes(b'changed separate Home app')
        result, status = self.run_guard('--status')
        self.assertEqual(status, 0)
        self.assertTrue(result['stock_verified'])

    def test_target_kind_change_invalidates_an_inflight_configuration(self):
        harness = self.root / 'mode-change.c'
        harness.write_text(f'''#define main guardian_main
#include "{fixture.SOURCE}"
#undef main
int main(void) {{
    if (!config_read() || !cfg.embedded) return 2;
    FILE *file = fopen(STATE "/config", "w");
    if (!file) return 3;
    fprintf(file, "CYTV-C1-KEYFILTER-1\\ntoken %s\\nboot %s\\n"
            "dev %llu\\nino %llu\\nsize %llu\\nmtime_ns %llu\\n",
            cfg.token, cfg.boot, cfg.dev, cfg.ino, cfg.size, cfg.mtime);
    if (fclose(file)) return 4;
    int same = same_config();
    printf("%d %d\\n", same, cfg.embedded);
    return 0;
}}
''')
        binary = self.root / 'mode-change'
        subprocess.run([
            'cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
            '-DCYTV_KEYFILTER_FIXTURE', f'-DFIXTURE_ROOT="{self.root}"',
            str(harness), '-o', str(binary),
        ], check=True, capture_output=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, '0 1\n')

    def test_embedded_target_cannot_be_a_symlink(self):
        (self.root / 'compositor').unlink()
        (self.root / 'compositor').symlink_to(self.root / 'home')
        result, _ = self.run_guard('--status')
        self.assertFalse(result['stock_verified'])
        self.assertFalse(result['healthy'])

    def test_unknown_configuration_headers_are_refused(self):
        for header in ('CYTV-QML-KEYFILTER-2', 'CYTV-QML-KEYFILTER-1 ', 'CYTV-KEYFILTER-1'):
            with self.subTest(header=header):
                self.config(header)
                result, status = self.run_guard('--status')
                self.assertNotEqual(status, 0)
                self.assertFalse(result['stock_verified'])
                self.assertEqual(result['reason'], 'config_invalid')

    def test_embedded_controller_eof_latches_routing_off(self):
        guard, input_writer, control_writer = self.armed()
        os.close(control_writer)
        self.guards[-1] = (guard, (input_writer,))
        result = self.finish(guard)
        self.assertEqual(result['reason'], 'controller_lost')
        self.assertTrue(result['stopped'])
        self.assertTrue(result['stock_verified'])
        self.assertNotIn('com.webos.app.home', (self.root / 'luna-calls').read_text())

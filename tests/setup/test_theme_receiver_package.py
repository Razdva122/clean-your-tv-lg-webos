import unittest
from unittest.mock import patch
import shutil
import subprocess
import tempfile
from pathlib import Path
from scripts.theme_receiver import inject


class ThemeReceiverPackageTest(unittest.TestCase):
    def test_canonical_modules_are_owned_by_each_service_package(self):
        for files in ({'service.js': b'root'}, {'service.js': b'no-root'}):
            result = inject(files)
            self.assertEqual(result['service.js'], files['service.js'])
            self.assertIn(b'./theme-receiver/register', result['theme-receiver.js'])
            self.assertIn(b'exports', result['theme-receiver/core.js'])
            self.assertIn(b'themeReceiverStart', result['theme-receiver/register.js'])
            self.assertIn(b'CYTV_SESSION_EXPIRES', result['theme-receiver/wallpaper-phone.js'])
            self.assertIn('theme-receiver/vendor/heic/libheif-bundle.txt',result)
            self.assertIn(b'GNU LESSER GENERAL PUBLIC LICENSE',result['theme-receiver/vendor/heic/LICENSE.txt'])
            self.assertNotIn('theme-receiver.js', files)

    def test_changed_decoder_bytes_are_rejected(self):
        from scripts import theme_receiver
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(theme_receiver.ROOT / 'theme-receiver', root / 'theme-receiver')
            (root / 'theme-receiver/vendor/heic/libheif-bundle.txt').write_bytes(b'changed')
            with patch.object(theme_receiver, 'ROOT', root), self.assertRaisesRegex(ValueError, 'Changed pinned HEIC decoder'):
                inject({'service.js':b'root'})

    def test_standalone_root_receiver_preserves_the_private_inventory(self):
        source = {'service.js': b"module.exports = require('./theme-receiver');"}
        result = inject(source, standalone=True)
        self.assertEqual(set(result), set(source))
        self.assertIn(b'themeReceiverStart', result['service.js'])
        self.assertNotIn(b"require('./theme-receiver')", result['service.js'])
        self.assertIn(b'CYTV_SESSION_EXPIRES', result['service.js'])
        self.assertNotIn(b"require('./wallpaper-phone')", result['service.js'])
        with self.assertRaises(ValueError):
            inject({'service.js': b'no receiver registration'}, standalone=True)


    def test_standalone_root_wallpaper_capabilities_resolve_bundled_cache(self):
        bundle = inject({'service.js': b"module.exports = require('./theme-receiver');"}, standalone=True)
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'service.js'
            from scripts.helper_build import compile_helper
            bundle = compile_helper(bundle)
            for name, raw in bundle.items():
                target=Path(directory)/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
            result = subprocess.run(['node', '-e', """
const assert = require('assert/strict');
const register = require(process.argv[1]);
const {request} = require('./tests/themes/personal-receiver.cjs');
const methods = {};
register({register:(name, fn) => methods[name] = fn}, {appId:'com.test', port:0});
const call = (name, payload) => new Promise(resolve => methods[name]({
  payload, ls2Message:{applicationID:() => 'com.test'}, respond:resolve
}));
(async () => {
  const session = await call('themeReceiverStart', {kind:'wallpaper'});
  try {
    const worker = await request(session,'/wallpaper-heic-worker.js');
    assert.equal(worker.code,200);
    assert(worker.body.startsWith(require('fs').readFileSync('theme-receiver/vendor/heic/libheif-bundle.txt','utf8')));
    new (require('vm').Script)(worker.body);
    assert.match((await request(session,'/wallpaper-heic-license.txt')).body,/GNU LESSER GENERAL PUBLIC LICENSE/);
    const response = await request(session, '/v1/wallpaper-capabilities');
    assert.equal(response.code, 200);
    const capabilities = JSON.parse(response.body);
    assert.equal(capabilities.wallpaperProtocol, 1);
    assert.equal(capabilities.videoCacheStorage.required, 0);
    assert(capabilities.videoCacheStorage.available === null || capabilities.videoCacheStorage.available >= 0);
  } finally { await call('themeReceiverStop', {sessionId:session.sessionId}); }
})().catch(error => { console.error(error); process.exit(1); });
""", str(script)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

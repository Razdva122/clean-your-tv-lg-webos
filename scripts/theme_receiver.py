"""Explicitly package the same receiver modules in each service's private tree."""
from pathlib import Path
import json
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ('wallpaper-phone.js', 'core.js', 'wallpaper-cache.js', 'register.js', 'wallpaper-heic.js')


def inject(files, standalone=False):
    result = dict(files)
    modules = {}
    for name in FILES:
        source = ROOT / 'theme-receiver' / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing or indirect theme receiver source: ' + name)
        modules[name] = source.read_bytes()
    decoder = ROOT / 'theme-receiver/vendor/heic/libheif-bundle.txt'
    if decoder.is_symlink() or not decoder.is_file():
        raise ValueError('Missing or indirect HEIC decoder')
    decoder_bytes = decoder.read_bytes()
    if hashlib.sha256(decoder_bytes).hexdigest() != '074b2b55ef3de477ba9f794ca381f3f0324c1cba8c91b4af07395f39c22d54cc':
        raise ValueError('Changed pinned HEIC decoder')
    if standalone:
        # Root's immutable supervisor inventory already owns service.js. Keep
        # its dependency closure there so historical supervisors can update it.
        needle = b"require('./theme-receiver')"
        if result['service.js'].count(needle) != 1:
            raise ValueError('Expected one Root receiver registration')
        core_import = b"var core = require('./core');"
        if modules['register.js'].count(core_import) != 1:
            raise ValueError('Expected one canonical receiver core import')
        register = modules['register.js'].replace(core_import, b'var core = receiverCore.exports;')
        if register.count(b"var wallpaperCache = require('./wallpaper-cache');") != 1:
            raise ValueError('Expected one canonical wallpaper cache import')
        register = register.replace(b"var wallpaperCache = require('./wallpaper-cache');", b'var wallpaperCache = wallpaperCacheModule.exports;')
        phone_import = b"var phonePage = require('./wallpaper-phone');"
        if modules['core.js'].count(phone_import) != 1:
            raise ValueError('Expected one canonical phone page import')
        core = modules['core.js'].replace(phone_import, b'var phonePage = phonePageModule.exports;')
        cache_import = b"require('./wallpaper-cache')"
        if core.count(cache_import) != 1:
            raise ValueError('Expected one receiver capabilities cache import')
        core = core.replace(cache_import, b'wallpaperCacheModule.exports')
        worker_import = b"require('./wallpaper-heic')"
        if core.count(worker_import) != 1:
            raise ValueError('Expected one HEIC worker import')
        core = core.replace(worker_import, b'heicWorkerModule.exports')
        worker = modules['wallpaper-heic.js']
        for name, raw in (('libheif-bundle.txt', decoder_bytes), ('LICENSE.txt', (decoder.parent / 'LICENSE.txt').read_bytes()), ('README.md', (decoder.parent / 'README.md').read_bytes())):
            pattern = rb"require\('fs'\)\.readFileSync\(\s*__dirname \+ '/vendor/heic/" + re.escape(name.encode()) + rb"',\s*'utf8'\s*\)"
            replacement = json.dumps(raw.decode('utf8')).encode()
            worker, count = re.subn(pattern, lambda _: replacement, worker)
            if count != 1:
                raise ValueError('Expected one HEIC asset import: ' + name)
        bundled = (b'(function(){var phonePageModule={exports:{}};'
                   b'(function(module,exports){\n' + modules['wallpaper-phone.js'] + b'\n})(phonePageModule,phonePageModule.exports);'
                   b'var heicWorkerModule={exports:{}};(function(module,exports){\n' + worker + b'\n})(heicWorkerModule,heicWorkerModule.exports);'
                   b'var receiverCore={exports:{}};'
                   b'(function(module,exports){\n' + core + b'\n})(receiverCore,receiverCore.exports);'
                   b'var wallpaperCacheModule={exports:{}};(function(module,exports){\n' + modules['wallpaper-cache.js'] +
                   b'\n})(wallpaperCacheModule,wallpaperCacheModule.exports);'
                   b'var receiverRegister={exports:{}};(function(module,exports){\n' + register +
                   b'\n})(receiverRegister,receiverRegister.exports);return receiverRegister.exports;}())')
        result['service.js'] = result['service.js'].replace(needle, bundled)
        return result
    for name, data in modules.items():
        result['theme-receiver/' + name] = data
    for name in ('libheif-bundle.txt', 'LICENSE.txt', 'README.md'):
        result['theme-receiver/vendor/heic/' + name] = (decoder.parent / name).read_bytes()
    result['theme-receiver.js'] = b"module.exports = require('./theme-receiver/register');\n"
    return result

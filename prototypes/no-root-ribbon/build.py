"""Build the standalone experimental IPK locally; never connects to a TV."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cytv.package import ipk
from scripts.tv_web_build import compile_web

RIBBON_REVISION = '68fb76cc47951fad304d25b147efc9db2da41229'


def real_ribbon():
    # Read committed public project sources, never another chat's working files.
    paths = ['launcher', 'root-edition/ui', 'root-edition/assets', 'root-edition/preview.py',
             'preview/reference-apps', 'preview/bridge.js', 'preview/icons/browser.svg',
             'scripts/tv-dev.py', 'scripts/tv-dev-media.js']
    archive = subprocess.check_output(['git', 'archive', RIBBON_REVISION, *paths], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='cytv-ribbon-source-') as directory:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(directory, filter='data')
        files = runpy.run_path(str(Path(directory) / 'scripts/tv-dev.py'))['ui_files']()
    manifest = json.loads((Path(__file__).parent / 'app/appinfo.json').read_text())
    manifest.update(version='0.0.3', title='No-root Real Ribbon Lab', themeEngineVersion='1.8.1')
    files['appinfo.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    files['icon.png'] = (ROOT / 'launcher/brand-v2-icon.png').read_bytes()
    # The simulator must not draw synthetic content over real underlying video,
    # swallow self-close, or share the ordinary development app's preferences.
    for name in ('bridge.js', 'dev-entry.js'):
        text = files[name].decode()
        start = text.index('  // Synthetic content lives')
        end = text.index('  // The real controller', start)
        text = text[:start] + text[end:]
        if text.count('window.close = function () {};') != 1:
            raise ValueError('Unexpected preview close adapter')
        files[name] = text.replace('window.close = function () {};', '').replace(
            "prefix = 'cytv.dev.ui.'", "prefix = 'cytv.lab.norootribbon.'").encode()
    entry = files['dev-entry.js'].decode()
    match = re.search(r'document.write\(("[^\n]+")\);', entry)
    if not match:
        raise ValueError('Missing isolated UI script entry')
    scripts = json.loads(match[1])
    marker = '<script src="wallpaper.js"></script>'
    if scripts.count(marker) != 1:
        raise ValueError('Unexpected wallpaper initialization')
    scripts = scripts.replace(marker, marker + '<script src="lab-setup.js"></script>')
    seed = "window.PREVIEW_HOME_CONTEXT=window.RibbonLab.mode==='overlay'?'content':'empty';\n"
    seed += "window.CYTV_DEV_STORAGE.setItem('tvhome.theme.choice.v1',JSON.stringify({id:'builtin:ribbon',title:'Ribbon'}));\n"
    files['dev-entry.js'] = (entry[:match.start()] + seed + 'document.write(' + json.dumps(scripts) + ');' + entry[match.end():]).encode()
    files['lab-setup.js'] = b"HomeWallpaper.suspend('no-root-lab');\n"
    files['lab-native.js'] = (Path(__file__).parent / 'real-host.js').read_bytes()
    html = files['index.html'].decode()
    html = re.sub(r'media-src [^;]*;', "media-src 'none';", html)
    html = html.replace('<script src="dev-entry.js">', '<script src="lab-native.js"></script><script src="dev-entry.js">')
    html = html.replace('</head>', '<link rel="stylesheet" href="lab.css"></head>')
    files['index.html'] = html.encode()
    files['lab.css'] = b'html[data-lab-pending="true"] #homeSurface{visibility:hidden}\n'
    files['lab-source.json'] = json.dumps({'sourceRevision':RIBBON_REVISION, 'nativeServices':False, 'videoWallpaper':False}).encode()
    return files


def build(real=False):
    source = Path(__file__).resolve().parent / 'app'
    files = {name: (source / name).read_bytes()
             for name in ('appinfo.json', 'index.html', 'style.css', 'app.js')}
    files['icon.png'] = (ROOT / 'launcher/brand-v2-icon.png').read_bytes()
    if real:
        files = real_ribbon()
    files = compile_web(files)
    stage = ROOT / 'build/no-root-ribbon-prototype' / ('real' if real else 'app')
    for name, raw in files.items():
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    info = json.loads(files['appinfo.json'])
    app, version = info['id'], info['version']
    packaged = {'usr/palm/applications/' + app + '/' + name: raw for name, raw in files.items()}
    packaged['usr/palm/packages/' + app + '/packageinfo.json'] = json.dumps({
        'id': app, 'version': version, 'app': app, 'services': []
    }).encode()
    output = ROOT / 'dist/no-root-ribbon-prototype'
    output.mkdir(parents=True, exist_ok=True)
    package = output / (app + '_' + version + '_all.ipk')
    package.write_bytes(ipk(app, version, packaged))
    (output / 'SHA256SUMS').write_text(hashlib.sha256(package.read_bytes()).hexdigest() + '  ' + package.name + '\n')
    print(package)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-ribbon', action='store_true', help='Use the pinned actual Home/Ribbon UI with isolated simulated services')
    build(parser.parse_args().real_ribbon)

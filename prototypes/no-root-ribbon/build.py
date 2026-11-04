"""Build the standalone experimental IPK locally; never connects to a TV."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cytv.package import ipk
from scripts.tv_web_build import compile_web


def build():
    source = Path(__file__).resolve().parent / 'app'
    files = {name: (source / name).read_bytes()
             for name in ('appinfo.json', 'index.html', 'style.css', 'app.js')}
    files['icon.png'] = (ROOT / 'launcher/brand-v2-icon.png').read_bytes()
    files = compile_web(files)
    stage = ROOT / 'build/no-root-ribbon-prototype/app'
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
    build()

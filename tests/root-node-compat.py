#!/usr/bin/env python3
"""Build the opt-in Root Node prototype and execute its packaged JS, never a TV."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'root-edition')]
from cytv import package

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true', help='Demonstrate pre-prototype failure')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='cytv-root-node-') as directory:
        base = Path(directory).resolve()
        kwargs = {} if args.baseline else {'legacy_node_prototype': True}
        root = load('root_builder', 'root-edition/build.py').build(base/'root', version='0.0.1', **kwargs)
        updater = load('root_updater_builder', 'root-edition/build_updater.py').build(base/'root-updater', **kwargs)
        system_build = load('system_builder', 'system-updater/build.py')
        system = system_build.build(base/'system', **kwargs)
        # Real IPK extraction and authenticated bundle closure, not source-only compilation.
        for name, ipk in [('root',root),('root-updater',updater),('system',system)]:
            folder = base/name
            manifest = json.loads((folder/'bundle.json').read_text())
            for relative, digest in manifest['files'].items():
                assert hashlib.sha256((folder/relative).read_bytes()).hexdigest() == digest, relative
            for relative, raw in package.data_files(ipk.read_bytes()).items():
                target=base/(name+'-ipk')/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
        # Opt-in cannot silently alter the default shipping runtime path.
        if not args.baseline:
            load('default_root_builder', 'root-edition/build.py').build(base/'default-root', version='0.0.1')
            load('default_updater_builder', 'root-edition/build_updater.py').build(base/'default-root-updater')
            system_build.build(base/'default-system')
            for folder in ('root','root-updater','system'):
                normal=json.loads((base/('default-'+folder)/'bundle.json').read_text())
                legacy=json.loads((base/folder/'bundle.json').read_text())
                assert set(normal['files']) == set(legacy['files']), 'Prototype expanded immutable file paths'
            assert (base/'default-root/python_boot.js').read_bytes() == (ROOT/'root-edition/python_boot.js').read_bytes()
            assert (base/'default-root-updater/updater/fetch.js').read_bytes() == (ROOT/'root-edition/updater/fetch.js').read_bytes()
            assert (base/'default-system/system_updater/policy.js').read_bytes() == (ROOT/'system-updater/policy.js').read_bytes()
        raw, inventory = system_build.infrastructure(base)
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
            assert set(archive.getnames()) == set(inventory)
            for name, digest in inventory.items():
                data=archive.extractfile(name).read()
                assert hashlib.sha256(data).hexdigest() == digest
                target=base/'infrastructure'/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
        # Independently pinned supervisor path inventory must admit every produced byte.
        paths=json.loads((base/'system/infrastructure-paths.json').read_text())
        assert set(paths) == set(inventory), (set(paths)-set(inventory),set(inventory)-set(paths))
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                        '-subj','/CN=localhost','-keyout',str(base/'key.pem'),
                        '-out',str(base/'cert.pem')],check=True,capture_output=True)
        (base/'public.pem').write_bytes(subprocess.check_output(['openssl','x509','-in',str(base/'cert.pem'),'-pubkey','-noout']))
        runtimes=list(dict.fromkeys(filter(None,[os.environ.get('NODE012'),os.environ.get('NODE8'),shutil.which('node')])))
        from unittest.mock import patch
        deploy = load('root_deploy_gate', 'root-edition/deploy.py')
        real_run = subprocess.run
        for runtime in runtimes:
            version = subprocess.check_output([runtime, '--version'], text=True).strip()
            if runtime == os.environ.get('NODE012'): assert version == 'v0.12.2', version
            if runtime == os.environ.get('NODE8'): assert version == 'v8.12.0', version
            def node_run(argv, **kwargs):
                assert argv[:2] == ['/usr/bin/node', '-e']
                return real_run([runtime, *argv[1:]], **kwargs)
            with patch.object(deploy.subprocess, 'run', side_effect=node_run):
                if version.startswith('v0.'):
                    try: deploy.require_node()
                    except RuntimeError: pass
                    else: raise AssertionError('Legacy Root admission gate was weakened')
                else: deploy.require_node()
            diagnostic_dir=base/'root-ipk/usr/palm/services/com.cleanyourtv.root.preview.service'
            diagnostic=subprocess.run([runtime,str(ROOT/'tests/fixtures/root-node-diagnostics.js'),str(diagnostic_dir)],cwd=ROOT,timeout=30)
            assert diagnostic.returncode == 23
            record=json.loads((diagnostic_dir.parent/'recovery-service.json').read_text())
            assert record['phase']=='exited' and record['exit_status']==23
            (diagnostic_dir.parent/'recovery-service.json').unlink()
            print('PASS generated diagnostic native fd writes and exit status '+version,flush=True)
            for fixture in ('root-node-compat.js','root-node-transport.js','root-node-binding.js'):
                subprocess.run([runtime,str(ROOT/'tests/fixtures'/fixture),str(base)],check=True,cwd=ROOT,timeout=120)
        if not os.environ.get('NODE012'):
            print('Exact Node 0.12.2 NOT RUN; set NODE012. This is not legacy runtime evidence.')

if __name__ == '__main__':
    main()

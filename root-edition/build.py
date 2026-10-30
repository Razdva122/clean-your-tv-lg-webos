#!/usr/bin/env python3
"""Build an offline, isolated Root candidate IPK from the public UI sources."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import sys

import preview
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.tv_web_build import compile_web
from cytv.package import IPK_MTIME


SERVICE_ID = 'com.cleanyourtv.root.preview.service'
SERVICE_SOURCE = Path(__file__).resolve().parent / 'service'
SERVICE_FILES = ('service.js','startup-diagnostics.js', 'app-inventory.js', 'handlers.js', 'services.json', 'package.json', 'boot-recover.sh', 'activity.json')


def tgz(files, executables=()):
    """Secure owned package leaves, without chmod records for platform containers."""
    from cytv.package import tgz as package_tgz
    return package_tgz(files, executable=executables)


def ar(parts):
    buffer = io.BytesIO(b'!<arch>\n')
    buffer.seek(0, 2)
    for name, data in parts.items():
        buffer.write((f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n').encode('ascii'))
        buffer.write(data)
        if len(data) % 2:
            buffer.write(b'\n')
    return buffer.getvalue()


def build(output, version='0.0.1', legacy_node_prototype=False):
    output = Path(output).absolute()
    if '..' in output.parts or any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('Output must not traverse symlinks or parent segments')
    files = compile_web(preview.prepare(version=version))
    info = json.loads(files['appinfo.json'])
    app_id = info['id']
    version = info['version']
    if app_id != 'com.cleanyourtv.root.preview':
        raise ValueError('Unexpected isolated candidate identity')
    payload = {'usr/palm/applications/' + app_id + '/' + name: data for name, data in files.items()}
    service_prefix = 'usr/palm/services/' + SERVICE_ID + '/'
    for service_file in SERVICE_FILES:
        path = SERVICE_SOURCE / service_file
        if SERVICE_SOURCE.is_symlink() or path.is_symlink() or not path.is_file():
            raise ValueError('Missing or indirect service source: ' + service_file)
        payload[service_prefix + service_file] = path.read_bytes()
    from startup_hook import packaged_content
    payload['usr/palm/applications/'+app_id+'/startup.sh']=packaged_content(app_id)
    from scripts.theme_receiver import inject
    private_service = inject({name[len(service_prefix):]: data for name, data in payload.items() if name.startswith(service_prefix)}, standalone=True)
    if legacy_node_prototype:
        from scripts.root_node_build import compile_root_node
        private_service = compile_root_node(private_service)
    payload.update({service_prefix + name: data for name, data in private_service.items()})
    service_info = json.loads(payload[service_prefix + 'services.json'])
    service_package = json.loads(payload[service_prefix + 'package.json'])
    if (service_info.get('id') != SERVICE_ID
            or service_info.get('services') != [{'name': SERVICE_ID}]
            or service_package.get('name') != SERVICE_ID
            or service_package.get('main') != 'service.js'):
        raise ValueError('Unexpected recovery service identity')
    payload['usr/palm/packages/' + app_id + '/packageinfo.json'] = (json.dumps({
        'id': app_id, 'version': version, 'app': app_id, 'services': [SERVICE_ID]
    }, indent=2) + '\n').encode()
    control = (f'Package: {app_id}\nVersion: {version}\nSection: misc\nPriority: optional\n'
               'Architecture: all\nMaintainer: Clean Your TV\n'
               'Description: Isolated Root Edition hardware-test candidate\n').encode()
    package = ar({'debian-binary': b'2.0\n', 'control.tar.gz': tgz({'control': control}),
                  'data.tar.gz': tgz(payload, {service_prefix + 'boot-recover.sh', 'usr/palm/applications/'+app_id+'/startup.sh'})})
    name = app_id + '_' + version + '_all.ipk'
    release = {
        'application_id': app_id, 'version': version,
        'hardware_validated': False, 'public_release_ready': False,
        'activates_system_home': False,
        'runtime_layout': 'inline-audio-v1',
        'capabilities': ['theme-receiver-v1'],
        'inventory': 'empty; configure locally for the later hardware test',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())},
    }
    from deploy import SUPPORT_FILES, RUNTIME_FILES, checked_file
    source = Path(__file__).resolve().parent
    support = {name: checked_file(source, name) for name in SUPPORT_FILES}
    support.update({'runtime/' + name: checked_file(source, 'runtime/' + name) for name in RUNTIME_FILES})
    if legacy_node_prototype:
        support = compile_root_node(support)
    output.mkdir(parents=False, exist_ok=False)
    (output / name).write_bytes(package)
    (output / 'SHA256SUMS').write_text(hashlib.sha256(package).hexdigest() + '  ' + name + '\n')
    (output / 'release.json').write_text(json.dumps(release, indent=2) + '\n')
    for relative, data in support.items():
        target = output / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
    bundle_files = {**support, name: package,
                    'SHA256SUMS': (output / 'SHA256SUMS').read_bytes(),
                    'release.json': (output / 'release.json').read_bytes()}
    (output / 'bundle.json').write_text(json.dumps({
        'package': name, 'files': {relative: hashlib.sha256(data).hexdigest()
                                 for relative, data in sorted(bundle_files.items())}
    }, indent=2) + '\n')
    return output / name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; parent must exist')
    parser.add_argument('--version', default='0.0.1', help='Root release version, X.Y.Z')
    parser.add_argument('--legacy-node-prototype', action='store_true', help='Host-only Node 0.12 prototype; admission remains Node 8+')
    args = parser.parse_args()
    try:
        package = build(args.output, version=args.version, legacy_node_prototype=args.legacy_node_prototype)
    except (ValueError, OSError) as exc:
        parser.exit(1, 'Candidate build failed: ' + str(exc) + '\n')
    print('Built ' + str(package) + '. Offline only; hardware validation pending.')


if __name__ == '__main__':
    main()

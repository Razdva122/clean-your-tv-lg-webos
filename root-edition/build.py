#!/usr/bin/env python3
"""Build an offline, isolated Root candidate IPK from the public UI sources."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import struct

import preview
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.tv_web_build import compile_web
from cytv.package import ar


SERVICE_ID = 'com.cleanyourtv.root.preview.service'
SERVICE_SOURCE = Path(__file__).resolve().parent / 'service'
SERVICE_FILES = ('service.js','c1-lease.js','startup-diagnostics.js', 'app-inventory.js', 'presentation-context.js', 'handlers.js', 'services.json', 'package.json', 'boot-recover.sh', 'activity.json')


def validate_native_gate(data):
    """Admit a static ARM EABI5 executable, not an ELF-shaped placeholder."""
    def reject():
        raise ValueError('Experimental C1 gate requires a static ARM32 EABI5 executable')
    if len(data) < 84 or len(data) > 4 * 1024 * 1024 or data[:7] != b'\x7fELF\x01\x01\x01':
        reject()
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    _, kind, machine, version, entry, phoff, _, flags, ehsize, phsize, count, _, _, _ = h
    if (kind != 2 or machine != 40 or version != 1 or ehsize != 52 or phsize != 32
            or not 1 <= count <= 128 or phoff < 52 or phoff + count * 32 > len(data)
            or flags >> 24 != 5 or flags & 0x400):
        reject()
    executable = False
    for offset in range(phoff, phoff + count * 32, 32):
        ptype, start, address, _, size, memory, permissions, _ = struct.unpack_from('<IIIIIIII', data, offset)
        if ptype in (2, 3):  # No dynamic loader or dynamic linking contract on the TV.
            reject()
        if ptype == 1:
            if size > memory or start + size > len(data) or address + memory > 0x100000000:
                reject()
            executable |= bool(permissions & 1 and address <= entry < address + size)
    if not executable:
        reject()


def bundle_presentation_context(files):
    """Keep the immutable private-service inventory while shipping its closure."""
    files = dict(files)
    needle = b"require('./presentation-context')"
    if files['service.js'].count(needle) != 1:
        raise ValueError('Expected one Root presentation context factory')
    source = files['presentation-context.js']
    bundled = (b'(function(){var module={exports:{}};\n' + source
               + b'\nreturn module.exports;}())')
    files['service.js'] = files['service.js'].replace(needle, bundled)
    return files


def bundle_c1_lease(files):
    """Inline the optional broker without expanding legacy private inventories."""
    files=dict(files)
    needle=b"require('./c1-lease')"
    if files['service.js'].count(needle)!=1:raise ValueError('Expected one C1 lease factory')
    source=files.pop('c1-lease.js')
    bundled=b'(function(){var module={exports:{}};\n'+source+b'\nreturn module.exports;}())'
    files['service.js']=files['service.js'].replace(needle,bundled)
    return files


def bundle_weather(files):
    """Inline the shared fixed MET transport and trust in the owned service leaf."""
    import re
    from deploy import checked_file
    files = dict(files)
    needle = b"require('./weather')"
    if files['service.js'].count(needle) != 1:
        raise ValueError('Expected one Root weather registration')
    root = Path(__file__).resolve().parents[1] / 'renewal-service'
    source = checked_file(root, 'weather.js')
    ca = checked_file(root, 'ca-bundle.crt').decode('utf-8')
    license = checked_file(root, 'ca-LICENSE.txt').replace(b'*/', b'* /')
    pattern = rb"require\('fs'\)\.readFileSync\(\s*__dirname \+ '/ca-bundle.crt',\s*'utf8'\s*\)"
    source, count = re.subn(pattern, lambda _: json.dumps(ca).encode(), source)
    if count != 1:
        raise ValueError('Expected one canonical weather CA import')
    bundled = (b'(function(){var module={exports:{}};\n/* Mozilla CA bundle license\n'
               + license + b'\n*/\n' + source + b'\nreturn module.exports;}())')
    files['service.js'] = files['service.js'].replace(needle, bundled)
    return files


def tgz(files, executables=()):
    """Secure owned package leaves, without chmod records for platform containers."""
    from cytv.package import tgz as package_tgz
    return package_tgz(files, executable=executables)


def build(output, version='0.0.1', legacy_node_prototype=False, resolution=None, experimental_c1_gate=None, experimental_c1_keyfilter=None, legacy_node_beta=False, c1_mount_recovery=None):
    output = Path(output).absolute()
    if '..' in output.parts or any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('Output must not traverse symlinks or parent segments')
    native_gate = None
    keyfilter = experimental_c1_keyfilter is not None
    if keyfilter and experimental_c1_gate is not None:
        raise ValueError('Select exactly one experimental C1 routing helper')
    experimental_helper = experimental_c1_keyfilter if keyfilter else experimental_c1_gate
    if experimental_helper is not None:
        from deploy import checked_file
        candidate = Path(experimental_helper).absolute()
        native_gate = checked_file(candidate.parent, candidate.name)
        validate_native_gate(native_gate)
        if legacy_node_prototype or (legacy_node_beta and not keyfilter):
            raise ValueError('Legacy Node Beta only admits mount-free compositor routing; the host prototype is not admitted')
    recovery_gate = None
    if c1_mount_recovery is not None:
        if not keyfilter or legacy_node_beta:
            raise ValueError('Legacy mount recovery is installer-only support for the current native bundle')
        from deploy import checked_file
        candidate = Path(c1_mount_recovery).absolute()
        recovery_gate = checked_file(candidate.parent, candidate.name)
        validate_native_gate(recovery_gate)
    files = compile_web(preview.prepare(version=version, resolution=resolution))
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
    private_service = bundle_presentation_context({name[len(service_prefix):]: data for name, data in payload.items() if name.startswith(service_prefix)})
    private_service = bundle_c1_lease(private_service)
    private_service = bundle_weather(private_service)
    private_service = inject(private_service, standalone=True)
    payload.pop(service_prefix+'c1-lease.js')
    if legacy_node_beta:
        private_service['service.js'] = b"require('./startup-diagnostics');\n" + private_service['service.js']
    if legacy_node_prototype or legacy_node_beta:
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
        'capabilities': ['theme-receiver-v1','wallpaper-media-v1'],
        'inventory': 'empty; configure locally for the later hardware test',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())},
    }
    if legacy_node_beta:
        release['runtime_variant'] = 'node012-beta'
        release['automatic_updates'] = False
    if native_gate is not None:
        release.update(home_backend='c1-native-gate', experimental=True,
                       native_sha256=hashlib.sha256(native_gate).hexdigest())
        if keyfilter:
            release['routing'] = 'compositor-keyfilter-v1'
            release['compositor_admission'] = 3
            release['capabilities'].append('c1-keyfilter-v1')
    from deploy import SUPPORT_FILES, RUNTIME_FILES, checked_file
    source = Path(__file__).resolve().parent
    support = {name: checked_file(source, name) for name in SUPPORT_FILES}
    support.update({'runtime/' + name: checked_file(source, 'runtime/' + name) for name in RUNTIME_FILES})
    if native_gate is not None:
        helper_name = 'c1-keyfilter-guard' if keyfilter else 'c1-home-gate'
        support['runtime/' + helper_name] = native_gate
        support['runtime/c1_gate.py'] = checked_file(source, 'runtime/c1_gate.py')
        if keyfilter:
            for extra in ('c1_keyfilter.py', 'c1-home-filter.js'):
                support['runtime/' + extra] = checked_file(source, 'runtime/' + extra)
    if recovery_gate is not None:
        # Current trusted recovery for retained schema-1 installations only.
        # deploy.install still copies only the explicitly selected compositor.
        support['runtime/c1-home-gate'] = recovery_gate
    if legacy_node_beta:
        from scripts.root_node_build import compile_root_beta
        support = compile_root_beta(support)
    elif legacy_node_prototype:
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
    parser.add_argument('--legacy-node-beta', action='store_true', help='Explicit Node 0.12.2 Beta payload with ordinary OTA disabled')
    parser.add_argument('--resolution', choices=('1280x720', '1920x1080'), help='Explicit graphics resolution for this candidate package')
    parser.add_argument('--experimental-c1-gate', type=Path, metavar='ARM_BINARY',
                        help='Explicit developer-only C1 backend; excluded from normal installer and OTA')
    parser.add_argument('--experimental-c1-keyfilter', type=Path, metavar='ARM_BINARY',
                        help='Explicit mount-free C1 compositor routing guardian')
    parser.add_argument('--c1-mount-recovery', type=Path, metavar='ARM_BINARY',
                        help='Installer-only recovery for retained schema-1 native Home')
    args = parser.parse_args()
    try:
        package = build(args.output, version=args.version, legacy_node_prototype=args.legacy_node_prototype, legacy_node_beta=args.legacy_node_beta,
                        resolution=args.resolution, experimental_c1_gate=args.experimental_c1_gate, experimental_c1_keyfilter=args.experimental_c1_keyfilter, c1_mount_recovery=args.c1_mount_recovery)
    except (ValueError, OSError) as exc:
        parser.exit(1, 'Candidate build failed: ' + str(exc) + '\n')
    print('Built ' + str(package) + '. Offline only; hardware validation pending.')


if __name__ == '__main__':
    main()

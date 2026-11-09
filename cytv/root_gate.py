"""Fresh C1 installation inside the common installer, with native recovery only."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import tempfile
import tarfile
import uuid

from . import package
from .errors import UserError
from .state import private_write

BACKEND = 'c1-native-gate'
NOTICE = 'C1 Beta: native Home control selected automatically. Power recovery and TV controls are still being tested.'
GRAPHICS = {'1920x1080': 'root-c1', '1280x720': 'root-c1-720p'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_bundle(data, resolution):
    manifest = json.loads(data['bundle.json'])
    files = manifest['files']
    if (not isinstance(files, dict) or not files or 'bundle.json' in files
            or set(data) != set(files) | {'bundle.json'}):
        raise ValueError('Invalid native bundle inventory')
    for name, expected in files.items():
        package.safe_name(name)
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected) or digest(data[name]) != expected:
            raise ValueError('Invalid native bundle hash')
    release = json.loads(data['release.json'])
    routing = release.get('routing')
    if routing not in (None, 'compositor-keyfilter-v1'):
        raise ValueError('Unknown C1 routing payload')
    helper = 'runtime/c1-keyfilter-guard' if routing else 'runtime/c1-home-gate'
    if routing and not {'runtime/c1_keyfilter.py','runtime/c1-home-filter.js'}.issubset(files):
        raise ValueError('Missing compositor routing payload')
    native = files[helper]
    if (release.get('home_backend') != BACKEND or release.get('experimental') is not True
            or release.get('application_id') != package.ROOT_APP
            or release.get('native_sha256') != native or 'runtime/c1_gate.py' not in files
            or manifest.get('package') not in files
            or not isinstance(release.get('version'), str)
            or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}', release['version'])
            or manifest['package'] != package.ROOT_APP+'_'+release['version']+'_all.ipk'):
        raise ValueError('Native backend identity changed')
    raw = data[manifest['package']]
    package.verify_root_rollback_format(raw)
    contents = package.data_files(raw)
    info = json.loads(contents['usr/palm/applications/'+package.ROOT_APP+'/appinfo.json'])
    if (info.get('id') != package.ROOT_APP or info.get('version') != release['version']
            or info.get('resolution') != resolution
            or release.get('files') != {name: digest(raw) for name, raw in contents.items()}):
        raise ValueError('Native package identity changed')
    return manifest, release


def source_bundle(installer):
    capability = installer.manifest['root_backends'][BACKEND]
    resolution = installer.tv_info['graphics_resolution']
    if (capability.get('experimental') is not True or capability.get('hardware_validated') is not False
            or capability.get('graphics') != GRAPHICS or resolution not in GRAPHICS):
        raise ValueError('Invalid native graphics capability')
    variant = capability['graphics'][resolution]
    def read(name):
        name = variant+'/'+package.safe_name(name)
        for parent in (*PurePosixPath(name).parents, PurePosixPath(name)):
            if str(parent) != '.' and (installer.payload/str(parent)).is_symlink():
                raise ValueError('Indirect native bundle path')
        raw = (installer.payload/name).read_bytes()
        if digest(raw) != installer.manifest['files'][name]:
            raise ValueError('Native payload changed')
        return raw
    raw = read('bundle.json')
    manifest = json.loads(raw)
    if not isinstance(manifest.get('files'), dict):
        raise ValueError('Invalid native bundle')
    data = {'bundle.json': raw}
    for name in manifest['files']:
        data[name] = read(name)
    _, release = validate_bundle(data, resolution)
    if release.get('runtime_variant') != installer.profile.get('root_variant'):
        raise ValueError('Home backend runtime does not match the selected Root variant')
    if installer.tv_info.get('home_backend_schema') == 3 and (
            release.get('routing') != 'compositor-keyfilter-v1' or release.get('compositor_admission') != 3):
        raise ValueError('Generic compositor admission requires a matching mount-free payload')
    return data


def native_proof(device):
    if not isinstance(device, dict) or device.get('backend') != BACKEND:
        return None
    value = device.get('effective')
    keyfilter = isinstance(value, dict) and value.get('routing') == 'compositor-keyfilter-v1'
    if isinstance(value, dict) and 'routing' in value and not keyfilter:
        return None
    if (not isinstance(value, dict) or value.get('returnValue') is not True
            or value.get('backend') != BACKEND or value.get('profiles', {}) is not None
            or any(type(value.get(k)) is not bool for k in ('stock_verified','mounted','healthy'))
            or type(value.get('guardian_pid')) is not int or value['guardian_pid'] < 0
            or value['stock_verified'] and value['mounted']
            or value['healthy'] and (value['guardian_pid'] <= 1 or not keyfilter and not value['mounted'])):
        return None
    if keyfilter and (value['mounted'] is not False
            or any(type(value.get(k)) is not bool for k in ('filter_installed', 'routing_active', 'stopped'))
            or value['healthy'] and (not value['filter_installed'] or not value['routing_active'] or value['stopped'])
            or value['routing_active'] and not value['healthy']
            or value['stock_verified'] and (value['filter_installed'] or value['routing_active'] or value['guardian_pid'])):
        return None
    return value


def stock_proof(device):
    value = native_proof(device)
    return bool(value and value['stock_verified'] and not value['mounted']
                and not value['healthy'] and value['guardian_pid'] == 0)


def install(installer, inventory, migrate=False, reinstall=None):
    """One component submission; uncertainty retains the host/device receipts.

    Device deploy.experimental_admission rechecks the full fresh-install snapshot
    under the installation mutex before creating Root state or submitting IPKs.
    This host path never stages a normal updater or retries a failed native setup.
    """
    if migrate or reinstall is not None:
        raise UserError('Experimental Home setup requires a fresh installation without migration. Existing recovery data was kept.')
    if installer.store.pending(installer.profile):
        raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
    try:
        data = source_bundle(installer)
        with tempfile.TemporaryDirectory(prefix='cytv-c1-root-') as folder:
            bundle = Path(folder)/'root';bundle.mkdir()
            for name, raw in data.items():
                path = bundle/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
            package.personalize_root(bundle, inventory, tv_name=getattr(installer, 'tv_name', None))
            prepared = {name: (bundle/name).read_bytes() for name in data}
            validate_bundle(prepared, installer.tv_info['graphics_resolution'])
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, tarfile.TarError) as error:
        raise UserError('Experimental Home packages are missing or invalid. Use a complete installer build. Installation has not started.') from error
    from . import storage
    storage.install(installer.remote, prepared, installer.progress, root=True)
    installer.progress('Experimental compositor Home: physical controls and power recovery are unverified.'
                       if installer.tv_info.get('home_backend_schema') == 3 else NOTICE)
    installer.store.begin(installer.profile, 'install', release_sha=digest(prepared['release.json']),
                          bundle_sha=digest(prepared['bundle.json']), migrate=False, requires_updater=False,
                          home_backend=BACKEND, stage='upload')
    installer.progress('Uploading Root and recovery runtime…')
    if getattr(installer,'_native_clean_install',False):
        with tempfile.TemporaryDirectory(prefix='cytv-c1-root-') as folder:
            bundle=Path(folder)/'root';bundle.mkdir()
            for name,raw in prepared.items():
                path=bundle/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            stage=installer.upload_product(bundle)
        operation=uuid.uuid4().hex
        installer.store.checkpoint(installer.profile,stage='setup',product_operation=operation,product_payload=stage)
        reply=installer.product_action('native-install',operation,stage)
        if reply.get('state')!='complete':
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.',reason_code='pending-operation')
        result=reply.get('result')
    else:
        stage = '/tmp/cytv-c1-root-'+uuid.uuid4().hex
        installer.remote.run('umask 077; mkdir '+shlex.quote(stage))
        for name, raw in prepared.items():
            target = stage+'/'+name
            installer.remote.run('mkdir -p '+shlex.quote(str(PurePosixPath(target).parent)))
            installer.remote.upload(target, raw, mode=0o600)
        installer.store.checkpoint(installer.profile, stage='setup')
        result = installer.root_action('install', bundle=stage, experimental=True)
    if (not isinstance(result, dict) or result.get('returnValue') is not True
            or result.get('installed') != package.ROOT_APP or result.get('home_changed') is not False):
        raise UserError('C1 installation was not confirmed. Keep recovery state and run cytv status.')
    status = installer.root_action('status')
    device = status.get('result', {}) if isinstance(status, dict) else {}
    if not stock_proof(device) or not isinstance(device.get('recovery'), dict) or device['recovery'].get('integrity_verified') is not True:
        raise UserError('C1 recovery could not be verified. Run cytv status; activation has not started.')
    installer.outcome.packages_verified()
    private_write(installer.store.device_dir(installer.profile)/'installation.json',
                  json.dumps({'home_backend': BACKEND, 'experimental': True, 'hardware_validated': False}).encode())
    installer.store.checkpoint(installer.profile, action='activate-root', stage='stop-helper',
                               requires_updater=False, home_backend=BACKEND)
    launched = installer.activate_root()
    return dict(result, home_changed=True, launch_requested=launched, updates_ready=False, beta=True, backend=BACKEND)


PROJECT_APPS = {package.ROOT_APP, 'com.gathin.tvhome', 'com.local.nativehome',
                'com.cleanyourtv.updater', 'com.cleanyourtv.root.updater',
                'com.cleanyourtv.system.updater'}
ROOT_STATE = '/var/lib/clean-your-tv-root'


def project_apps(installer):
    apps = installer.installed_apps()
    if not isinstance(apps, list) or any(not isinstance(app,dict) or not isinstance(app.get('id'),str) for app in apps):
        raise UserError('Installed applications could not be verified. Removal has not started.')
    return {app['id'] for app in apps} & PROJECT_APPS


def remove_project(installer):
    """Remove only a lone native Root; never promise removal of untouched apps."""
    present = project_apps(installer)
    if present - {package.ROOT_APP}:
        raise UserError('Other Clean Your TV components are installed. C1 full removal cannot verify them; no removal was started.')
    pending = installer.store.pending(installer.profile)
    terminal = False
    if pending:
        if pending.get('action') != 'uninstall':
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore before removal.', reason_code='pending-operation')
        status = installer.status()
        if installer.store.pending(installer.profile):
            raise UserError('Previous package removal is not verified. It was not submitted again; keep recovery data.')
        terminal = status.get('deployment_stage') == 'uninstalled-state-retained'
        if not terminal:
            raise UserError('Previous package removal is not verified. It was not submitted again; keep recovery data.')
    status = installer.root_action('status')
    device = status.get('result', {}) if isinstance(status,dict) else {}
    if native_proof(device) is None:
        raise UserError('Native C1 recovery could not be verified. Removal has not started.')
    if not terminal and package.ROOT_APP not in present:
        observed = installer.status()
        terminal = observed.get('deployment_stage') == 'uninstalled-state-retained'
        if not terminal:
            raise UserError('Previous package removal is not verified. It was not submitted again; keep recovery data.')
    if not terminal:
        recovery = device.get('recovery')
        if not isinstance(recovery,dict) or recovery.get('integrity_verified') is not True:
            raise UserError('Native C1 recovery could not be verified. Removal has not started.')
        removed = installer.uninstall(full_project=False)
        if (not isinstance(removed,dict) or removed.get('removed') != package.ROOT_APP
                or removed.get('state_retained') != ROOT_STATE):
            raise UserError('C1 removal was not confirmed. Keep recovery state and run cytv status.')
    status = installer.root_action('status')
    device = status.get('result', {}) if isinstance(status,dict) else {}
    if project_apps(installer) or not stock_proof(device):
        raise UserError('Original LG Home or package removal could not be verified. Keep recovery data; removal is incomplete.')
    installer.verify_project_startup_removed()
    return dict(removed=True, applications_services_startup_removed=True, state_retained=ROOT_STATE)

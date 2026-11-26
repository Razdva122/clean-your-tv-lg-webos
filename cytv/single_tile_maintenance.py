"""In-place maintenance of a Developer Mode generation-two Home and its daily tile."""
import hashlib
import json
import re
import shlex

from . import no_root_observer, package, storage
from .errors import UserError
from .operations import HELPER, HOME, SYSTEM_UPDATER_APP, UPDATER_APP
from .single_tile_setup import app_metadata, installed_role, read_app_file


def admission(installer, apps):
    home = app_metadata(installer, HOME)
    helper = app_metadata(installer, HELPER)
    if all('cytvProductGeneration' not in info for info in (home, helper)) and package.TILE_APP not in apps:
        return None
    connection = installer.profile.get('connection') or 'developer-mode'
    if connection != 'developer-mode' or not read_app_file(installer, HOME, 'apps.js').endswith(
            'window.CYTVNoRootConnection = "developer-mode";\n'):
        raise UserError('Use the saved connection for this Clean Your TV installation.', reason_code='existing-installation')
    if (any(info.get('cytvProductGeneration') != 2 or info.get('visible') is not False for info in (home, helper))
            or any(app in apps for app in (package.ROOT_APP, UPDATER_APP, SYSTEM_UPDATER_APP, 'com.cleanyourtv.updater'))
            or package.TILE_APP in apps and installed_role(installer) != 'no-root'):
        raise UserError('Check the existing Clean Your TV installation before continuing.', reason_code='existing-installation')
    for app in (package.ROOT_APP, UPDATER_APP, SYSTEM_UPDATER_APP, 'com.cleanyourtv.updater'):
        installer.verify_absent(app)
    if package.TILE_APP not in apps:
        installer.verify_absent(package.TILE_APP)
    if package.SCREENSAVER_APP not in apps:
        installer.verify_absent(package.SCREENSAVER_APP)
    if (home.get('version') != apps[HOME] or helper.get('version') != apps[HELPER]
            or helper.get('version') != installer.manifest['helper_version']):
        # Its private state directory is inside the package, alongside the
        # stop latch and pairing key. Keep it until a verified transfer exists.
        raise UserError('Use the installer for the installed Clean Your TV version.', reason_code='existing-installation')
    ids = (HOME, HELPER, package.TILE_APP, package.SCREENSAVER_APP)
    return {'maintenance': {app: apps[app] for app in ids if app in apps}}


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,8}(\.[0-9]{1,8}){2}', value):
        raise UserError('The TV package result could not be verified.', reason_code='version-mismatch')
    return tuple(map(int, value.split('.')))


def inventory(installer):
    # Re-serialize only data emitted by package.inventory_script. The TV source
    # is never copied to the new app or evaluated by the installer.
    source = read_app_file(installer, HOME, 'apps.js')
    marker = 'window.TV_APPS = '
    if not source.startswith(marker):
        raise UserError('The TV package result could not be verified.', reason_code='version-mismatch')
    data, end = json.JSONDecoder().raw_decode(source[len(marker):])
    rest = source[len(marker) + end:]
    fallback = ';\nwindow.CYTVPackagedIconFallback = '
    if rest.startswith(fallback):
        data['fallbackIcon'], _ = json.JSONDecoder().raw_decode(rest[len(fallback):])
    package.inventory_script(data)
    return data


def digests(raw):
    from .operations import BASE
    return {BASE.removesuffix('/usr/palm') + '/' + path: hashlib.sha256(data).hexdigest()
            for path, data in package.data_files(raw).items()}


def tile_matches(installer, raw):
    # A missing regular file or a content mismatch can be repaired. Refuse
    # ambiguous OS errors, indirect paths, races, and transport uncertainty.
    check = ("try {" + no_root_observer.FILE_CHECK + "} catch(e) {"
             "if(e.code!=='ENOENT'&&e.message!=='changed-content')throw e;"
             "process.stdout.write('CYTV_TILE_MISMATCH');}")
    reply = installer.remote.run('/usr/bin/node -e ' + shlex.quote(check) + ' ' +
                                 shlex.quote(no_root_observer.canonical(digests(raw)))).strip()
    if reply not in ('CYTV_ORIGINAL_FILES_VERIFIED', 'CYTV_TILE_MISMATCH'):
        raise UserError('The TV package result could not be verified.', reason_code='version-mismatch')
    return reply == 'CYTV_ORIGINAL_FILES_VERIFIED'


def run(installer, source):
    if source != installer.single_tile_source():
        raise UserError('The Clean Your TV installation changed.', reason_code='pending-operation')
    installed = source['maintenance']
    installer.select_graphics()
    tile, tile_version = package.tile_payload(installer.payload, installer.manifest, 'no-root')
    tile_name = package.TILE_FILES['no-root']
    if package.TILE_APP in installed and version(installed[package.TILE_APP]) > version(tile_version):
        raise UserError('Use the installer for the installed Clean Your TV version.', reason_code='version-mismatch')
    bundles, versions = {}, {}
    if (package.TILE_APP not in installed or version(installed[package.TILE_APP]) < version(tile_version)
            or not tile_matches(installer, tile)):
        bundles[tile_name] = tile
        versions[package.TILE_APP] = tile_version
    target = installer.manifest['home_version']
    if version(target) < version(installed[HOME]):
        raise UserError('Use the installer for the installed Clean Your TV version.', reason_code='version-mismatch')
    if version(target) > version(installed[HOME]):
        launcher = (installer.payload / installer._graphics_paths['launcher']).read_bytes()
        bundles['launcher.ipk'], _ = package.personalize(launcher, HOME, inventory(installer),
                                                        no_root_connection='developer-mode')
        versions[HOME] = target
    saver = package.screensaver_payload(installer.payload, installer.manifest)
    if saver and (package.SCREENSAVER_APP not in installed or version(saver[1]) > version(installed[package.SCREENSAVER_APP])):
        bundles[package.SCREENSAVER_IPK], versions[package.SCREENSAVER_APP] = saver
    if not bundles:
        return {'maintained': 'no-root', 'launch_requested': False}
    expected = {path: digest for raw in bundles.values() for path, digest in digests(raw).items()}
    installer.outcome.begin()
    ramfs = storage.install(installer.remote, bundles, installer.progress)
    if source != installer.single_tile_source():
        raise UserError('The Clean Your TV installation changed.', reason_code='pending-operation')
    pending = no_root_observer.begin(installer, 'install', bundles, versions, expected, {}, ramfs=ramfs,
                                    maintenance=list(bundles))
    return installer.continue_no_root(pending)

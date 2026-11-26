"""Continue Root setup in the full Homebrew tile only on a clean television."""

from . import package, prompts
from .errors import UserError
from .operations import require_root_reinstall_cleanup
from .single_tile_setup import installed_role


def handoff(installer, write, ask, *, non_interactive):
    """Opening the tile delegates review and any installation consent to the TV."""
    if installer.profile['edition'] != 'root' or installer.store.pending(installer.profile):
        raise UserError('Use the installer for the installed Clean Your TV version.',
                        reason_code='pending-operation')
    products = ('com.gathin.tvhome', 'com.local.nativehome', 'com.cleanyourtv.updater',
                package.ROOT_APP, 'com.cleanyourtv.root.updater', 'com.cleanyourtv.system.updater')
    def product_versions():
        return {item['id']: item.get('version') for item in installer.installed_apps()
                if item['id'] in products or item['id'] == package.TILE_APP}
    apps = product_versions()
    legacy = {package.ROOT_APP, 'com.cleanyourtv.root.updater'}
    present = set(apps).intersection(products)
    if present and not (legacy <= present <= legacy | {'com.cleanyourtv.system.updater'}):
        raise UserError('Check the existing Clean Your TV installation before continuing.',
                        reason_code='existing-installation')
    if package.TILE_APP not in apps:
        raise UserError('To start Root setup, install the full Clean Your TV Homebrew package on the TV.',
                        reason_code='unsupported-operation')
    if installed_role(installer, require_tile_protocol=True) != 'homebrew':
        raise UserError('The installed Clean Your TV entry belongs to another installation.',
                        reason_code='existing-installation')
    for app in products:
        if app not in present:
            installer.verify_absent(app)
    if present:
        source = installer.root_installation()
        if (source.get('state') != 'installed' or source.get('can_maintain') is not True
                or source.get('tile_protocol') is not None or installer.native_root_present()):
            raise UserError('Check the existing Clean Your TV installation before continuing.',
                            reason_code='existing-installation')
        write('LG Home will be restored. Clean Your TV, its updaters, Home Helper and saved preferences will be removed.')
        if non_interactive or not prompts.confirm('Remove this Root installation to switch to one tile?', ask, write):
            return 130
        if (installer.store.pending(installer.profile) or product_versions() != apps
                or installed_role(installer, require_tile_protocol=True) != 'homebrew'
                or installer.root_installation() != source):
            raise UserError('The Clean Your TV installation changed.', reason_code='pending-operation')
        require_root_reinstall_cleanup(installer.uninstall_project())
        for app in products:
            installer.verify_absent(app)
        if installed_role(installer, require_tile_protocol=True) != 'homebrew':
            raise UserError('The Clean Your TV installation changed.', reason_code='pending-operation')
    if non_interactive or not prompts.confirm('Open Clean Your TV on the TV to continue setup?', ask, write):
        return 130
    reply = installer.remote.luna('com.webos.applicationManager/launch', {'id': package.TILE_APP})
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        raise UserError('The TV package result could not be verified.', reason_code='unsupported-operation')
    write('Continue setup on the TV.')
    return 0

"""Continue Root setup in the full Homebrew tile only on a clean television."""

from . import package, prompts
from .errors import UserError
from .no_root_cleanup import _exact_developer_app
from .single_tile_setup import installed_role


def handoff(installer, write, ask, *, non_interactive):
    """Opening the tile delegates review and any installation consent to the TV."""
    if installer.profile['edition'] != 'root' or installer.store.pending(installer.profile):
        raise UserError('Use the installer for the installed Clean Your TV version.',
                        reason_code='pending-operation')
    apps = {item['id'] for item in installer.installed_apps()}
    products = ('com.gathin.tvhome', 'com.local.nativehome', 'com.cleanyourtv.updater',
                package.ROOT_APP, 'com.cleanyourtv.root.updater', 'com.cleanyourtv.system.updater')
    if apps.intersection(products):
        raise UserError('Check the existing Clean Your TV installation before continuing.',
                        reason_code='existing-installation')
    for app in products:
        installer.verify_absent(app)
    if package.TILE_APP not in apps:
        raise UserError('To start Root setup, install the full Clean Your TV Homebrew package on the TV.',
                        reason_code='unsupported-operation')
    if not _exact_developer_app(installer, package.TILE_APP) or installed_role(installer, require_tile_protocol=True) != 'homebrew':
        raise UserError('The installed Clean Your TV entry belongs to another installation.',
                        reason_code='existing-installation')
    if non_interactive or not prompts.confirm('Open Clean Your TV on the TV to continue setup?', ask, write):
        return 130
    reply = installer.remote.luna('com.webos.applicationManager/launch', {'id': package.TILE_APP})
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        raise UserError('The TV package result could not be verified.', reason_code='unsupported-operation')
    write('Continue setup on the TV.')
    return 0

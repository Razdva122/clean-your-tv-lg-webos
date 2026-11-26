"""Explicit clean transition from an eligible ordinary No-root installation."""

from . import prompts
from .errors import UserError
from .operations import require_root_reinstall_cleanup


def select_source(installer, write, ask, *, non_interactive):
    source = installer.single_tile_source()
    if not source:
        return True

    # A's built-in snapshot excludes browser media and service/pairing state.
    # The existing complete-removal path is a separate owner choice. It cannot
    # confer approval to start the new install, even after verified removal.
    write('A clean installation removes your CYTV layout, themes, personal wallpapers, preferences and TV pairing. Returning to the previous version requires uninstalling and installing that version again.')
    if non_interactive or not prompts.confirm('Remove this No-root installation to switch to one tile?', ask, write, default=False):
        return False
    installer.select_graphics()
    installer.preflight(install=True, defer_helper=True)
    if installer.single_tile_source() != source:
        raise UserError('The installation changed. Check TV status before continuing.',
                        reason_code='pending-operation')
    result = installer.uninstall_project()
    require_root_reinstall_cleanup(result)
    installer.require_fresh_single_tile()
    return prompts.confirm('Install Clean Your TV with one tile now?', ask, write, default=False)

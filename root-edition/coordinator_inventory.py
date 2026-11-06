"""Data-only shared worker inventory; safe for host verification on all platforms."""
BUNDLED_FILES=('coordinator_inventory.py', 'install_driver.py', 'install_device.py', 'system_setup.py', 'root_package.py', 'app-inventory.js', 'cleanup_root_updater.py', 'cleanup_system_updater.py', 'cleanup_legacy_permissions.py', 'cleanup_app_permissions.py', 'cleanup_root_archive.py', 'system_updater/__init__.py', 'system_updater/core.py', 'system_updater/device.py', 'system_updater/support/__init__.py', 'system_updater/support/package.py', 'system_updater/support/store.py', 'system_updater/support/profile.py', 'system_updater/support/luna.py')
# Current installer staging authenticates these helpers without extending the
# fixed infrastructure destinations pinned by already installed supervisors.
INSTALLER_ONLY_FILES=('cancel_install.py','cancel_provision.py','clean_removal.py','cleanup_tail.js','cleanup_no_root_private.js')
BUNDLED_FILES += INSTALLER_ONLY_FILES

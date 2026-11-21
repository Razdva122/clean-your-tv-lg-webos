"""Shared runtime assets for the No-root package builders."""

UPDATER_APP_FILES = ('app.js', 'appinfo.json', 'icon.png', 'index.html', 'largeIcon.png')
UPDATER_SERVICE_FILES = (
    'ca-LICENSE.txt', 'ca-bundle.crt', 'manager.js', 'package.json', 'permissions.js',
    'policy.js', 'release-public.pem', 'service.js', 'services.json', 'storage.js', 'transport.js',
)
UPDATER_FONT_FAMILIES = ('NotoSans', 'NotoSansDevanagari', 'NotoSansKR', 'NotoSansSC', 'NotoSansTC')


def _public_files(directory, names):
    directory = directory.absolute()
    files = {}
    for name in names:
        path = directory / name
        if not path.is_file() or path.resolve() != path:
            raise ValueError('Missing or indirect public source: ' + str(path))
        files[name] = path.read_bytes()
    return files


def updater_sources(root):
    """Select the public app and service inputs for both IPK builders."""
    app = _public_files(root / 'updater-app', UPDATER_APP_FILES)
    app.update(updater_app_assets(root))
    service = _public_files(root / 'updater-service', UPDATER_SERVICE_FILES)
    service.update(updater_service_assets(root))
    return app, service


def renewal_service_assets(root):
    from scripts.theme_receiver import inject

    files = inject({}, root=root)
    files.update({name: (root / 'native/app' / name).read_bytes()
                  for name in ('state-permissions.js', 'contract-events.js')})
    return files


def updater_app_assets(root):
    launcher = root / 'launcher'
    files = _public_files(launcher, (
        'settings-panel.css', 'renewal-panel.css', 'i18n.js', 'catalogs.js', 'i18n.css',
        'system-updates.js', 'release-notes.js',
        *('fonts/' + family + suffix for family in UPDATER_FONT_FAMILIES
          for suffix in ('.ttf', '-OFL.txt')),
    ))
    files.update(_public_files(root / 'root-edition/ui', ('root-locales.js',)))
    return files


def updater_service_assets(root):
    return _public_files(root / 'launcher', ('user-data.js',))

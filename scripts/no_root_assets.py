"""Shared runtime assets for the No-root package builders."""


def renewal_service_assets(root):
    from scripts.theme_receiver import inject

    files = inject({}, root=root)
    files.update({name: (root / 'native/app' / name).read_bytes()
                  for name in ('state-permissions.js', 'contract-events.js')})
    return files


def updater_app_assets(root):
    launcher = root / 'launcher'
    files = {name: (launcher / name).read_bytes()
             for name in ('settings-panel.css', 'renewal-panel.css', 'i18n.js', 'catalogs.js', 'i18n.css',
                          'system-updates.js', 'release-notes.js')}
    files['root-locales.js'] = (root / 'root-edition/ui/root-locales.js').read_bytes()
    for font in (launcher / 'fonts').glob('NotoSans*'):
        if font.is_file():
            files['fonts/' + font.name] = font.read_bytes()
    return files


def updater_service_assets(root):
    return {'user-data.js': (root / 'launcher/user-data.js').read_bytes()}

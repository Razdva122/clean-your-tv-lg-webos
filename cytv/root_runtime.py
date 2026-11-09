"""Explicit legacy choices before any installation submission."""
import re

from . import state, prompts
from .errors import UserError

BETA = 'node012-beta'
NO_ROOT_TITLE = 'No-root — reduced functionality'
NO_ROOT_DETAIL = 'Home with Home Helper, without system Home routing or Root-only controls. Uses existing root SSH; Developer Mode is not installed.'
BETA_TITLE = 'Root Beta — not sufficiently tested'
NOTICE = 'Root Beta for Node.js 0.12.2 is not sufficiently tested on TVs. Automatic updates are unavailable. Please share voluntary feedback after testing.'
FEEDBACK = 'Please save the diagnostic report and share your result: model, firmware, remote, Home, emergency exit, sound, standby and cold boot. Mark untested checks. Nothing is sent automatically.'
NODE_BETA_PROBE = '/usr/bin/node -e \'process.exit(process.versions.node === "0.12.2" ? 0 : 1)\''
FRESH_PROBE = '''for cytv_path in /var/lib/clean-your-tv-root /var/lib/clean-your-tv-root-updater /var/lib/clean-your-tv-system-updater /var/lib/clean-your-tv-installation; do
if [ -e "$cytv_path" ] || [ -L "$cytv_path" ]; then printf CYTV_RETAINED_ROOT; exit 0; fi
done
for cytv_app in com.cleanyourtv.root.preview com.cleanyourtv.root.updater com.cleanyourtv.system.updater; do
for cytv_kind in applications packages services; do
cytv_path="/media/developer/apps/usr/palm/$cytv_kind/$cytv_app"
if [ "$cytv_kind" = services ]; then cytv_path="$cytv_path.service"; fi
if [ -e "$cytv_path" ] || [ -L "$cytv_path" ]; then printf CYTV_RETAINED_ROOT; exit 0; fi
done
done
printf CYTV_FRESH_ROOT
'''
VENDOR_PROBE = '''unset NODE_OPTIONS NODE_PATH
export NODE_PATH=/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules
if test -r /usr/palm/services/jsservicelauncher/bootstrap-node.js &&
test -r /usr/palm/services/jsservicelauncher/bootstrap.js &&
/usr/bin/node -e 'var S=require("webos-service");require("palmbus");require("pmloglib");process.exit(typeof S === "function" ? 0 : 1)' >/dev/null 2>&1;
then printf CYTV_VENDOR_READY; else printf CYTV_VENDOR_UNAVAILABLE; fi
'''


def select_payload(payload, manifest):
    from . import package
    outer = manifest or package.verify_payload(payload)
    if outer.get('legacy_root_beta') != 'legacy-root-beta':
        raise UserError('Root Beta packages are missing or invalid. Use a complete installer build.')
    nested = payload/'legacy-root-beta'
    if nested.is_symlink():
        raise UserError('Root Beta packages are missing or invalid. Use a complete installer build.')
    selected = package.verify_payload(nested)
    if (selected.get('runtime_variant') != BETA or
            any(outer['files'].get('legacy-root-beta/'+name) != digest for name,digest in selected['files'].items())):
        raise UserError('Root Beta packages are missing or invalid. Use a complete installer build.')
    return nested, selected


def alternatives(value):
    if not isinstance(value, str) or not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        return ()
    if int(value[1:].split('.')[0]) >= 8:
        return ()
    return ('no-root', BETA) if value == 'v0.12.2' else ('no-root',)


def require_idle(store, profile, replacing=None):
    for saved in [profile, *store.profiles()]:
        pending = store.pending(saved)
        if replacing is not None and saved == profile and pending == replacing:
            continue
        if saved['host'] == profile['host'] and pending:
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')


def offer(installer, args, ask, write):
    """Only invoked after the ordinary Node requirement has actually failed."""
    require_idle(installer.store, installer.profile)
    value = installer.remote.run('/usr/bin/node --version', timeout=10).strip()
    options = alternatives(value)
    if not options:
        raise UserError('Root requirements failed or could not be verified: node-version. Check the diagnostic report.', reason_code='root-requirements')
    installer.tv_info['node_version'] = value[1:]
    installer.tv_info['node_version_status'] = 'read'
    if installer.remote.run(FRESH_PROBE, timeout=10).strip() != 'CYTV_FRESH_ROOT':
        from .root_no_root_handoff import probe
        try:installer._root_handoff=probe(installer)
        except (OSError,ValueError,RuntimeError):
            raise UserError('Previous Root installation needs recovery. Run cytv status or cytv restore. Reinstallation has not started; recovery data was left unchanged.') from None
    write.heading('Choose an alternative edition')
    from .i18n import translate
    write(translate('Ordinary Root requires Node.js 8+. Detected TV Node.js: {version}').format(version=value))
    write.option(1, NO_ROOT_TITLE, NO_ROOT_DETAIL)
    beta = BETA in options and installer.manifest.get('legacy_root_beta') == 'legacy-root-beta'
    if beta:
        write.option(2, BETA_TITLE, NOTICE)
    write.option(0, 'Cancel')
    if args.non_interactive:
        raise UserError('Choose an alternative edition interactively; --yes does not select Root Beta.', reason_code='root-requirements')
    choice = prompts.number(ask, write, 'Alternative edition [0]: ', 0, 2 if beta else 1, default=0)
    if choice == 0:
        raise EOFError
    require_idle(installer.store, installer.profile)
    previous = dict(installer.profile)
    if choice == 1:
        selected = state.target(previous['host'], 'no-root', previous['port'], previous.get('identity'), connection='root-ssh')
        # Preserve the already authenticated exact host key and SSAP connection.
        source = installer.store.device_dir(previous)
        target = installer.store.device_dir(selected)
        for name in ('known_hosts',):
            if (target/name).exists() and (source/name).is_file() and (target/name).read_bytes() != (source/name).read_bytes():
                raise UserError('SSH host key was not verified. Connection cancelled.', reason_code='ssh-identity-unverified')
            if (source/name).is_file() and not (target/name).exists():
                state.private_write(target/name, (source/name).read_bytes())
    else:
        write(NOTICE)
        if not prompts.confirm('Install experimental Root Beta?', ask, write):
            raise EOFError
        selected = state.target(**dict(previous, root_variant=BETA))
    installer.profile.clear()
    installer.profile.update(selected)
    installer.store.save(installer.profile)
    installer.use_runtime_variant()
    installer.checks.results.clear()
    write.selected_profile(selected)
    installer.checks.prepare(selected['edition'], 'install')
    installer.checks.update('ssh', 'pass')
    return selected

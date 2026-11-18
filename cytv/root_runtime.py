"""Explicit legacy choices before any installation submission."""
import hashlib
import json
import re
from pathlib import Path
from typing import NamedTuple

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


class SavedOperationReview(NamedTuple):
    profile: dict
    directory: Path
    evidence: dict


def _blocking_operations(store, profile, replacing=None):
    blocked = {}
    for saved in [profile, *store.profiles(require_operation_profiles=True)]:
        if saved['host'] != profile['host']:
            continue
        pending = store.pending(saved)
        if pending and not (replacing is not None and saved == profile and pending == replacing):
            blocked[store.device_path(saved)] = saved, pending
    return blocked


def require_idle(store, profile, replacing=None):
    store.reconcile_removed_profiles(profile)
    if _blocking_operations(store, profile, replacing):
        raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.',
                        reason_code='pending-operation')


def saved_operation_for_review(store, selected):
    """An address only locates candidates; the original connection owns review."""
    blocked = _blocking_operations(store, selected)
    if len(blocked) > 1:
        raise UserError('More than one saved TV connection at this address has an unfinished operation. '
                        'Choose Review recovery options for the same saved TV connection. Recovery data was kept.',
                        reason_code='pending-operation')
    if not blocked:
        return None
    directory, (candidate, pending) = next(iter(blocked.items()))
    if candidate['edition'] == selected['edition']:
        return None

    from .ssh_identity_review import original_evidence
    try:
        if directory.is_symlink() or pending['action'] == 'unknown':
            raise ValueError('Unverified recovery records')
        evidence = original_evidence(directory)
        if json.loads(evidence['operation.json']) != pending:
            raise ValueError('Recovery record changed')
        pin = hashlib.sha256(evidence['known_hosts']).hexdigest()
        original, recovered = store.connection_profile(candidate, expected_pin=pin)
        if not recovered or original != candidate or store.device_path(original) != directory:
            raise ValueError('Recovery connection changed')
    except (OSError, ValueError):
        raise UserError('The original saved TV connection and host key are required for recovery. Recovery data was kept.',
                        reason_code='ssh-identity-unverified') from None
    return SavedOperationReview(original, directory, evidence)


def offer(installer, args, ask, write, *, home_error=None):
    """Offer a compatible edition before submitting any installation."""
    require_idle(installer.store, installer.profile)
    if args.non_interactive:
        if home_error is not None:
            raise home_error
        raise UserError('Choose an alternative edition interactively; --yes does not select Root Beta.', reason_code='root-requirements')
    previous = dict(installer.profile)
    no_root = state.target(previous['host'], 'no-root', previous['port'], previous.get('identity'), connection='root-ssh')
    beta = False
    node_error = 'Root requirements failed or could not be verified: node-version. Check the diagnostic report.'
    if home_error is None:
        value = installer.remote.run('/usr/bin/node --version', timeout=10).strip()
        options = alternatives(value)
        if not options:
            raise UserError(node_error, reason_code='root-requirements')
        installer.tv_info['node_version'] = value[1:]
        installer.tv_info['node_version_status'] = 'read'
        beta = BETA in options and installer.manifest.get('legacy_root_beta') == 'legacy-root-beta'
    from .operations import Installer
    payload, manifest = installer._ordinary_payload or (installer.payload, installer.manifest)
    candidate = Installer(installer.remote, installer.store, no_root, payload, manifest,
                          progress=lambda _: None)
    no_root_verified = False
    try:
        candidate.check_no_root_alternative()
    except UserError as error:
        if home_error is not None:
            write(str(error))
            raise home_error from error
        root_clear = candidate.checks.results.get('root-conflict', {}).get('status') == 'pass'
        if not beta or not root_clear or error.reason_code == 'pending-operation':
            raise
        write(str(error))
    except (OSError, RuntimeError, ValueError, KeyError, TypeError):
        raise (home_error or UserError(node_error, reason_code='root-requirements')) from None
    else:
        no_root_verified = True
    write.heading('Choose an alternative edition')
    from .i18n import translate
    if home_error is None:
        write(translate('Ordinary Root requires Node.js 8+. Detected TV Node.js: {version}').format(version=value))
    else:
        from .failure_help import for_error
        guidance = for_error(home_error, 'inspect-installation', previous)
        write(guidance['title'])
        write(guidance['detail'])
    if no_root_verified:
        write.option(1, NO_ROOT_TITLE, NO_ROOT_DETAIL)
    if beta:
        write.option(2 if no_root_verified else 1, BETA_TITLE, NOTICE)
    write.option(0, 'Cancel')
    choice = prompts.number(ask, write, 'Alternative edition [0]: ', 0, int(no_root_verified) + int(beta), default=0)
    if choice == 0:
        raise EOFError
    require_idle(installer.store, installer.profile)
    if no_root_verified and choice == 1:
        selected = no_root
        installer.store.check_capsule_storage(selected)
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
    if hasattr(installer, '_graphics_paths'):
        del installer._graphics_paths
    installer.use_runtime_variant()
    installer.checks.results.clear()
    write.selected_profile(selected)
    installer.checks.prepare(selected['edition'], 'install')
    installer.checks.update('ssh', 'pass')
    return selected

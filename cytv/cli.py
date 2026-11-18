"""Numbered terminal wizard and small maintenance command surface."""
import argparse
from contextlib import nullcontext
import functools
import getpass
import hashlib
import inspect as signature_inspect
import io
import json
from pathlib import Path
import sys
from time import sleep
from types import SimpleNamespace

from . import __version__, package, state, i18n
from .errors import ExistingRoot, LocalRecoveryError, TVConnectionError, TVNotReady, UserError, is_storage_full
from .desktop import EXPLICIT_TV_CHOICE, RETRY_STORAGE_PROMPT
from .operations import Installer, require_root_reinstall_cleanup
from .terminal import Console, supports_ansi
from . import diagnostics, discovery, inspect_tv, prompts, install_settings, debloat


def payload_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'payload'
    return Path(__file__).resolve().parents[1] / 'build/cytv/payload'


class LanguageParser(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace('usage:', i18n.translate('usage:'))

    def format_help(self):
        return super().format_help().replace('usage:', i18n.translate('usage:'))

    def error(self, message):
        self.print_usage(sys.stderr)
        if message.startswith('argument ') and ': ' in message:
            argument, detail = message[9:].split(': ', 1)
            message = argument + ': ' + i18n.translate(detail)
        else:
            message = i18n.translate(message)
        Console(lambda text: self._print_message(text + '\n', sys.stderr),
                interactive=supports_ansi(sys.stderr)).error(self.prog + ': ' + i18n.translate('error:') + ' ' + message)
        self.exit(2)


def home_screen_name_arg(value):
    if not value.strip():
        raise argparse.ArgumentTypeError(i18n.translate('Enter a Home screen name, or omit --tv-name.'))
    return package.normalize_tv_name(value)


def parser(desktop=False):
    result = LanguageParser(prog='cytv', add_help=False, description=i18n.translate('Clean Your TV — one installer for No-root and Root.'))
    result._positionals.title = i18n.translate('positional arguments')
    result._optionals.title = i18n.translate('options')
    result.add_argument('-h', '--help', action='help', help=i18n.translate('Show this help message and exit'))
    commands = ('install', 'status', 'doctor', 'home-diagnostics', 'recover', 'trust-root-ssh', 'restore', 'uninstall', 'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access', 'recover-system-rollback', 'recover-root-rollback', 'replace-system-updater', 'clean-wam-cache', 'debloat')
    if desktop:
        commands += ('ssh-command',)
        result.add_argument('--resume-root-reinstall', action='store_true', help=argparse.SUPPRESS)
        result.add_argument('--removal-operation', help=argparse.SUPPRESS)
        result.add_argument('--removal-pin', help=argparse.SUPPRESS)
    result.add_argument('command', nargs='?', default='install', choices=commands)
    result.add_argument('--language', choices=tuple(i18n.LANGUAGES), help=i18n.translate('Interface language (auto uses the computer language)'))
    result.add_argument('--version', action='store_true', help=i18n.translate('Print installer version'))
    result.add_argument('--host', help=i18n.translate('TV IPv4 address or hostname'))
    result.add_argument('--no-discovery', action='store_true', help=i18n.translate('Skip local network discovery and enter a TV address manually'))
    result.add_argument('--edition', choices=('no-root', 'root'))
    result.add_argument('--tv-name', type=home_screen_name_arg, help=i18n.translate('Home screen name (Root Edition only)'))
    result.add_argument('--connection', choices=('root-ssh',), help=i18n.translate('No-root: use existing root SSH without Developer Mode'))
    result.add_argument('--root-variant', choices=('node012-beta',), help=i18n.translate('Root: select the experimental Node.js 0.12.2 payload'))
    result.add_argument('--port', type=int, help=i18n.translate('SSH port (No-root: 9922; Root: 22)'))
    result.add_argument('--identity', type=Path, help=i18n.translate('Existing Root SSH private key'))
    result.add_argument('--data-dir', type=Path, help=i18n.translate('Private local profile directory'))
    result.add_argument('--non-interactive', action='store_true', help=i18n.translate('Never prompt; needs a saved, trusted connection'))
    result.add_argument('--use-bundled-version', action='store_true', help=i18n.translate('Non-interactive install: explicitly use this installer even if a newer version is available'))
    result.add_argument('--yes', action='store_true', help=i18n.translate('Accept install/remove summary; does not accept SSH trust'))
    result.add_argument('--migrate-home', action='store_true', help=i18n.translate('Root install: explicitly import existing Home packaged/profile data'))
    result.add_argument('--check-payload', action='store_true', help=i18n.translate('Verify embedded release assets without contacting a TV'))
    result.add_argument('--prepare-python-runtime', action='store_true', help=i18n.translate('Download and verify the optional TV Python for offline setup'))
    result.add_argument('--new-recovery-attempt', action='store_true', help=i18n.translate('recover-system-rollback: explicitly start a new audited attempt after the old deadline'))
    result.add_argument('--repair-package-permissions', action='store_true', help=i18n.translate('enable-firmware-access: explicitly repair verified Root package permissions'))
    result.add_argument('--reconnect-after-reset', action='store_true',
                        help=i18n.translate('Install No-root using a new connection after a factory reset'))
    result.add_argument('--report', action='store_true', help=i18n.translate('doctor: save an issue-ready diagnostic report without private connection data'))
    return result


def explain_failure(write, store, profile, phase, error, *, offer_actions=True):
    from .failure_help import for_error

    def has_reset_source():
        from .no_root_reconnect import original_pins
        try:
            original_pins(store, profile)
        except UserError:
            return False
        return True

    pending = store.diagnostic_pending if hasattr(store, 'diagnostic_pending') else store.pending(profile) if profile else None
    if profile and phase in ('status', 'doctor', 'recover'):
        from .recovery import no_root_package_check_plan
        if no_root_package_check_plan(write, profile, pending, error=error):
            return None
    help = for_error(error, phase, profile, pending, has_reset_source=has_reset_source)
    if help:
        write.failure_help(help)
        if help['code'] == 'ssh-identity' and profile and profile['edition'] == 'root' and (pending or {}).get('action') == 'uninstall':
            write.raw('https://github.com/Razdva122/clean-your-tv-lg-webos/blob/release/next/docs/RECOVERY.md#ssh-identity-changed')
        if offer_actions and help['code'] in ('removal-not-submitted','no-root-recovery'):
            write.recovery(profile)
        if offer_actions and phase != 'recover' and pending and pending.get('action') in ('install', 'activate-root'):
            from .recovery import offer_install_recovery
            offer_install_recovery(write, store, profile)
    return help


def removal_connection_message(store, profile, phase, error):
    from .failure_help import removal_failure, transient_connection_failure
    pending = store.pending(profile) if profile else None
    if not pending or pending.get('recovery_protocol') != 'clean-removal-v1':
        return None
    if not transient_connection_failure(removal_failure(error, phase, profile, pending)):
        return None
    store.checkpoint(profile,removal_reason='connection-interrupted')
    return 'Connection to the TV was interrupted. Check the connection and try again.'


def _connect_via(callback, profile, directory, secret, trust, *, persist):
    """Use the optional persistence flag while preserving four-argument embedders."""
    options = {}
    if not persist:
        try:
            signature_inspect.signature(callback).bind(profile, directory, secret, trust, persist=False)
            options['persist'] = False
        except (TypeError, ValueError):
            pass
    return callback(profile, directory, secret, trust, **options)


def storage_preflight_review(store, profile, ask, write):
    """Keep retry on the authenticated SSH session and the exact saved profile."""
    directory = store.device_path(profile)
    known = directory / 'known_hosts'
    try:
        pin = hashlib.sha256(known.read_bytes()).hexdigest() if not known.is_symlink() else None
    except OSError:
        pin = None

    def guard():
        from .root_runtime import require_idle
        try:
            require_idle(store, profile)
        except UserError:
            pending = store.pending(profile)
            if pending and pending.get('action') not in ('install', 'activate-root') and pending.get(
                    'recovery_protocol') != 'clean-removal-v1':
                from .recovery import plan, REVIEW
                write.recovery(profile)
                plan(write, 'review', REVIEW)
            raise
        if pin is None or store.device_path(profile) != directory:
            raise UserError('SSH host key was not verified. Connection cancelled.',
                            reason_code='ssh-identity-unverified')
        original, _ = store.connection_profile(profile, expected_pin=pin)
        if original != profile:
            raise UserError('SSH host key was not verified. Connection cancelled.',
                            reason_code='ssh-identity-unverified')

    def review(error):
        guard()
        if error is None:
            write('The read-only storage check passed. Confirm installation to continue.')
            question = 'Install these versions?'
        else:
            from .failure_help import for_error
            write(str(error))
            help = for_error(error, 'install-packages', profile)
            if help and help['code'] == 'tv-storage-unavailable':
                write(help['next_step'])
            write('Repeat the read-only check on the same TV.')
            question = RETRY_STORAGE_PROMPT
        if not prompts.confirm(question, ask, write):
            raise EOFError
        guard()

    return review


def choose_profile(args, store, ask, write, search, inspect):
    observing = args.command in ('status', 'doctor')
    profile_errors = {}

    def record_profile_error(error):
        profile_errors.setdefault(error.local_recovery['reason'], error)

    host = args.host.strip().lower() if args.host else None
    exact = observing and host and args.port is not None and (args.edition == 'root' or args.connection)
    selector = None
    if exact:
        try:
            selector = state.target(host, args.edition, args.port, connection=args.connection)
        except ValueError:
            # The ordinary picker owns its existing validation on a complete list.
            pass
    if selector:
        exact_directory = store.device_path(selector)
        exact_profile = store.saved_profile(selector)
    saved = store.profiles(on_profile_error=record_profile_error if observing else None,
                           already_read=(exact_directory, exact_profile) if selector and exact_profile else None)
    profiles = [p for p in saved if not args.edition or p['edition'] == args.edition]
    profile = None
    if profile_errors:
        # Omitted connection is a wildcard for No-root, which can also use
        # Root SSH on the same port. Only a complete selector can skip review.
        if selector:
            profile = next((p for p in profiles if store.device_path(p) == exact_directory), exact_profile)
            if profile and args.root_variant and profile.get('root_variant') != args.root_variant:
                profile = None
            if profile:
                for error in profile_errors.values():
                    write(str(error))
        elif exact:
            raise UserError('Invalid TV address or port. Use an IPv4 address or hostname and a port from 1 to 65535.') from None
        elif not args.non_interactive:
            choices = [p for p in profiles if (not host or p['host'] == host)
                       and (args.port is None or p['port'] == args.port)
                       and (args.connection is None or p.get('connection') == args.connection)
                       and (args.root_variant is None or p.get('root_variant') == args.root_variant)]
            if choices:
                write.step(1, 'Choose a saved TV')
                for error in profile_errors.values():
                    write(str(error))
                for index, saved_profile in enumerate(choices, 1):
                    kind = ('Root (SSH)' if saved_profile['edition'] == 'root' else
                            'No-root (Root SSH)' if saved_profile.get('connection') == 'root-ssh' else
                            'No-root (Developer Mode)')
                    write.option(index, f"{saved_profile['host']}:{saved_profile['port']}", i18n.translate(kind))
                selected = prompts.number(ask, write, EXPLICIT_TV_CHOICE, 1, len(choices))
                profile = choices[selected - 1]
        if profile is None:
            raise next(iter(profile_errors.values()))
        if args.identity:
            profile = dict(profile, identity=str(args.identity.expanduser().resolve()))
        return profile, True
    if not args.host:
        if len(profiles) == 1 and (args.command != 'install' or args.non_interactive):
            profile = dict(profiles[0])
            write('Using saved ' + profile['edition'] + ' TV connection.')
        elif profiles:
            write.step(1, 'Choose a saved TV')
            for index, p in enumerate(profiles, 1):
                write.option(index, p['host'], 'Root' if p['edition'] == 'root' else 'No-root')
            write.option(0, 'Add another TV')
            selected = prompts.number(ask, write, 'TV number [1]: ', 0, len(profiles), default=1)
            profile = dict(profiles[selected - 1]) if selected else None
    if profile is None:
        host = args.host or prompts.tv_address(ask, write, search=None if args.no_discovery or args.non_interactive else search)
        edition = args.edition
        if edition is None:
            try:
                state.target(host, 'no-root', args.port)
            except ValueError:
                raise UserError('Invalid TV address or port. Use an IPv4 address or hostname and a port from 1 to 65535.') from None
            info = {}
            if not args.non_interactive:
                write('')
                write('Checking TV connections…')
                info = inspect(host, args.port)
            default_choice = 2 if info.get('root_ssh') else 1
            write.step(2, 'Choose your edition' if args.command == 'install' else 'Choose how you normally connect to this TV.')
            write('TV: ' + host)
            write.heading('Connection check')
            if info.get('root_ssh'):
                write(f"Root SSH detected on port {info.get('root_port', 22)}.")
                write('Root privileges will be verified after sign-in.')
            else:
                write('Root access not confirmed. SSH may be disabled or use another port.')
            if info.get('developer_ssh'):
                write('Developer Mode SSH detected.')
            write.option(1, 'No-root',
                         'For a TV without root. Uses LG Developer Mode.')
            write.option(2, 'Root',
                         'For an already rooted TV with existing SSH access.')
            write('')
            if args.command == 'install':
                write("No-root uses LG's Developer Mode app. Root requires administrator access already set up on the TV.")
                write('This installer does not obtain root.')
            write('Enter = current choice   |   q = quit')
            choice = prompts.number(ask, write, f'Edition [{default_choice}]: ', 1, 2, default=default_choice)
            edition = 'no-root' if choice == 1 else 'root'
        try:
            profile = state.target(host, edition, args.port, args.identity, args.connection, args.root_variant)
        except ValueError:
            raise UserError('Invalid TV address or port. Use an IPv4 address or hostname and a port from 1 to 65535.') from None
        # Match saved credentials, including the identity, when targeting a known TV explicitly.
        matches = [saved for saved in profiles if saved['host'] == host and saved['edition'] == edition
                   and (args.port is None or saved['port'] == profile['port'])
                   and (args.connection is None or saved.get('connection') == args.connection)
                   and (args.root_variant is None or saved.get('root_variant') == args.root_variant)]
        if len(matches) == 1:
            profile = dict(matches[0])
    if args.port is not None:
        profile['port'] = args.port
    if args.identity:
        profile['identity'] = str(args.identity.expanduser().resolve())
    if args.connection:
        profile['connection'] = args.connection
    if args.root_variant:
        profile['root_variant'] = args.root_variant
    return state.target(**profile), False


def main(argv=None, ask=input, write=print, connect=None, secret=getpass.getpass, search=None, inspect=None, payload_root=None, check_updates=False):
    # Preserve the terminal/file encoding; escape unsupported text instead of
    # aborting setup or even --help on redirected legacy Windows streams.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors='backslashreplace')
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if raw_args == ['--check-runtime']:
        from .runtime_check import check_runtime
        check_runtime()
        (write if isinstance(write, Console) else Console(write)).raw('Installer runtime verified; no TV contacted.')
        return 0
    requested = next((arg.split('=', 1)[1] for arg in raw_args if arg.startswith('--language=')), None)
    if '--language' in raw_args and raw_args.index('--language') + 1 < len(raw_args):
        requested = raw_args[raw_args.index('--language') + 1]
    if requested in i18n.LANGUAGES:
        i18n.set_language(requested)
    language_parser = LanguageParser(prog='cytv', add_help=False)
    language_parser.add_argument('--language', choices=tuple(i18n.LANGUAGES))
    language_parser.add_argument('--data-dir', type=Path)
    language_args, _ = language_parser.parse_known_args(argv)
    try:
        i18n.configure(language_args.language, language_args.data_dir)
    except OSError as error:
        from .failure_help import for_error
        i18n.set_language(language_args.language or 'auto')
        write = write if isinstance(write, Console) else Console(write)
        write.error('Could not save language preference', heading=True)
        local_error = LocalRecoveryError('storage-unavailable', 'ancestor', storage_full=is_storage_full(error),
                                         write_precheck=True)
        write.failure_help(for_error(local_error, 'select-tv'))
        return 2
    from .desktop import DesktopConsole, SSH_COMMAND_PROMPT
    args = parser(desktop=isinstance(write, DesktopConsole)).parse_args(argv)
    if args.version:
        write('cytv ' + __version__)
        return 0
    write = write if isinstance(write, Console) else Console(write, interactive=False if args.non_interactive else None)
    from .checks import CheckList
    checks = CheckList(write.check)
    ask = write.reader(ask)
    remote = None
    store, profile, phase, tv_info = state.Store(args.data_dir), None, 'select-tv', {'frontend':getattr(write,'frontend','console')}
    partial = False
    saved_review = None
    if args.command == 'trust-root-ssh':
        from .ssh_identity_review import run
        return run(args, store, ask, write)
    try:
        removal_operation = getattr(args, 'removal_operation', None)
        removal_pin = getattr(args, 'removal_pin', None)
        if removal_pin is not None and (removal_operation is None or args.command != 'uninstall'):
            raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
        if removal_operation is not None and (args.command not in ('restore', 'uninstall')
                or not args.host or not args.edition or args.port is None or args.non_interactive):
            raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
        if args.reconnect_after_reset and (
                args.command != 'install' or args.edition != 'no-root' or not args.host
                or args.connection or args.identity or args.non_interactive or args.yes):
            raise UserError('Start a new No-root connection interactively with the saved TV address.')
        if args.tv_name is not None and args.command != 'install':
            raise UserError('--tv-name applies only to installation.')
        if args.new_recovery_attempt and (args.command != 'recover-system-rollback' or args.edition == 'no-root'):
            raise UserError('--new-recovery-attempt applies only to Root rollback recovery.')
        if args.repair_package_permissions and (args.command!='enable-firmware-access' or args.edition=='no-root'):
            raise UserError('--repair-package-permissions applies only to Root enable-firmware-access.')
        if args.prepare_python_runtime:
            phase = 'prepare-python-runtime'
            from .python_runtime import prime_cache
            archive = prime_cache(store.root / 'python-cache', write)
            write.heading('Python runtime ready for offline setup')
            write.raw('  ' + str(archive))
            return 0
        if args.check_payload:
            manifest = package.verify_payload(Path(payload_root) if payload_root is not None else payload_dir())
            write(f"Embedded payload verified: {len(manifest['files'])} public files; no TV contacted.")
            return 0
        if args.migrate_home and (args.command != 'install' or args.edition == 'no-root'):
            raise UserError('--migrate-home applies only to Root installation.')
        if args.report and args.command != 'doctor':
            raise UserError('--report is available with cytv doctor.')
        if args.command == 'clean-wam-cache' and args.non_interactive:
            raise UserError('WAM cleanup requires interactive confirmation; --yes does not authorize it.')
        if args.command == 'debloat' and args.non_interactive:
            raise UserError('Debloat requires interactive selection of the settings to change.')
        if args.non_interactive:
            def no_ask(_):
                raise UserError('Non-interactive mode needs --host and --edition or one saved profile; pairing and SSH trust must already be completed.')
            ask = no_ask
            secret = no_ask
        packaged_desktop_setup = (args.command == 'install' and isinstance(write, DesktopConsole)
                                  and getattr(sys, 'frozen', False))
        if packaged_desktop_setup:
            phase = 'prepare-payload'
            try:
                package.check_payload_files(Path(payload_root) if payload_root is not None else payload_dir())
            except (OSError, ValueError):
                write('Installation has not started.')
                raise UserError('Use a complete installer build.') from None
            phase = 'select-tv'
        if args.command == 'install' and not args.non_interactive:
            write.heading('Clean Your TV  /  Installation')
            write('TV > Edition > Connection > Install > Settings')
            write('q / Ctrl+C = quit. Password entry uses Ctrl+C.')
        def inspect_connection(host, port):
            nonlocal phase
            phase = 'inspect-tv'
            info = (inspect or inspect_tv.inspect)(host, port)
            phase = 'select-edition'
            return info

        profile, partial = choose_profile(args, store, ask, write, search or discovery.find_tvs, inspect_connection)
        if partial:
            tv_info['partial_profile_observation'] = True
            # Root status can stage support code and ordinary status may
            # reconcile receipts. Partial selection only admits SSH metadata.
        if args.tv_name is not None and profile['edition'] != 'root':
            raise UserError('--tv-name requires Root Edition.')
        desktop_install = isinstance(write, DesktopConsole) and args.command == 'install' and not args.non_interactive
        reinstall_step = store.root_reinstall(profile) if desktop_install else None
        if reinstall_step:
            profile = state.target(**dict(profile, root_variant=reinstall_step.variant))
        if getattr(args, 'resume_root_reinstall', False) and not reinstall_step:
            raise UserError('There is no saved Root reinstallation to continue.')
        if args.command == 'install' and not args.reconnect_after_reset:
            from .root_runtime import saved_operation_for_review
            phase = 'review-saved-operation'
            saved_review = saved_operation_for_review(store, profile)
            if saved_review:
                guidance = 'An earlier operation is unresolved. Choose Review recovery options or run cytv recover with the original TV connection.'
                if args.non_interactive:
                    raise UserError(guidance, reason_code='pending-operation')
                selected = profile
                original = saved_review.profile
                write(guidance)
                write('TV: ' + original['host'])
                kind = ('Root (SSH)' if original['edition'] == 'root' else
                        'No-root (Root SSH)' if original.get('connection') == 'root-ssh' else
                        'No-root (Developer Mode)')
                write(i18n.translate('Edition: {edition}').format(edition=i18n.translate(kind)))
                write(i18n.translate('SSH port: {port}').format(port=original['port']))
                write('Checking recovery does not reinstall or remove packages. Root checks may run verified support code.')
                from .recovery import SAVED_CONNECTION_PROMPT
                if not prompts.confirm(SAVED_CONNECTION_PROMPT, ask, write):
                    return 130
                profile = original
                args.command = 'recover'
                desktop_install = False
                reinstall_step = None
        write.selected_profile(profile)
        if reinstall_step:
            write.root_reinstall()
            if not getattr(args, 'resume_root_reinstall', False) and not prompts.confirm('Continue Root reinstallation?', ask, write):
                return 130
        setup = {}
        if args.command == 'replace-system-updater':
            if profile['edition'] != 'root': raise UserError('System Updater replacement requires an existing Root connection.')
            if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        if args.command in ('recover-system-rollback', 'recover-root-rollback'):
            if profile['edition'] != 'root': raise UserError('Rollback readiness recovery requires an existing Root connection.')
            if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        if args.command in ('enable-firmware-access','disable-firmware-access'):
            if profile['edition']!='root':raise UserError('Homebrew API access requires an existing Root installation.')
            if store.pending(profile):raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        if args.command == 'clean-wam-cache':
            if profile['edition'] != 'root':
                raise UserError('WAM cleanup requires an existing Root SSH connection.')
            if store.pending(profile):
                raise UserError('Resolve the pending installation or removal before clearing WAM data. Keep recovery records.')
        if check_updates and args.command == 'install' and not reinstall_step and not store.pending(profile):
            from .installer_update import offer
            if not offer(ask, write, args.non_interactive, args.use_bundled_version):
                return 0
        if args.command == 'install' and not reinstall_step:
            phase = 'prepare-payload'
            write.step(3, 'Prepare the TV connection')
            if profile['edition'] == 'root':
                write('Root requires existing root and SSH access.')
            elif profile.get('connection') != 'root-ssh' and not args.reconnect_after_reset:
                write('Developer Mode lets CYTV install apps on a TV without root.')
                write('Home is your app screen. Home Helper makes the Home button open it.')
                write.heading('1. Developer Mode')
                write('On the TV, open LG Apps, search for Developer Mode and install it.')
                write('Open Developer Mode and sign in with your LG Developer account. Create an account at webostv.developer.lge.com if needed.')
                write.heading('2. Dev Mode Status')
                write('Turn on Dev Mode Status. The TV restarts. Open Developer Mode again.')
                write.heading('3. Key Server')
                write('Turn on Key Server and leave Developer Mode open. Its IP Address is the TV address to enter in CYTV.')
                write('Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.')
            write.step(4, 'Review and install', clear=profile['edition'] == 'root')
            write('TV: ' + profile['host'])
            write('Edition: ' + ('Root Beta (Node.js 0.12.2)' if profile.get('root_variant') else
                                'Root' if profile['edition'] == 'root' else 'No-root'))
            write('SSH port: ' + str(profile['port']))
            if profile['edition'] == 'root':
                write('Automatic SSH sign-in first; credentials only if needed.')
            write('Next: verify SSH, read your apps, then install.')
            if profile['edition']=='no-root':
                write('Pairing is a separate step: when the TV asks, approve CYTV with your remote.')
            if profile['edition'] == 'root':
                write('Root will stop the old Home Helper, turn on Home control and open Clean Your TV Home.')
            write('Check controls on the TV after installation.')
        retry_removal = args.command == 'uninstall' and (removal_operation is not None or
            (store.pending(profile) or {}).get('recovery_protocol') == 'clean-removal-v1')
        if args.command in ('install', 'uninstall', 'restore', 'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access', 'recover-system-rollback', 'recover-root-rollback', 'replace-system-updater') and not (args.yes or retry_removal or args.reconnect_after_reset or reinstall_step):
            if args.command == 'uninstall':
                write('LG Home will be restored. Clean Your TV, its updaters, Home Helper and saved preferences will be removed.')
            if args.command == 'uninstall' and profile['edition'] == 'root':
                write('This removes Root, Root Updater, their services and startup hooks, plus any installed No-root Home, Helper and Updater.')
                write('Recovery records are retained for diagnostics. Other TV apps stay installed.')
            verb = {'install': 'Connect to check installed versions', 'uninstall': 'Restore LG Home and remove this edition', 'restore': 'Restore LG Home', 'enable-system-updates': 'Prepare updates for all system components on this rooted TV','enable-firmware-access':'Change Root Home access to Homebrew configuration','disable-firmware-access':'Change Root Home access to Homebrew configuration','recover-system-rollback':'Recover verified Root rollback readiness','recover-root-rollback':'Recover verified Root rollback readiness','replace-system-updater':'Replace only the System Updater and preserve Root settings'}[args.command]
            if args.command == 'uninstall' and profile['edition'] == 'root':
                pending = store.pending(profile)
                if pending and pending.get('action') == 'uninstall' and pending.get('full_project') is True:
                    verb = 'Check TV and continue removal'
            if args.new_recovery_attempt:
                write('Start a new audited attempt after the previous deadline')
            if not prompts.confirm(verb + '?', ask, write, default=args.command == 'install'):
                write('Cancelled. No TV changes were made.')
                return 130 if desktop_install else 0
        # Canonicalize the selected local build root (macOS /var is an OS
        # alias); authenticated support members still reject indirect children.
        payload, manifest = (Path(payload_root) if payload_root is not None else payload_dir()).resolve(), {}
        root_doctor = not partial and args.command == 'doctor' and profile['edition'] == 'root' and not store.pending(profile)
        # Source-only doctor can still check basic TV requirements without a built payload.
        check_doctor_payload = root_doctor and (
            payload_root is not None or getattr(sys, 'frozen', False) or (payload / 'payload.json').exists()
        )
        if not partial and (check_doctor_payload or (profile.get('root_variant') and args.command not in ('ssh-command', 'debloat')) or args.command in (
                'install', 'enable-system-updates', 'enable-firmware-access',
                'disable-firmware-access', 'replace-system-updater')):
            if root_doctor:
                phase = 'prepare-payload'
            try:
                manifest = package.verify_payload(payload)
            except (OSError, ValueError) as error:
                if packaged_desktop_setup and args.command == 'install':
                    write('Installation has not started.')
                    raise UserError('Use a complete installer build.') from None
                if isinstance(error, FileNotFoundError):
                    raise UserError('Release payload is missing. Download a built cytv executable or run python scripts/build-cytv.py --payload-only from source.') from None
                raise
            if args.migrate_home and profile['edition'] != 'root':
                raise UserError('--migrate-home applies only to Root installation.')
        reinstall_payload = (hashlib.sha256(json.dumps([profile.get('root_variant'), manifest], sort_keys=True).encode()).hexdigest()
                             if desktop_install and profile['edition'] == 'root' else None)

        def trust(value, root):
            if args.non_interactive:
                raise UserError('This TV is not remembered yet. Connect interactively once to confirm it on your trusted home network.')
            if not prompts.trust_tv(profile['host'], profile['port'], value, ask, write):
                raise EOFError
            return True

        def secret_with_help(prompt):
            if not args.non_interactive:
                if prompt.startswith('Developer Mode'):
                    write.heading('Developer Mode code (Passphrase)')
                    write('Enter Passphrase: the six characters shown in Developer Mode on the TV. Match uppercase and lowercase letters.')
                    write('Use the code from the TV, not your LG account password. If no code is visible, turn on Key Server.')
                elif prompt.startswith('SSH key'):
                    write.heading('SSH key passphrase')
                    write('Enter the passphrase that unlocks your private SSH key file.')
                else:
                    write.heading('Root SSH password (hidden):')
                    write('Enter your existing TV root SSH password. This was set when SSH access was configured.')
                write('Typing is hidden: no characters or dots appear.')
                write('Enter = submit   |   Ctrl+C = cancel')
            localized = write.prompt(prompt)
            if isinstance(prompt, CredentialPrompt):
                localized = CredentialPrompt(localized, prompt.credential_type)
            return secret(localized)

        from .transport import SSH, CredentialPrompt
        observe_while_busy = (args.command == 'status' and not partial and profile['edition'] == 'no-root'
                              and profile.get('connection') != 'root-ssh')
        lock_options = {'allow_observation': True} if observe_while_busy else {}
        with store.lock(profile, **lock_options) as writer, (
                nullcontext() if writer is False else diagnostics.context.operation_context(store, profile)):
            if writer is False:
                from .recovery import active_operation_plan, refresh_active_no_root
                connector = functools.partial(_connect_via, connect) if connect else SSH.connect
                try:
                    refresh_active_no_root(store, profile, payload, write, connector)
                except Exception as error:
                    if getattr(error, 'reason_code', None) == 'operation-active':
                        raise
                    write.error(str(error) if isinstance(error, UserError) else 'The TV package result could not be verified.')
                    active_operation_plan(write, profile)
                    return 2
                return 0
            if removal_operation is not None:
                from .recovery import confirmed_uninstall
                pending = store.pending(profile)
                if (confirmed_uninstall(pending) != removal_operation
                        or args.command == 'restore' and pending.get('stage') in ('restart-required', 'verified-clean')):
                    raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
            if desktop_install and store.root_reinstall(profile) != reinstall_step:
                raise UserError('The saved Root reinstallation changed. Return to the start screen and check again.')
            if reinstall_step and reinstall_step.payload != reinstall_payload:
                raise UserError('Continue Root reinstallation using the same installer build.')
            if args.command == 'debloat':
                from .root_runtime import require_idle
                phase = 'debloat'
                try:
                    require_idle(store, profile)
                except UserError:
                    raise UserError('An earlier operation is unresolved. Choose Review recovery options or run cytv recover with the original TV connection.',
                                    reason_code='pending-operation') from None
            recovering = False
            if args.command == 'install' and profile['edition'] == 'no-root' and not store.pending(profile):
                # Check again before staging as pairing can take time.
                store.check_capsule_storage(profile)
            if args.reconnect_after_reset:
                from .no_root_reconnect import original_pins, reconnect
                old_key_type, old_pins = original_pins(store, profile)
                write('Start a new No-root connection only after a factory reset. The old profile and its uninstall record will be kept.')
                write('Only continue for your own TV on your trusted home network.')
                if not prompts.confirm('Start a new No-root connection after a factory reset?', ask, write, default=False):
                    raise EOFError
            elif saved_review:
                recovering = True
            elif partial:
                directory = store.device_path(profile)
                state.require_original_ssh_identity(directory)
                if (directory / 'known_hosts').is_symlink():
                    raise UserError('The original saved TV connection and host key are required for recovery. Recovery data was kept.',
                                    reason_code='ssh-identity-unverified')
            else:
                profile, recovering = store.connection_profile(
                    profile, expected_pin=reinstall_step.pin if reinstall_step else removal_pin)
                if reinstall_step:
                    profile = state.target(**dict(profile, root_variant=reinstall_step.variant))
            # An explicit sign-in key may change; the saved TV identity and pin
            # must still be resolved and verified before using it.
            if (recovering and not saved_review and args.identity and (reinstall_step or args.command in ('uninstall', 'recover', 'restore')
                    and (profile['edition'] == 'root' or profile.get('connection') == 'root-ssh')
                    and (store.pending(profile) or {}).get('recovery_protocol') == 'clean-removal-v1')):
                profile = dict(profile, identity=str(args.identity.expanduser().resolve()))
            if args.command=='uninstall':
                if not recovering:store.save(profile)
                store.request_clean_removal(profile)
            from .recovery import removal_plan
            cleanup=not (partial or args.reconnect_after_reset) and (store.pending(profile) or {}).get('recovery_protocol')=='clean-removal-v1'
            observer_support = (not partial and profile.get('connection') == 'root-ssh'
                and (store.pending(profile) or {}).get('recovery_protocol') == 'no-root-original-stream-v1'
                and args.command in ('status', 'doctor', 'recover'))
            if args.command in ('uninstall','recover') and cleanup and not saved_review:
                removal_plan(write,store,profile,state='waiting',connecting=True)
            if (args.command in ('uninstall','recover') and cleanup) or observer_support:
                try:manifest=package.verify_payload(payload)
                except FileNotFoundError:
                    raise UserError('Release payload is missing. Download a built cytv executable or run python scripts/build-cytv.py --payload-only from source.') from None
            if args.command == 'replace-system-updater':
                if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
            if args.command in ('enable-firmware-access','disable-firmware-access','recover-system-rollback','recover-root-rollback') and store.pending(profile):raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
            if args.command == 'clean-wam-cache' and store.pending(profile):
                raise UserError('Resolve the pending installation or removal before clearing WAM data. Keep recovery records.')
            phase = 'ssh-connect'
            if not partial and args.command in ('install', 'doctor'):
                checks.prepare(profile['edition'], args.command)
            checks.update('ssh', 'running')
            write('Connecting to the TV…')
            def connect_tv(pinned, directory=None, confirm=trust):
                pairing = {'previous_host_key_type': old_key_type} if directory is not None else {}
                if directory is None:
                    if saved_review:
                        directory = saved_review.directory
                    else:
                        directory = store.device_path(profile) if partial else store.device_dir(profile)
                if connect:
                    return _connect_via(connect, profile, directory, secret_with_help,
                                        (lambda *_: False) if pinned else confirm, persist=not pinned)
                return SSH.connect(profile, directory, secret_with_help, confirm,
                                   identity_prompt=None if pinned or args.non_interactive else lambda: prompts.root_credentials(ask, write),
                                   persist=not pinned, **pairing)

            from .errors import connection_interrupted
            for attempt in range(3 if cleanup else 1):
                try:
                    if saved_review and saved_operation_for_review(store, selected) != saved_review:
                        raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.',
                                        reason_code='pending-operation')
                    if args.reconnect_after_reset:
                        remote = reconnect(store, profile, lambda directory, confirm: connect_tv(False, directory, confirm),
                                           trust, old_pins)
                    else:
                        remote = connect_tv(recovering or partial)
                    break
                except Exception as error:
                    if not cleanup or attempt == 2 or not connection_interrupted(error):
                        raise
                    write('Connecting to the TV…')
                    sleep(attempt + 1)
            checks.update('ssh', 'pass')
            if partial:
                diagnostics.context.collect_metadata(remote, tv_info)
                diagnostics.context.collect_node_version(remote, tv_info)
                write('SSH connection verified. Full TV checks and recovery details are unavailable.')
                write.raw(json.dumps(diagnostics.context.tv_summary(tv_info), indent=2))
                diagnostics.save_result(write, store, args.command, profile, 'partial-tv-observation',
                                        tv_info, checks=checks.results)
                return 0
            if args.command == 'ssh-command':
                phase = 'ssh-command'
                if not recovering and not store.pending(profile):
                    store.save(profile)
                write.selected_profile(profile)
                command = ask(SSH_COMMAND_PROMPT)
                if not command.strip():
                    return 130
                result = remote.run_command(command)
                write.ssh_command_result(result)
                return 0

            if not recovering and args.command in ('install', 'status', 'doctor', 'recover', 'debloat'):
                diagnostics.context.collect_metadata(remote, tv_info)
            if not recovering:
                store.save(profile)
                pending=store.pending(profile)
                if pending and pending.get('recovery_protocol')=='clean-removal-v1' and pending.get('connection_pending') is True:
                    store.checkpoint(profile,connection_pending=False)
            if args.command == 'debloat':
                phase = 'debloat'
                settings = SimpleNamespace(remote=remote, store=store, profile=profile, tv_info=tv_info)
                events = tv_info.setdefault('debloat', {})
                try:
                    debloat.run(settings, ask, write, diagnostic=events, maintenance=True)
                finally:
                    if events:
                        diagnostics.save_result(write, store, args.command, profile, phase, tv_info,
                                                checks=checks.results)
                return 0
            installer = Installer(remote, store, profile, payload, manifest, write, tv_info=tv_info, checks=checks)
            def reconnect_tv():
                nonlocal remote
                if remote is not None:
                    remote.close()
                    remote = None
                remote = connect_tv(True)
                return remote
            installer.reconnect = reconnect_tv
            if args.command == 'install':
                reinstall = None
                home_conflict = None
                home_pending = False
                resume = False
                pending = store.pending(profile)
                if reinstall_step and reinstall_step.stage in ('removing', 'verified'):
                    phase = 'remove-existing-root'
                    if reinstall_step.stage == 'verified':
                        # The device proof was saved before the host retired its active receipt.
                        store.finish_clean_removal(profile)
                    else:
                        write('Restoring LG Home and removing the previous Clean Your TV installation…')
                        require_root_reinstall_cleanup(installer.continue_clean_removal(pending))
                    reinstall_step = reinstall_step._replace(stage='removed')
                    if store.root_reinstall(profile) != reinstall_step:
                        raise UserError('The saved Root reinstallation changed. Return to the start screen and check again.')
                    pending = None
                continue_after_cleanup = bool(reinstall_step and reinstall_step.stage == 'removed')
                replacing_activation = (profile['edition'] == 'root' and pending
                    and pending.get('action') == 'activate-root'
                    and not reinstall_step
                    and pending.get('home_backend') != 'c1-native-gate')
                if pending and not replacing_activation:
                    from .recovery import recover
                    phase = args.command = 'recover'
                    recover(installer, ask, write, args.non_interactive)
                    diagnostics.save_result(write, store, 'recover', profile, phase, tv_info,
                                            checks=checks.results, status=tv_info.get('status'))
                    return 0
                from .root_runtime import require_idle, BETA, NOTICE
                require_idle(store, profile, replacing=pending if replacing_activation else None)
                if profile.get('root_variant') == BETA and not continue_after_cleanup:
                    write(NOTICE)
                    if args.non_interactive or not prompts.confirm('Install experimental Root Beta?', ask, write):
                        raise EOFError
                if continue_after_cleanup:
                    phase = 'inspect-installation'
                    write('Clean Your TV removal is verified.')
                    if not prompts.confirm('Continue Root installation?', ask, write):
                        return 130
                    installer.select_graphics()
                    try:
                        installer.preflight(install=True, home_interfaces=True)
                    except ExistingRoot:
                        raise UserError('A Root installation was found after removal. Check the TV status before continuing.') from None
                    installer.root_reinstall_payload = reinstall_payload
                elif profile['edition'] == 'root' and not resume:
                    installer.select_graphics()
                    phase = 'inspect-installation'
                    from .root_capabilities import NativeHomeScriptError, NoRootAlternativeError, RootCapabilityError
                    from .root_runtime import offer
                    try:
                        if replacing_activation:
                            reinstall = 'installed'
                        else:
                            try:
                                installer.preflight(install=True, home_interfaces=True)
                            except RootCapabilityError as error:
                                mount_conflict = tv_info.get('root_compositor_failure') in (
                                    'keyfilters-incompatible', 'native-home-incompatible',
                                )
                                if profile.get('root_variant') or not (mount_conflict or isinstance(error, NativeHomeScriptError)):
                                    raise
                                home_conflict = error
                            except UserError as error:
                                if (error.reason_code != 'root-requirements' or profile.get('root_variant')
                                        or tv_info.get('root_requirements', {}).get('node-version') != 'fail'):
                                    raise
                                if args.migrate_home:
                                    raise UserError('Choose an alternative edition without --migrate-home. Installation has not started.')
                                offer(installer, args, ask, write)
                                if profile['edition'] == 'root':
                                    installer.select_graphics()
                                    installer.preflight(install=True, home_interfaces=True)
                    except RootCapabilityError as error:
                        if not isinstance(error, NoRootAlternativeError):
                            raise
                        if args.migrate_home:
                            raise UserError('Choose an alternative edition without --migrate-home. Installation has not started.')
                        offer(installer, args, ask, write, home_error=error)
                    except ExistingRoot:
                        reinstall = 'installed'
                    if args.tv_name is not None and profile['edition'] == 'no-root':
                        write('--tv-name was skipped because the selected edition is No-root.')
                    if (not reinstall and profile['edition'] == 'root' and not profile.get('root_variant')
                            and installer.manifest.get('root_backends', {}).get('c1-native-gate')):
                        from .home_handoff import handoff_pending
                        home_pending = handoff_pending(remote)
                if reinstall:
                    if args.migrate_home:
                        raise UserError('For Root reinstallation, omit --migrate-home. The installer reads a fresh TV inventory before replacing Root.')
                    if args.non_interactive:
                        raise UserError('Root is already installed or recovery state remains. Run the installer interactively to confirm reinstallation. --yes does not approve replacing Root.')
                    write.heading('Versions on the TV → versions in this installer')
                    for row in installer.version_summary():
                        write(row)
                    write.heading('Reinstall Root using this installer')
                    write('LG Home will be restored. Clean Your TV, its updaters, Home Helper and saved preferences will be removed.')
                    write('After removal is verified, the packages and Root runtime in this installer will be installed and activated. Your other TV apps and existing root access stay in place.')
                    write('Earlier recovery records are kept on this computer. If removal cannot finish, the new installation will not start.')
                    if not prompts.confirm('Reinstall Root?', ask, write):
                        write('Existing Root and recovery data left unchanged.')
                        return 130 if desktop_install else 0
                    if reinstall_payload:
                        installer.root_reinstall_payload = reinstall_payload
                        write.root_reinstall()
                if not reinstall and not resume and not continue_after_cleanup:
                    phase = 'inspect-installation'
                    write.heading('Versions on the TV → versions in this installer')
                    for row in installer.version_summary():
                        write(row)
                    if not args.yes and not prompts.confirm('Install these versions?', ask, write, default=True):
                        write('Cancelled. No TV changes were made.')
                        return 130 if desktop_install else 0
                if home_conflict is not None or home_pending:
                    from .home_handoff import takeover
                    if not takeover(installer, pending=home_pending):
                        if home_pending:
                            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.',
                                            reason_code='root-operation-unconfirmed')
                        raise home_conflict
                    installer.preflight(install=True, home_interfaces=True)
                def helper_retry():
                    if args.non_interactive:
                        return False
                    write.heading('Stop Home Helper on the TV')
                    write('Press Home three times within two seconds (older Helper: hold Home for two seconds), then release all buttons and wait for LG Home.')
                    return prompts.confirm('Try stopping Helper again?', ask, write, default=True)

                def prepare_no_root(check):
                    auto_stop = True
                    while True:
                        try:
                            check(auto_stop)
                            return True
                        except UserError as error:
                            auto_stop = False
                            if error.reason_code != 'helper-running' or args.non_interactive:
                                raise
                            if not helper_retry():
                                return False

                def prepare_no_root_staging():
                    nonlocal phase
                    phase = 'inspect-installation'
                    if not prepare_no_root(installer.prepare_install_helper):
                        raise EOFError
                    phase = 'install-packages'

                installer.helper_retry = helper_retry
                if profile['edition'] == 'no-root':
                    phase = 'inspect-installation'
                    if not args.non_interactive and write.frontend in ('console', 'desktop', 'android'):
                        installer.storage_preflight_review = storage_preflight_review(store, profile, ask, write)
                    installer.before_no_root_staging = prepare_no_root_staging
                    installer.preflight(install=True, defer_helper=True)
                if not resume:
                    installer.select_graphics()
                phase = 'read-inventory'
                inventory, key = None, None
                if not args.migrate_home and not resume:
                    if profile['edition']=='root':
                        checks.update('inventory','running','')
                        inventory=installer.root_inventory((payload/'fallback.png').read_bytes())
                        if installer.tv_info.get('root_inventory',{}).get('inputs')=='unavailable':
                            checks.update('inventory','unknown','Warning: TV inputs could not be read. Continuing with applications only.')
                        else:
                            checks.update('inventory','pass')
                    else:
                        from .tv import SSAP
                        while True:
                            try:
                                phase = 'pair-tv'
                                checks.update('pairing', 'running', '')
                                with SSAP(profile['host'], store.device_dir(profile), write) as tv:
                                    checks.update('pairing', 'pass')
                                    phase = 'read-inventory'
                                    checks.update('inventory', 'running', '')
                                    try:
                                        inventory = tv.inventory(
                                            (payload / 'fallback.png').read_bytes(),
                                            allow_missing_inputs=installer.may_omit_no_root_inputs,
                                        )
                                    finally:
                                        icon_counts = getattr(tv, 'icon_diagnostics', None)
                                        if type(icon_counts) is dict:
                                            tv_info['icon_inventory'] = icon_counts
                                    key = tv.key
                                    if getattr(tv, 'inputs_available', None) is False:
                                        checks.update('inventory', 'unknown', 'Warning: TV inputs could not be read. Continuing with applications only.')
                                    else:
                                        checks.update('inventory', 'pass')
                                break
                            except TVNotReady:
                                checks.finish_running()
                                if args.non_interactive:
                                    raise
                                prompts.wait_for_tv(ask, write)
                            except TVConnectionError as error:
                                if phase != 'pair-tv' or error.reason_code != 'pairing-rejected' or args.non_interactive:
                                    raise
                                checks.update('pairing', 'fail', '')
                                write('TV pairing was rejected.')
                                write('Keep the TV on and approve the next pairing request with the remote.')
                                if not prompts.confirm('Try pairing again?', ask, write):
                                    raise
                    write(f"Read {len(inventory['apps'])} applications.")
                phase = 'install-packages'
                def progress(message):
                    nonlocal phase
                    phase = {'Installing Home Helper…': 'install-helper', 'Installing Home…': 'install-home',
                             'Configuring Home Helper…': 'configure-helper',
                             'Starting Home Helper…': 'launch-helper',
                             'Uploading Root and recovery runtime…': 'install-root',
                             'Installing Root Updater and preparing rollback…': 'install-root-updater',
                             'Checking Root Updater…': 'verify-root-updater',
                             'Checking Root recovery…': 'verify-root-recovery',
                             'Stopping the old Home Helper…': 'stop-old-helper',
                             'Turning on Root Home control…': 'activate-root',
                             'Opening Clean Your TV Home…': 'launch-root',
                             'Restoring LG Home and removing the previous Root…': 'remove-existing-root',
                             'Restoring LG Home and removing the previous Clean Your TV installation…': 'remove-existing-root',
                             'Keeping the previous recovery state in an archive…': 'archive-root-state'}.get(message, phase)
                    write(message)
                installer.progress = progress
                if resume:
                    result = installer.resume_root_setup()
                else:
                    result = installer.install(inventory, key, args.migrate_home, reinstall=reinstall) if reinstall else installer.install(inventory, key, args.migrate_home)
                setup_cancelled = False
                setup = {}
                if not args.non_interactive and (not args.yes or write.frontend != 'console'):
                    phase = 'debloat'
                    try:
                        debloat.run(installer, ask, write, diagnostic=tv_info.setdefault('debloat', {}))
                        phase = 'configure-home'
                        setup = install_settings.collect(profile, ask, write,
                            current=install_settings.read_current(installer) if write.frontend == 'desktop' else None)
                    except (EOFError, KeyboardInterrupt):
                        setup_cancelled = True
                if args.tv_name is not None and profile['edition'] == 'root' and not setup_cancelled:
                    setup['tv_name'] = args.tv_name
                if setup:
                    install_settings.apply_services(installer, setup, write)
                phase = 'verify-home-button'
                installer.outcome.review_home(ask, write, args.non_interactive or setup_cancelled)
                installer.observe_failed_root_home_button()
                if profile['edition'] == 'root':
                    write.heading('Review TV checks')
                    if result.get('backend') != 'c1-native-gate':
                        write('Root activation and the launch request completed. Check the separate startup and physical Home results.')
                    if result.get('updates_ready'):
                        write('Root Updater is ready. Install future compatible updates in Settings → Software updates on the TV.')
                    if profile.get('root_variant') == 'node012-beta':
                        write(NOTICE)
                    if result.get('backend') == 'c1-native-gate':
                        write('C1 Beta is installed. Automatic updates are unavailable; after a stop, turn Home control on again in TV settings.')
                    else:
                        write('Home control stays on until you turn it off. The computer can now be switched off.')
                    write('To restore LG Home, use Return to LG Home in settings or run cytv restore.')
                    write('Root emergency exit: three short Home presses within two seconds.')
                else:
                    write('Three short Home presses within two seconds return to LG Home. To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept.')
                    if result.get('activation_cancelled') is not True:
                        write("After installation, press Home to try it. If LG Home opens, open Home Helper from the TV's apps.")
                        write('Packages installed; Home Helper launch requested. Check short Home, arrows/OK, Back, volume, standby and cold boot.')
                    if profile.get('connection') == 'root-ssh':
                        write('No-root is installed using root SSH. Keep this saved connection for status, recovery and removal.')
                    else:
                        write('Emergency exit: three short Home presses within two seconds. Keep Developer Mode active. The computer can now be switched off.')
                        write('Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.')
            elif args.command == 'recover':
                from .recovery import recover
                phase = 'recover'
                if saved_review:
                    write.recovery(profile)
                recover(installer, ask, write, args.non_interactive, review_confirmed=bool(saved_review))
            elif args.command == 'replace-system-updater':
                phase = args.command
                installer.replace_system_updater()
                write('System updates are ready. Open Home Settings → Software updates on the TV.')
            elif args.command == 'recover-root-rollback':
                phase = args.command
                installer.recover_root_rollback()
                write('Previous Root components and profile verified. Rollback recovery is complete.')
            elif args.command == 'recover-system-rollback':
                phase = args.command
                if args.new_recovery_attempt:
                    installer.recover_system_rollback(new_attempt=True)
                else:
                    installer.recover_system_rollback()
                write('Previous Root components and profile verified. Rollback recovery is complete.')
            elif args.command == 'enable-system-updates':
                phase = 'enable-system-updates'
                result = installer.enable_system_updates()
                write('System updates are ready. Open Home Settings → Software updates on the TV.')
            elif args.command in ('enable-firmware-access','disable-firmware-access'):
                phase=args.command
                if args.repair_package_permissions:
                    installer.configure_firmware_access(True,repair=True)
                else:
                    installer.configure_firmware_access(args.command=='enable-firmware-access')
                write('Root Home permissions were updated. Reopen Home and check LG firmware updates.')
            elif args.command == 'home-diagnostics':
                phase = 'home-diagnostics'
                if args.non_interactive:
                    raise UserError('Open Home button diagnostics in the installer to record a Home press.')
                write.heading('Home button diagnostics')
                write('Open an app on the TV. Recording lasts one minute and saves one report with application IDs and timing.')
                if not prompts.confirm('Ready to record? Continue and wait for the Home prompt.', ask, write, default=True):
                    return 0
                report = diagnostics.collect_home_report(remote, store, profile, write, reconnect=reconnect_tv)
                write.report(report)
            elif args.command == 'clean-wam-cache':
                from . import wam_cleanup
                phase = 'clean-wam-cache'
                write('You can cancel and free space yourself. Use the manual cleanup guide and recheck /var/lib; removing apps may free a different partition.')
                write.raw('https://github.com/Razdva122/clean-your-tv-lg-webos/blob/release/next/docs/WAM-CLEANUP.md')
                snapshot = wam_cleanup.inspect(remote)
                write.heading('Clear WAM caches')
                write.raw('Cache, Code Cache')
                write('Close TV apps first. Cached data will be downloaded or rebuilt; the next app launch may be slower.')
                write('Only cache and codecache are requested. Session Storage, cookies, Local Storage, Service Worker and databases are excluded.')
                write('WAM cache estimate: {size} MiB. Free in /var/lib: {available} MiB.'.format(
                    size=format(snapshot['bytes']/1048576, '.1f'), available=format(snapshot['available_kib']/1024, '.1f')))
                if not prompts.confirm('Clear WAM Cache and Code Cache through the TV service?', ask, write):
                    write('Cancelled. No cache cleanup was requested.')
                    return 0
                wam_cleanup.clean(remote)
                write('Cache cleanup request accepted. Recheck free space before retrying installation; no reboot or setup resume was requested.')
            elif args.command == 'doctor':
                phase = 'doctor'
                if profile['edition']=='root' and not store.pending(profile):
                    installer.preflight(home_interfaces=True, diagnose=True)
                else:
                    installer.preflight()
                write('Connection and basic requirements passed. This does not certify hardware compatibility.')
                result = installer.status()
                write.doctor_result(result)
                if args.report:
                    diagnostics.save_result(write, store, args.command, profile, 'doctor-complete', tv_info, checks=checks.results, status=result)
            else:
                phase = args.command
                if args.command == 'uninstall':
                    if not args.non_interactive:
                        debloat.offer_restore(remote, store, profile, ask, write)
                    result = installer.uninstall(full_project=True)
                else:
                    result = getattr(installer, args.command)()
                if args.command == 'restore' and removal_operation is not None:
                    from .recovery import restored_for_uninstall
                    restored_for_uninstall(write, profile, removal_operation, result,
                                           evidence=tv_info.get('removal_evidence'))
                from .recovery import verified_removal_plan
                if verified_removal_plan(write, profile, result, evidence=tv_info.get('removal_evidence'),
                                         next_step='Other TV apps stay installed.'):
                    write.heading('Clean Your TV removed')
                    write('Clean Your TV removed. Its apps, startup and Home-button control were removed.')
                    if result.get('temporary_files_retained'):
                        write('Some temporary recovery files were kept.')
                    elif result.get('empty_helper_dirs_retained') is not True:
                        write('Only ownership backups and minimal removal records were kept.')
                elif result.get('restart_required') is True:
                    from .recovery import removal_plan
                    removal_plan(write,store,profile,state='waiting',restart_observed=True,
                                 evidence=tv_info.get('removal_evidence'))
                elif (result.get('reconciled') or '').startswith('updater-not-started'):
                    write.heading('Ready to reinstall Root')
                    write('The previous attempt stopped before Root Updater setup. Recovery and installed files are verified; the previous operation report was saved.')
                    write('Return to the start screen, choose Set up my TV and confirm reinstallation. In the console, run cytv install.')
                else:
                    write.raw(json.dumps(result, indent=2))
            if args.command in ('install', 'status', 'restore', 'recover', 'uninstall'):
                diagnostics.save_result(write, store, args.command, profile,
                    'install-complete' if args.command == 'install' else phase, tv_info,
                    checks=checks.results, status=result if args.command in ('status', 'restore', 'uninstall') else tv_info.get('status'))
            if args.command == 'install':
                diagnostics.context.clear_previous_attempt(store, profile)
            if args.command in ('status', 'doctor', 'restore'):
                pending = store.pending(profile)
                if pending:
                    if pending.get('recovery_protocol') == 'no-root-original-stream-v1':
                        from .recovery import no_root_package_check_plan
                        from .recovery_state import assess
                        if no_root_package_check_plan(write, profile, pending, assess(profile, pending, result)):
                            return 0
                    from .recovery import missing_root_deployment_plan
                    write.recovery(profile)
                    missing_root_deployment_plan(write, profile, pending, result)
        return 0
    except (EOFError, KeyboardInterrupt, StopIteration):
        checks.finish_running(cancelled=True)
        if partial or args.command == 'ssh-command':
            return 130
        if args.command == 'debloat':
            write('Cancelled')
            return 130
        from .recovery import cancelled
        cancelled(write, store, profile, args.command, phase, tv_info, checks.results)
        return 130
    except UserError as exc:
        checks.finish_running()
        if profile and exc.reason_code == 'operation-active':
            from .failure_help import for_error
            from .recovery import active_operation_plan
            active_operation_plan(write, profile, failure=for_error(exc, phase, profile, store.pending(profile)))
            return 2
        write.error('Could not complete this step', heading=True)
        unverified_review = saved_review and remote is None
        write.error((None if partial or unverified_review else
                     removal_connection_message(store, profile, phase, exc)) or str(exc))
        if phase in ('pair-tv', 'read-inventory'):
            write('Installation has not started. No TV packages were changed by this attempt.')
        if not partial:
            from .recovery import removal_plan
            help = explain_failure(write, store, profile, phase, exc, offer_actions=not unverified_review)
            if not unverified_review:
                removal_plan(write, store, profile, failure=help, error=exc, phase=phase,
                             evidence=tv_info.get('removal_evidence'))
        failure, exit_code = exc, 2
    except Exception as exc:
        checks.finish_running()
        write.error('Could not complete this step', heading=True)
        kind = type(exc).__name__
        hints = {
            'BadHostKeyException': 'TV identity changed since the last trusted connection. cytv stopped before sign-in. If you reset the TV or changed SSH, verify that change through your existing trusted setup before connecting again.',
            'AuthenticationException': 'SSH authentication failed. Check your key/password; for No-root check Developer Mode and Key Server.',
            'ModuleNotFoundError': 'Source dependencies are missing. Install cytv/requirements.txt or use a built cytv executable.',
        }
        unverified_review = saved_review and remote is None
        message = None if partial or unverified_review else removal_connection_message(store, profile, phase, exc)
        write.error(message or ('Could not read the TV applications. Keep the TV on and accept its pairing request. Installation has not started.'
              if phase in ('pair-tv', 'read-inventory') and kind != 'ModuleNotFoundError' else hints.get(kind,
              'Removal could not be verified. Review recovery options before continuing.' if args.command=='uninstall'
              else 'Operation could not be confirmed. Save the diagnostic report and keep recovery data; do not retry blindly.')))
        if not partial:
            from .recovery import removal_plan
            help = explain_failure(write, store, profile, phase, exc, offer_actions=not unverified_review)
            if not unverified_review:
                removal_plan(write, store, profile, failure=help, error=exc, phase=phase,
                             evidence=tv_info.get('removal_evidence'))
        failure, exit_code = exc, 1
    finally:
        if profile and profile.get('root_variant') == 'node012-beta' and args.command == 'install':
            from .root_runtime import FEEDBACK
            write(FEEDBACK)
        if remote is not None:
            remote.close()

    diagnostics.suggest_issue(write, store, args.command, profile, phase, failure, tv_info,
                              checks=checks.results, status=tv_info.get('status'),
                              ask=None if args.non_interactive else ask)
    return exit_code


def interactive_main(*args, **kwargs):
    """Computer frontends opt into the public release advisory before TV changes."""
    return main(*args, check_updates=True, **kwargs)


def entry():
    # Keep the console visible when a frozen Windows executable is opened from Explorer.
    launched_without_args = getattr(sys, 'frozen', False) and sys.platform == 'win32' and len(sys.argv) == 1
    code = interactive_main()
    if launched_without_args:
        try:
            input(i18n.translate('\nPress Enter to close…'))
        except (EOFError, KeyboardInterrupt):
            pass
    return code

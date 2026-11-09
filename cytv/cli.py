"""Numbered terminal wizard and small maintenance command surface."""
import argparse
import getpass
import io
import json
from pathlib import Path
import sys
from time import sleep

from . import __version__, package, state, i18n
from .errors import UserError, TVNotReady, ExistingRoot
from .operations import Installer
from .terminal import Console, supports_ansi
from . import diagnostics, discovery, inspect_tv, prompts


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


def parser():
    result = LanguageParser(prog='cytv', add_help=False, description=i18n.translate('Clean Your TV — one installer for No-root and Root.'))
    result._positionals.title = i18n.translate('positional arguments')
    result._optionals.title = i18n.translate('options')
    result.add_argument('-h', '--help', action='help', help=i18n.translate('Show this help message and exit'))
    result.add_argument('command', nargs='?', default='install', choices=('install', 'status', 'doctor', 'home-diagnostics', 'recover', 'restore', 'uninstall', 'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access', 'recover-system-rollback', 'replace-system-updater', 'clean-wam-cache'))
    result.add_argument('--language', choices=tuple(i18n.LANGUAGES), help=i18n.translate('Interface language (auto uses the computer language)'))
    result.add_argument('--version', action='store_true', help=i18n.translate('Print installer version'))
    result.add_argument('--host', help=i18n.translate('TV IPv4 address or hostname'))
    result.add_argument('--no-discovery', action='store_true', help=i18n.translate('Skip local network discovery and enter a TV address manually'))
    result.add_argument('--edition', choices=('no-root', 'root'))
    result.add_argument('--tv-name', type=package.normalize_tv_name, help=i18n.translate('Launcher name shown while loading (default: Home)'))
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
    result.add_argument('--report', action='store_true', help=i18n.translate('doctor: save an issue-ready diagnostic report without private connection data'))
    return result


def explain_failure(write, store, profile, phase, error):
    from .failure_help import for_error
    pending = store.diagnostic_pending if hasattr(store, 'diagnostic_pending') else store.pending(profile) if profile else None
    help = for_error(error, phase, profile, pending)
    if help:
        write.failure_help(help)
        if help['code'] in ('removal-not-submitted','no-root-recovery'):
            write.recovery(profile)
        if phase != 'recover' and pending and pending.get('action') in ('install', 'activate-root'):
            from .recovery import offer_install_recovery
            offer_install_recovery(write, store, profile)
    return help


def removal_connection_message(store, profile, phase, error):
    if not profile or (store.pending(profile) or {}).get('recovery_protocol')!='clean-removal-v1':return None
    disconnected=(isinstance(error,ConnectionError) or getattr(error,'reason_code',None)=='connection-interrupted'
                  or type(error).__name__ in ('SSHException','NoValidConnectionsError')
                  or phase=='ssh-connect' and isinstance(error,TimeoutError))
    if not disconnected:return None
    store.checkpoint(profile,removal_reason='connection-interrupted')
    return 'Connection to the TV was interrupted. Check the connection and try again.'


def choose_profile(args, store, ask, write, search, inspect):
    profiles = [p for p in store.profiles() if not args.edition or p['edition'] == args.edition]
    if not args.host and len(profiles) == 1 and (args.command != 'install' or args.non_interactive):
        profile = dict(profiles[0])
        write('Using saved ' + profile['edition'] + ' TV connection.')
    elif not args.host and profiles:
        write.step(1, 'Choose a saved TV')
        for index, p in enumerate(profiles, 1):
            write.option(index, p['host'], 'Root' if p['edition'] == 'root' else 'No-root')
        write.option(0, 'Add another TV')
        selected = prompts.number(ask, write, 'TV number [1]: ', 0, len(profiles), default=1)
        profile = dict(profiles[selected - 1]) if selected else None
    else:
        profile = None
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
    return state.target(**profile)


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
    except OSError:
        i18n.set_language(language_args.language or 'auto')
        (write if isinstance(write, Console) else Console(write)).error('Could not save language preference', heading=True)
        (write if isinstance(write, Console) else Console(write)).error('Check write access to the application data folder and try again.')
        return 2
    args = parser().parse_args(argv)
    if args.version:
        write('cytv ' + __version__)
        return 0
    write = write if isinstance(write, Console) else Console(write, interactive=False if args.non_interactive else None)
    from .checks import CheckList
    checks = CheckList(write.check)
    ask = write.reader(ask)
    remote = None
    store, profile, phase, tv_info = state.Store(args.data_dir), None, 'select-tv', {'frontend':getattr(write,'frontend','console')}
    try:
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
        if args.non_interactive:
            def no_ask(_):
                raise UserError('Non-interactive mode needs --host and --edition or one saved profile; pairing and SSH trust must already be completed.')
            ask = no_ask
            secret = no_ask
        if args.command == 'install' and not args.non_interactive:
            write.heading('Clean Your TV  /  Installation')
            write('TV > Edition > Connection > Install')
            write('q / Ctrl+C = quit. Password entry uses Ctrl+C.')
        def inspect_connection(host, port):
            nonlocal phase
            phase = 'inspect-tv'
            info = (inspect or inspect_tv.inspect)(host, port)
            phase = 'select-edition'
            return info

        profile = choose_profile(args, store, ask, write, search or discovery.find_tvs, inspect_connection)
        write.selected_profile(profile)
        if args.command == 'replace-system-updater':
            if profile['edition'] != 'root': raise UserError('System Updater replacement requires an existing Root connection.')
            if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        if args.command == 'recover-system-rollback':
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
        if check_updates and args.command == 'install' and not store.pending(profile):
            from .installer_update import offer
            if not offer(ask, write, args.non_interactive, args.use_bundled_version):
                return 0
        if args.command == 'install':
            phase = 'prepare-payload'
            write.step(3, 'Prepare the TV connection')
            if profile['edition'] == 'root':
                write('Root requires existing root and SSH access.')
                if not profile.get('root_variant'):
                    write('Hardware validation: LG C3; other models are unverified.')
            elif profile.get('connection') != 'root-ssh':
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
                if not profile.get('root_variant'):
                    write('Hardware validation: LG C3; other models are unverified.')
                write('Automatic SSH sign-in first; credentials only if needed.')
            write('Next: verify SSH, read your apps, then install.')
            if profile['edition']=='no-root':
                write('Pairing is a separate step: when the TV asks, approve CYTV with your remote.')
            if profile['edition'] == 'root':
                write('Root will stop the old Home Helper, turn on Home control and open Clean Your TV Home.')
            write('Check controls on the TV after installation.')
        retry_removal=(args.command=='uninstall' and (store.pending(profile) or {}).get('recovery_protocol')=='clean-removal-v1')
        if args.command in ('install', 'uninstall', 'restore', 'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access', 'recover-system-rollback', 'replace-system-updater') and not args.yes and not retry_removal:
            if args.command == 'uninstall' and profile['edition'] == 'root':
                write('This removes Root, Root Updater, their services and startup hooks, plus any installed No-root Home, Helper and Updater.')
                write('Recovery records are retained for diagnostics. Other TV apps stay installed.')
            verb = {'install': 'Connect to check installed versions', 'uninstall': 'Restore LG Home and remove this edition', 'restore': 'Restore LG Home', 'enable-system-updates': 'Prepare updates for all system components on this rooted TV','enable-firmware-access':'Change Root Home access to Homebrew configuration','disable-firmware-access':'Change Root Home access to Homebrew configuration','recover-system-rollback':'Recover verified Root rollback readiness','replace-system-updater':'Replace only the System Updater and preserve Root settings'}[args.command]
            if args.command == 'uninstall' and profile['edition'] == 'root':
                pending = store.pending(profile)
                if pending and pending.get('action') == 'uninstall' and pending.get('full_project') is True:
                    verb = 'Check TV and continue removal'
            if not prompts.confirm(verb + '?', ask, write, default=args.command == 'install'):
                write('Cancelled. No TV changes were made.')
                return 0
        # Canonicalize the selected local build root (macOS /var is an OS
        # alias); authenticated support members still reject indirect children.
        payload, manifest = (Path(payload_root) if payload_root is not None else payload_dir()).resolve(), {}
        if args.command in ('install', 'enable-system-updates','enable-firmware-access','disable-firmware-access','replace-system-updater') or profile.get('root_variant'):
            try:
                manifest = package.verify_payload(payload)
            except FileNotFoundError:
                raise UserError('Release payload is missing. Download a built cytv executable or run python scripts/build-cytv.py --payload-only from source.') from None
            if args.migrate_home and profile['edition'] != 'root':
                raise UserError('--migrate-home applies only to Root installation.')

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
        with store.lock(profile), diagnostics.context.operation_context(store, profile):
            profile, recovering = store.connection_profile(profile)
            # An explicit sign-in key may change; the saved TV identity and pin
            # must still be resolved and verified before using it.
            if (recovering and args.identity and args.command == 'uninstall'
                    and (profile['edition'] == 'root' or profile.get('connection') == 'root-ssh')
                    and (store.pending(profile) or {}).get('recovery_protocol') == 'clean-removal-v1'):
                profile = dict(profile, identity=str(args.identity.expanduser().resolve()))
            if args.command=='uninstall':
                if not recovering:store.save(profile)
                store.request_clean_removal(profile)
            from .recovery import removal_plan
            cleanup=(store.pending(profile) or {}).get('recovery_protocol')=='clean-removal-v1'
            if args.command in ('uninstall','recover') and cleanup:
                removal_plan(write,store,profile,state='waiting',connecting=True)
                try:manifest=package.verify_payload(payload)
                except FileNotFoundError:
                    raise UserError('Release payload is missing. Download a built cytv executable or run python scripts/build-cytv.py --payload-only from source.') from None
            if args.command == 'replace-system-updater':
                if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
            if args.command in ('enable-firmware-access','disable-firmware-access','recover-system-rollback') and store.pending(profile):raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
            if args.command == 'clean-wam-cache' and store.pending(profile):
                raise UserError('Resolve the pending installation or removal before clearing WAM data. Keep recovery records.')
            phase = 'ssh-connect'
            if args.command in ('install', 'doctor'):
                checks.prepare(profile['edition'], args.command)
            checks.update('ssh', 'running')
            write('Connecting to the TV…')
            def connect_tv(pinned):
                if connect:
                    # Older embedders accept exactly four positional arguments.
                    import inspect as signature_inspect
                    options = {}
                    if pinned:
                        try:
                            signature_inspect.signature(connect).bind(profile, store.device_dir(profile), secret_with_help, trust, persist=False)
                            options['persist'] = False
                        except TypeError:
                            pass
                    return connect(profile, store.device_dir(profile), secret_with_help,
                                   (lambda *_: False) if pinned else trust, **options)
                return SSH.connect(profile, store.device_dir(profile), secret_with_help, trust,
                                   identity_prompt=None if pinned or args.non_interactive else lambda: prompts.root_credentials(ask, write),
                                   persist=not pinned)

            from .errors import connection_interrupted
            for attempt in range(3 if cleanup else 1):
                try:
                    remote = connect_tv(recovering)
                    break
                except Exception as error:
                    if not cleanup or attempt == 2 or not connection_interrupted(error):
                        raise
                    write('Connecting to the TV…')
                    sleep(attempt + 1)
            checks.update('ssh', 'pass')
            if not recovering and args.command in ('install', 'status', 'doctor', 'recover'):
                diagnostics.context.collect_metadata(remote, tv_info)
            if not recovering:
                store.save(profile)
                pending=store.pending(profile)
                if pending and pending.get('recovery_protocol')=='clean-removal-v1' and pending.get('connection_pending') is True:
                    store.checkpoint(profile,connection_pending=False)
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
                resume = False
                pending = store.pending(profile)
                replacing_activation = (profile['edition'] == 'root' and pending
                    and pending.get('action') == 'activate-root'
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
                if profile.get('root_variant') == BETA:
                    write(NOTICE)
                    if args.non_interactive or not prompts.confirm('Install experimental Root Beta?', ask, write):
                        raise EOFError
                if profile['edition'] == 'root' and not resume:
                    installer.select_graphics()
                    phase = 'inspect-installation'
                    try:
                        if replacing_activation:
                            reinstall = 'installed'
                        else:
                            installer.preflight(install=True, home_interfaces=True)
                    except ExistingRoot:
                        if tv_info.get('home_backend') == 'c1-native-gate':
                            raise UserError('Root is already installed or recovery state remains. Use cytv status or cytv restore; reinstallation has not started.')
                        reinstall = 'installed'
                    except UserError as error:
                        if (error.reason_code != 'root-requirements' or profile.get('root_variant')
                                or tv_info.get('root_requirements', {}).get('node-version') != 'fail'):
                            raise
                        if args.migrate_home:
                            raise UserError('Choose an alternative edition without --migrate-home. Installation has not started.')
                        from .root_runtime import offer
                        offer(installer, args, ask, write)
                        installer.select_graphics()
                        installer.preflight(install=True, home_interfaces=profile['edition']=='root')
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
                        return 0
                if not reinstall and not resume:
                    phase = 'inspect-installation'
                    write.heading('Versions on the TV → versions in this installer')
                    for row in installer.version_summary():
                        write(row)
                    if not args.yes and not prompts.confirm('Install these versions?', ask, write, default=True):
                        write('Cancelled. No TV changes were made.')
                        return 0
                if profile['edition'] == 'no-root':
                    phase = 'inspect-installation'
                    while True:
                        try:
                            installer.preflight(install=True)
                            break
                        except UserError as error:
                            if error.reason_code != 'helper-running' or args.non_interactive:
                                raise
                            write.heading('Stop Home Helper on the TV')
                            write('Press Home three times within two seconds (older Helper: hold Home for two seconds), then release all buttons and wait for LG Home.')
                            if not prompts.confirm('Try stopping Helper again?', ask, write, default=True):
                                write('Cancelled. No TV changes were made.')
                                return 0
                if not resume:
                    installer.select_graphics()
                    installer.tv_name = (args.tv_name if args.tv_name is not None else
                                         'Home' if args.non_interactive or args.yes else prompts.tv_name(ask, write))
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
                                        inventory = tv.inventory((payload / 'fallback.png').read_bytes())
                                    finally:
                                        icon_counts = getattr(tv, 'icon_diagnostics', None)
                                        if type(icon_counts) is dict:
                                            tv_info['icon_inventory'] = icon_counts
                                    key = tv.key
                                    checks.update('inventory', 'pass')
                                break
                            except TVNotReady:
                                checks.finish_running()
                                if args.non_interactive:
                                    raise
                                prompts.wait_for_tv(ask, write)
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
                             'Keeping the previous recovery state in an archive…': 'archive-root-state'}.get(message, phase)
                    write(message)
                installer.progress = progress
                def helper_retry():
                    if args.non_interactive:
                        return False
                    write.heading('Stop Home Helper on the TV')
                    write('Press Home three times within two seconds (older Helper: hold Home for two seconds), then release all buttons and wait for LG Home.')
                    return prompts.confirm('Try stopping Helper again?', ask, write, default=True)
                installer.helper_retry = helper_retry
                if resume:
                    result = installer.resume_root_setup()
                else:
                    result = installer.install(inventory, key, args.migrate_home, reinstall=reinstall) if reinstall else installer.install(inventory, key, args.migrate_home)
                phase = 'verify-home-button'
                installer.outcome.review_home(ask, write, args.non_interactive)
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
                    write("After installation, press Home to try it. If LG Home opens, open Home Helper from the TV's apps.")
                    write('Three short Home presses within two seconds return to LG Home. To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept.')
                    write('Packages installed; Home Helper launch requested. Check short Home, arrows/OK, Back, volume, standby and cold boot.')
                    if profile.get('connection') == 'root-ssh':
                        write('No-root is installed using root SSH. Keep this saved connection for status, recovery and removal.')
                    else:
                        write('Emergency exit: three short Home presses within two seconds. Keep Developer Mode active. The computer can now be switched off.')
                        write('Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.')
            elif args.command == 'recover':
                from .recovery import recover
                phase = 'recover'
                recover(installer, ask, write, args.non_interactive)
            elif args.command == 'replace-system-updater':
                phase = args.command
                installer.replace_system_updater()
                write('System updates are ready. Open Home Settings → Software updates on the TV.')
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
                report = diagnostics.collect_home_report(remote, store, profile, write)
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
                    installer.preflight(home_interfaces=True)
                else:
                    installer.preflight()
                write('Connection and basic requirements passed. This does not certify hardware compatibility.')
                result = installer.status()
                write.raw(json.dumps(result, indent=2))
                if args.report:
                    diagnostics.save_result(write, store, args.command, profile, 'doctor-complete', tv_info, checks=checks.results, status=result)
            else:
                phase = args.command
                result = installer.uninstall(full_project=True) if args.command == 'uninstall' else getattr(installer, args.command)()
                if result.get('verified_clean') is True and result.get('removed') is True:
                    write.recovery_plan({'state':'complete','disposition':'clean-removal','verified_clean':True,'removed':True,
                                         'summary':'Clean Your TV removal is verified.','next_step':'Other TV apps stay installed.'})
                    write.heading('Clean Your TV removed')
                    write('Clean Your TV removed. Its apps, startup and Home-button control were removed.')
                    if result.get('temporary_files_retained'):
                        write('Some temporary files were kept; they do not prevent reinstallation.')
                    else:
                        write('Only ownership backups and minimal removal records were kept.')
                elif result.get('restart_required') is True:
                    from .recovery import removal_plan
                    removal_plan(write,store,profile,state='waiting')
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
                    write.recovery(profile)
        return 0
    except (EOFError, KeyboardInterrupt, StopIteration):
        checks.finish_running(cancelled=True)
        from .recovery import cancelled
        cancelled(write, store, profile, args.command, phase, tv_info, checks.results)
        return 130
    except UserError as exc:
        checks.finish_running()
        write.error('Could not complete this step', heading=True)
        write.error(removal_connection_message(store,profile,phase,exc) or str(exc))
        if phase in ('pair-tv', 'read-inventory'):
            write('Installation has not started. No TV packages were changed by this attempt.')
        from .recovery import removal_plan
        help = explain_failure(write, store, profile, phase, exc)
        removal_plan(write,store,profile,failure=help)
        diagnostics.suggest_issue(write, store, args.command, profile, phase, exc, tv_info, checks=checks.results, status=tv_info.get('status'))
        return 2
    except Exception as exc:
        checks.finish_running()
        write.error('Could not complete this step', heading=True)
        kind = type(exc).__name__
        hints = {
            'BadHostKeyException': 'TV identity changed since the last trusted connection. cytv stopped before sign-in. If you reset the TV or changed SSH, verify that change through your existing trusted setup before connecting again.',
            'AuthenticationException': 'SSH authentication failed. Check your key/password; for No-root check Developer Mode and Key Server.',
            'ModuleNotFoundError': 'Source dependencies are missing. Install cytv/requirements.txt or use a built cytv executable.',
        }
        message=removal_connection_message(store,profile,phase,exc)
        write.error(message or ('Could not read the TV applications. Keep the TV on and accept its pairing request. Installation has not started.'
              if phase in ('pair-tv', 'read-inventory') and kind != 'ModuleNotFoundError' else hints.get(kind,
              'Some Clean Your TV files or settings remain. Choose Try again.' if args.command=='uninstall'
              else 'Operation could not be confirmed. Save the diagnostic report and keep recovery data; do not retry blindly.')))
        from .recovery import removal_plan
        help = explain_failure(write, store, profile, phase, exc)
        removal_plan(write,store,profile,failure=help)
        diagnostics.suggest_issue(write, store, args.command, profile, phase, exc, tv_info, checks=checks.results, status=tv_info.get('status'))
        return 1
    finally:
        if profile and profile.get('root_variant') == 'node012-beta' and args.command == 'install':
            from .root_runtime import FEEDBACK
            write(FEEDBACK)
        if remote is not None:
            remote.close()


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

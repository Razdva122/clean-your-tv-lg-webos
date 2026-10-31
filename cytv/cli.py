"""Numbered terminal wizard and small maintenance command surface."""
import argparse
import getpass
import io
import json
from pathlib import Path
import sys

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
    result.add_argument('command', nargs='?', default='install', choices=('install', 'status', 'doctor', 'home-diagnostics', 'restore', 'uninstall', 'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access', 'recover-system-rollback', 'replace-system-updater', 'clean-wam-cache'))
    result.add_argument('--language', choices=tuple(i18n.LANGUAGES), help=i18n.translate('Interface language (auto uses the computer language)'))
    result.add_argument('--version', action='store_true', help=i18n.translate('Print installer version'))
    result.add_argument('--host', help=i18n.translate('TV IPv4 address or hostname'))
    result.add_argument('--no-discovery', action='store_true', help=i18n.translate('Skip local network discovery and enter a TV address manually'))
    result.add_argument('--edition', choices=('no-root', 'root'))
    result.add_argument('--port', type=int, help=i18n.translate('SSH port (No-root: 9922; Root: 22)'))
    result.add_argument('--identity', type=Path, help=i18n.translate('Existing Root SSH private key'))
    result.add_argument('--data-dir', type=Path, help=i18n.translate('Private local profile directory'))
    result.add_argument('--non-interactive', action='store_true', help=i18n.translate('Never prompt; needs a saved, trusted connection'))
    result.add_argument('--yes', action='store_true', help=i18n.translate('Accept install/remove summary; does not accept SSH trust'))
    result.add_argument('--migrate-home', action='store_true', help=i18n.translate('Root install: explicitly import existing Home packaged/profile data'))
    result.add_argument('--check-payload', action='store_true', help=i18n.translate('Verify embedded release assets without contacting a TV'))
    result.add_argument('--prepare-python-runtime', action='store_true', help=i18n.translate('Download and verify the optional TV Python for offline setup'))
    result.add_argument('--new-recovery-attempt', action='store_true', help=i18n.translate('recover-system-rollback: explicitly start a new audited attempt after the old deadline'))
    result.add_argument('--repair-package-permissions', action='store_true', help=i18n.translate('enable-firmware-access: explicitly repair verified Root package permissions'))
    result.add_argument('--report', action='store_true', help=i18n.translate('doctor: save an issue-ready diagnostic report without private connection data'))
    return result


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
            profile = state.target(host, edition, args.port, args.identity)
        except ValueError:
            raise UserError('Invalid TV address or port. Use an IPv4 address or hostname and a port from 1 to 65535.') from None
        # Match saved credentials, including the identity, when targeting a known TV explicitly.
        for saved in profiles:
            if all(saved[k] == profile[k] for k in ('host', 'edition', 'port')):
                profile = dict(saved)
                break
    if args.port is not None:
        profile['port'] = args.port
    if args.identity:
        profile['identity'] = str(args.identity.expanduser().resolve())
    return state.target(**profile)


def main(argv=None, ask=input, write=print, connect=None, secret=getpass.getpass, search=None, inspect=None, payload_root=None):
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
    store, profile, phase, tv_info = state.Store(args.data_dir), None, 'select-tv', {}
    try:
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
        if args.command == 'replace-system-updater':
            if profile['edition'] != 'root': raise UserError('System Updater replacement requires an existing Root connection.')
            if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        if args.command == 'recover-system-rollback':
            if profile['edition'] != 'root': raise UserError('Rollback readiness recovery requires an existing Root connection.')
            if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        if args.command in ('enable-firmware-access','disable-firmware-access'):
            if profile['edition']!='root':raise UserError('Homebrew API access requires an existing Root installation.')
            if store.pending(profile):raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        if args.command == 'clean-wam-cache':
            if profile['edition'] != 'root':
                raise UserError('WAM cleanup requires an existing Root SSH connection.')
            if store.pending(profile):
                raise UserError('Resolve the pending installation or removal before clearing WAM data. Keep recovery records.')
        if args.command == 'install':
            phase = 'prepare-payload'
            write.step(3, 'Prepare the TV connection')
            if profile['edition'] == 'root':
                write('Root requires existing root and SSH access.')
                write('Hardware validation: LG C3; other models are unverified.')
            else:
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
            write('Edition: ' + ('Root' if profile['edition'] == 'root' else 'No-root'))
            write('SSH port: ' + str(profile['port']))
            if profile['edition'] == 'root':
                write('Hardware validation: LG C3; other models are unverified.')
                write('Automatic SSH sign-in first; credentials only if needed.')
            write('Next: verify SSH, read your apps, then install.')
            write('Pairing is a separate step: when the TV asks, approve CYTV with your remote.')
            if profile['edition'] == 'root':
                write('Root will stop the old Home Helper, turn on Home control and open Clean Your TV Home.')
            write('Check controls on the TV after installation.')
        if args.command in ('install', 'uninstall', 'restore', 'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access', 'recover-system-rollback', 'replace-system-updater') and not args.yes:
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
        payload, manifest = Path(payload_root) if payload_root is not None else payload_dir(), {}
        if args.command in ('install', 'enable-system-updates','enable-firmware-access','disable-firmware-access','replace-system-updater'):
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
            return secret(write.prompt(prompt))

        from .transport import SSH
        with store.lock(profile):
            if args.command == 'replace-system-updater':
                if store.pending(profile): raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
            if args.command in ('enable-firmware-access','disable-firmware-access','recover-system-rollback') and store.pending(profile):raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
            if args.command == 'clean-wam-cache' and store.pending(profile):
                raise UserError('Resolve the pending installation or removal before clearing WAM data. Keep recovery records.')
            phase = 'ssh-connect'
            if args.command in ('install', 'doctor'):
                checks.prepare(profile['edition'], args.command)
            checks.update('ssh', 'running')
            write('Connecting to the TV…')
            if connect:
                remote = connect(profile, store.device_dir(profile), secret_with_help, trust)
            else:
                remote = SSH.connect(profile, store.device_dir(profile), secret_with_help, trust,
                                     identity_prompt=None if args.non_interactive else lambda: prompts.root_credentials(ask, write))
            checks.update('ssh', 'pass')
            store.save(profile)
            installer = Installer(remote, store, profile, payload, manifest, write, tv_info=tv_info, checks=checks)
            if args.command == 'install':
                reinstall = None
                resume = False
                if store.pending(profile):
                    phase = 'inspect-installation'
                    write('Checking the previous installation on the TV…')
                    existing = installer.status()
                    pending = store.pending(profile)
                    if (profile['edition'] == 'no-root' and pending and
                            (pending.get('action') == 'uninstall' or
                             (pending.get('action') == 'install' and pending.get('stage') == 'pending'))):
                        write.heading('Recover and reinstall' if pending['action'] == 'install' else 'Unfinished removal')
                        if pending['action'] == 'install':
                            write('The previous installation did not finish. Remove its packages before installing again.')
                        write('Finish removing Clean Your TV before installing again. LG Home will be restored and remaining Clean Your TV packages removed.')
                        write('After removal is verified, setup continues with the bundled versions.')
                        if args.non_interactive:
                            raise UserError('Open cytv interactively to finish the previous removal, or run cytv uninstall for this TV, then retry installation.')
                        if not prompts.confirm('Finish removal before installing again?', ask, write):
                            write('Recovery data kept. Installation has not restarted.')
                            return 0
                        phase = 'uninstall'
                        installer.uninstall()
                        phase = 'inspect-installation'
                        if store.pending(profile):
                            raise UserError('The previous operation could not be safely resolved. Recovery data was kept. Save the diagnostic report; installation has not restarted.')
                    if existing.get('can_resume_root_setup') is True:
                        if args.non_interactive:
                            raise UserError('Root setup is ready to finish. Open cytv interactively to confirm Home activation.')
                        write.heading('Ready to finish Root setup')
                        write('Root and Root Updater are installed and verified. Continue to stop the old Helper, turn on Home control and open Clean Your TV Home.')
                        if not prompts.confirm('Finish Root setup?', ask, write, default=True):
                            write('Setup left unchanged. You can continue here next time.')
                            return 0
                        resume = True
                    elif store.pending(profile):
                        raise UserError('The previous operation could not be safely resolved. Recovery data was kept. Save the diagnostic report; installation has not restarted.')
                if profile['edition'] == 'root' and not resume:
                    phase = 'inspect-installation'
                    try:
                        installer.preflight(install=True)
                    except ExistingRoot:
                        if args.migrate_home:
                            raise UserError('For Root reinstallation, omit --migrate-home. cytv will read a fresh TV inventory before replacing Root; the existing installation was left unchanged.')
                        existing = installer.status()
                        stage = existing.get('deployment_stage')
                        device = existing.get('device', {}).get('result', {})
                        if stage == 'installed-recovery-only' and device.get('recovery', {}).get('integrity_verified') is True:
                            reinstall = 'installed'
                        elif stage == 'uninstalled-state-retained':
                            reinstall = 'removed'
                        else:
                            raise UserError('Previous Root installation needs recovery. Run cytv status or cytv restore. Reinstallation has not started; recovery data was left unchanged.')
                        if args.non_interactive:
                            raise UserError('Root is already installed or removal data remains. Run cytv interactively to review reinstallation. --yes does not approve replacing Root.')
                        write.heading('Versions on the TV → versions in this installer')
                        for row in installer.version_summary():
                            write(row)
                        write.heading('Root is already installed' if reinstall == 'installed' else 'Previous Root was removed')
                        write('You can reinstall using the packages in this cytv build.')
                        write('LG Home will be restored first. Previous recovery data will be archived on the TV.')
                        write('Root preferences may be reset. Your other TV apps will stay installed.')
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
                phase = 'read-inventory'
                inventory, key = None, None
                if not args.migrate_home and not resume:
                    from .tv import SSAP
                    while True:
                        try:
                            phase = 'pair-tv'
                            checks.update('pairing', 'running', '')
                            with SSAP(profile['host'], store.device_dir(profile), write) as tv:
                                checks.update('pairing', 'pass')
                                phase = 'read-inventory'
                                checks.update('inventory', 'running', '')
                                inventory = tv.inventory((payload / 'fallback.png').read_bytes())
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
                if profile['edition'] == 'root':
                    write.heading('Root is ready')
                    write('Home control is on and Clean Your TV Home was opened.')
                    if result.get('updates_ready'):
                        write('Root Updater is ready. Install future compatible updates in Settings → Software updates on the TV.')
                    write('Home control stays on until you turn it off. The computer can now be switched off.')
                    write('To restore LG Home, use Return to LG Home in settings or run cytv restore.')
                    write('Root emergency exit: three short Home presses within two seconds.')
                else:
                    write("After installation, press Home to try it. If LG Home opens, open Home Helper from the TV's apps.")
                    write('Three short Home presses within two seconds return to LG Home. To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept.')
                    write('Packages installed; Home Helper launch requested. Check short Home, arrows/OK, Back, volume, standby and cold boot.')
                    write('Emergency exit: three short Home presses within two seconds. Keep Developer Mode active. The computer can now be switched off.')
                    write('Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.')
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
                installer.preflight()
                write('Connection and basic requirements passed. This does not certify hardware compatibility.')
                write.raw(json.dumps(installer.status(), indent=2))
                if args.report:
                    write.report(diagnostics.create_report(store, args.command, profile, 'doctor-complete', tv_info=tv_info))
            else:
                phase = args.command
                result = installer.uninstall(full_project=True) if args.command == 'uninstall' else getattr(installer, args.command)()
                if result.get('applications_services_startup_removed'):
                    write.heading('Clean Your TV removed')
                    write('Project apps, Root Updater service and startup registration were removed. LG Home is restored.')
                    write('Recovery records were retained for diagnostics; they do not start automatically.')
                elif (result.get('reconciled') or '').startswith('updater-not-started'):
                    write.heading('Ready to reinstall Root')
                    write('The previous attempt stopped before Root Updater setup. Recovery and installed files are verified; the previous operation report was saved.')
                    write('Return to the start screen, choose Set up my TV and confirm reinstallation. In the console, run cytv install.')
                else:
                    write.raw(json.dumps(result, indent=2))
            if args.command in ('status', 'doctor', 'restore') and profile['edition'] == 'no-root':
                pending = store.pending(profile)
                if pending and (pending.get('action') == 'uninstall' or
                                (pending.get('action') == 'install' and pending.get('stage') == 'pending')):
                    write.recovery(profile)
        return 0
    except (EOFError, KeyboardInterrupt, StopIteration):
        checks.finish_running(cancelled=True)
        write('Cancelled. Installation has not started.' if args.command == 'install' and phase in ('pair-tv', 'read-inventory', 'prepare-payload', 'select-tv', 'select-edition', 'inspect-tv', 'ssh-connect', 'inspect-installation')
              else 'Cancelled. If an installation was submitted, run cytv status before retrying.')
        return 130
    except UserError as exc:
        checks.finish_running()
        write.error('Could not complete this step', heading=True)
        write.error(str(exc))
        if phase in ('pair-tv', 'read-inventory'):
            write('Installation has not started. No TV packages were changed by this attempt.')
        if args.command == 'uninstall' and phase == 'uninstall' and profile['edition'] == 'root' and store.pending(profile):
            write('Keep the TV on and choose Remove again. The app checks its state before continuing.')
        diagnostics.suggest_issue(write, store, args.command, profile, phase, exc, tv_info)
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
        write.error('Could not read the TV applications. Keep the TV on and accept its pairing request. Installation has not started.'
              if phase in ('pair-tv', 'read-inventory') and kind != 'ModuleNotFoundError' else hints.get(kind, 'Operation could not be confirmed. Check TV connectivity and run cytv status or cytv doctor. Retain local and TV recovery state; do not retry blindly.'))
        if args.command == 'uninstall' and phase == 'uninstall' and profile['edition'] == 'root' and store.pending(profile):
            write('Keep the TV on and choose Remove again. The app checks its state before continuing.')
        diagnostics.suggest_issue(write, store, args.command, profile, phase, exc, tv_info)
        return 1
    finally:
        if remote is not None:
            remote.close()


def entry():
    # Keep the console visible when a frozen Windows executable is opened from Explorer.
    launched_without_args = getattr(sys, 'frozen', False) and sys.platform == 'win32' and len(sys.argv) == 1
    code = main()
    if launched_without_args:
        try:
            input(i18n.translate('\nPress Enter to close…'))
        except (EOFError, KeyboardInterrupt):
            pass
    return code

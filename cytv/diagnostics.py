"""Issue-ready diagnostics built from allowlisted metadata, never raw logs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import traceback
import time
import re
import uuid

from . import __version__
from .state import private_write
from .terminal import console
from .errors import TVConnectionError, DeveloperKeyError, UserError, TVCommandError, TVRejected, PythonPreflightError, PythonCacheError, root_recovery_details

ISSUE_URL = 'https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new'
KERNEL_ARCHES = ('armv7l', 'armv7', 'armv8l', 'aarch64', 'arm64', 'x86_64', 'i686', 'unknown')
ROOT_REQUIREMENTS = ('root-user', 'python3', 'luna-send', 'apps-directory',
                     'luna-services-directory', 'python-json', 'python-fcntl', 'python-version', 'node-version')


def create_report(store, action, profile, phase, error=None, tv_info=None):
    pending = store.pending(profile) if profile else None
    report = {
        'schema': 1, 'cytv_version': __version__,
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'desktop': {'os': platform.system(), 'architecture': platform.machine(), 'python': platform.python_version()},
        'action': action, 'edition': profile.get('edition') if profile else None,
        'phase': phase,
        'error_type': type(error).__name__ if error else None,
        'pending': {k: pending.get(k) for k in ('action', 'stage')} if pending else None,
        'trace': [{'file': Path(frame.filename).name, 'function': frame.name, 'line': frame.lineno}
                  for frame in traceback.extract_tb(error.__traceback__)[-12:]] if error else [],
        'tv': {k: tv_info[k] for k in ('modelName', 'firmwareVersion', 'sdkVersion') if tv_info and k in tv_info},
        'privacy': 'No addresses, SSH identities, exception text, credentials, app inventory, environment or raw TV logs are collected.',
    }
    if isinstance(error, TVConnectionError):
        report['connection'] = {'protocol': 'ssap', 'close_code': error.close_code, 'reason_code': error.reason_code}
    if isinstance(error, DeveloperKeyError):
        report['connection'] = {'protocol': 'developer-key', 'reason_code': error.reason_code}
    if isinstance(error, TVCommandError):
        report['ssh_command'] = {'exit_status': error.exit_status}
        for key, allowed in (('root_action', ('inspect','install','status','remove')),
                             ('root_boundary', ('coordinator-stage','python-select','driver'))):
            value = getattr(error, key, None)
            if isinstance(value, str) and value in allowed:
                report['ssh_command'][key] = value
        recovery = root_recovery_details(getattr(error, 'root_recovery', None))
        if recovery: report['root_recovery'] = recovery
    if isinstance(error, TVRejected):
        report['luna'] = error.luna
    if isinstance(error, PythonCacheError):
        report['python_cache'] = {'reason': PythonCacheError(error.reason).reason}
    if isinstance(error, PythonPreflightError):
        safe = PythonPreflightError(error.reason, error.available_kib, error.required_kib, error.wam_session_kib)
        report['python_runtime'] = {'reason': safe.reason}
        report['python_runtime'].update({key: getattr(safe, key) for key in
            ('available_kib', 'required_kib', 'wam_session_kib') if getattr(safe, key) is not None})
    if tv_info and isinstance(tv_info.get('root_requirements'), dict):
        checks = tv_info['root_requirements']
        report['tv']['root_requirements'] = {
            name: checks[name] if checks[name] in ('pass', 'fail', 'unknown') else 'unknown'
            for name in ROOT_REQUIREMENTS if name in checks}
    for name, allowed in (('helper_state', ('running', 'stopped', 'stale', 'uncertain')),
                          ('kernel_arch', KERNEL_ARCHES),
                          ('userland_abi', ('arm32', 'arm64', 'other', 'unknown'))):
        if tv_info and name in tv_info:
            report['tv'][name] = tv_info[name] if tv_info[name] in allowed else 'unknown'
    if tv_info and type(tv_info.get('arm32_supported')) is bool:
        report['tv']['arm32_supported'] = tv_info['arm32_supported']
    path = store.root / 'reports' / ('diagnostic-' + uuid.uuid4().hex[:12] + '.json')
    private_write(path, json.dumps(report, indent=2).encode())
    return path


def suggest_issue(write, store, action, profile, phase, error, tv_info=None):
    write = console(write)
    write.heading('Need help? Open an issue')
    write(ISSUE_URL)
    try:
        path = create_report(store, action, profile, phase, error, tv_info)
        write.heading('Attach this diagnostic report')
        write.report(path)
    except (OSError, ValueError):
        write.error('Could not save a diagnostic file. Include cytv ' + __version__ + ', your desktop OS, edition and failed step: ' + phase + '.')
    write('')
    write('Include your steps, expected/actual result and TV model/firmware.')
    write('Review the report. Do not attach keys or your profile folder.')


def collect_home_report(remote, store, profile, write):
    """One bounded observation window, exported without raw logs or credentials."""
    if profile['edition'] != 'no-root':
        raise UserError('Home Helper diagnostics is available for No-root installations.')
    session = uuid.uuid4().hex
    directory = '/media/developer/apps/usr/palm/applications/com.local.nativehome/state'
    def command(name):
        remote.upload(directory + '/control.json',
                      json.dumps({'cmd': name, 'nonce': session}).encode(), mode=0o640)
    records = []
    triggers = {'started', 'sample', 'home', 'launch-request', 'launch-result',
                'launch-timeout', 'foreground', 'monitor', 'monitor-reset', 'expired', 'stopped'}
    monitors = {'starting', 'reset', 'screen-watch-connected', 'screen-watch-unavailable',
                'screen-watch-error', 'screen-watch-disconnected'}
    started = complete = announced = False
    beginning = time.monotonic()
    try:
        command('diagnostics-start')
        while True:
            raw = remote.run('tail -c 262144 ' + directory + '/controller.log')
            records = []
            for line in raw.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(item, dict) or item.get('event') != 'home-diagnostic' or item.get('session') != session or not isinstance(item.get('trigger'), str) or item['trigger'] not in triggers:
                    continue
                clean = {'trigger': item['trigger']}
                for name in ('time', 'homeSequence', 'sinceHomeMs', 'foregroundAgeMs', 'launchSequence', 'durationMs'):
                    value = item.get(name)
                    if value is None or type(value) is int and 0 <= value <= 10**15:
                        clean[name] = value
                for name in ('ready', 'enabled', 'launching', 'visitingLG', 'returnValue'):
                    if type(item.get(name)) is bool:
                        clean[name] = item[name]
                for name in ('foreground', 'id'):
                    value = item.get(name)
                    if value is None or isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9_.-]{0,256}', value):
                        clean[name] = value
                if isinstance(item.get('monitor'), str) and item['monitor'] in monitors:
                    clean['monitor'] = item['monitor']
                if item.get('monitorReason') in (None, 'state-permissions', 'missing-pairing-key', 'pairing-required'):
                    clean['monitorReason'] = item.get('monitorReason')
                clean['foregroundSource'] = 'subscription-cache'
                records.append(clean)
            started = started or any(r['trigger'] == 'started' for r in records)
            complete = any(r['trigger'] == 'expired' for r in records)
            elapsed = time.monotonic() - beginning
            if not started and elapsed >= 5:
                raise UserError('Helper did not start diagnostics. Update to a release containing diagnostics and start Helper in Home settings, then try again.')
            if complete or elapsed >= 70:
                break
            if started and not announced:
                announced = True
                write('Press Home once on the TV remote. Leave the remote untouched while the report is collected.')
            time.sleep(2)
    finally:
        try:
            command('diagnostics-stop')
        except Exception:
            pass  # The Helper also expires its own window after 60 seconds.
    path = create_report(store, 'home-diagnostics', profile, 'home-diagnostics-complete')
    report = json.loads(path.read_text())
    report['helper_diagnostics'] = {'schema': 1, 'complete': complete, 'records': records}
    report['privacy'] = 'Contains observed application IDs, routing state and timing. No addresses, keys, app inventory or raw TV logs are collected.'
    private_write(path, json.dumps(report, indent=2).encode())
    return path

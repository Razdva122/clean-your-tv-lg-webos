"""Issue-ready diagnostics built from allowlisted metadata, never raw logs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import traceback
import time
import re
import uuid

from . import __version__, diagnostic_context as context
from .state import private_write
from .terminal import console
from .errors import TVConnectionError, DeveloperKeyError, UserError, TVCommandError, TVRejected, PythonPreflightError, PythonCacheError, root_recovery_details

ISSUE_URL = 'https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new'
KERNEL_ARCHES = context.KERNEL_ARCHES
ROOT_REQUIREMENTS = context.ROOT_REQUIREMENTS


def create_report(store, action, profile, phase, error=None, tv_info=None, *, checks=None, status=None):
    pending = store.diagnostic_pending if hasattr(store, 'diagnostic_pending') else store.pending(profile) if profile else None
    report = {
        'schema': 1, 'cytv_version': __version__,
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'desktop': {'os': platform.system(), 'architecture': platform.machine(), 'python': platform.python_version()},
        'frontend': context.choice(context.mapping(tv_info).get('frontend'),('console','desktop','android')),
        'action': action, 'edition': profile.get('edition') if profile else None,
        'phase': phase,
        'error_type': type(error).__name__ if error else None,
        'pending': {'action': context.choice(pending.get('action'), (*context.ACTIONS, 'activate-root', 'setup-root-updater', 'archive-root-state')),
                    'stage': context.choice(pending.get('stage'), (*context.STAGES, 'enable', 'setup', 'verify', 'upload', 'removing', 'stop-helper'))} if pending else None,
        'trace': [{'file': Path(frame.filename).name, 'function': frame.name, 'line': frame.lineno}
                  for frame in traceback.extract_tb(error.__traceback__)[-12:]] if error else [],
        'tv': context.tv_summary(tv_info),
        'checks': context.checks_summary(checks),
        'privacy': 'No addresses, SSH identities, exception text, credentials, app inventory, environment or raw TV logs are collected.',
    }
    if profile:
        if profile.get('root_variant') == 'node012-beta':
            report['root_variant'] = 'node012-beta'
        if profile.get('connection') == 'root-ssh':
            report['connection_mode'] = 'root-ssh'
    from .recovery_state import assess, summary
    if pending and pending.get('activation_restore') in ('verified', 'unverified'):
        report['activation_recovery'] = {'lg_home':pending['activation_restore'],
                                         'retry_required':pending.get('activation_restore_pending') is True}
    report['recovery'] = {**summary(profile or {}, pending), **assess(profile, pending, status)}
    removal=pending or (getattr(store,'diagnostic_removal',None) if action in ('uninstall','recover') else None)
    if removal and removal.get('recovery_protocol')=='clean-removal-v1':
        from .recovery_state import removal_summary
        report['removal']=removal_summary(removal)
    from .failure_help import for_error, report_summary, network_failure_causes
    help = for_error(error, phase, profile, pending)
    if help:
        report['guidance'] = report_summary(help)
    reason = getattr(error, 'reason_code', 'unknown')
    if isinstance(error, TVCommandError):
        reason = 'ssh-command-failed'
    elif type(error).__name__ in ('NoValidConnectionsError', 'AuthenticationException', 'BadHostKeyException', 'ImportError'):
        reason = {'NoValidConnectionsError': 'ssh-unreachable', 'AuthenticationException': 'ssh-authentication',
                  'BadHostKeyException': 'ssh-identity-changed', 'ImportError': 'host-runtime'}[type(error).__name__]
    if phase == 'ssh-connect' and help and help['code'] in ('ssh-unreachable', 'ssh-access-denied', 'ssh-refused', 'ssh-timeout'):
        reason = help['code']
        report['connection'] = {'protocol': 'ssh', 'causes': network_failure_causes(error)}
    report['reason_code'] = context.choice(reason, context.REASONS)
    if status is not None:
        report['status'] = context.status_summary(status)
    if isinstance(error, TVConnectionError):
        report['connection'] = {'protocol': 'ssap', 'close_code': error.close_code, 'reason_code': error.reason_code}
    if isinstance(error, DeveloperKeyError):
        report['connection'] = {'protocol': 'developer-key', 'reason_code': error.reason_code}
    if isinstance(error, TVCommandError):
        report['ssh_command'] = {'exit_status': error.exit_status}
        for key, allowed in (('root_action', context.ROOT_ACTIONS),
                             ('root_boundary', ('coordinator-stage','python-select','driver'))):
            value = getattr(error, key, None)
            if isinstance(value, str) and value in allowed:
                report['ssh_command'][key] = value
        recovery = root_recovery_details(getattr(error, 'root_recovery', None))
        if recovery: report['root_recovery'] = recovery
    if hasattr(error, 'no_root_observer'):
        report['no_root_observer'] = getattr(error, 'no_root_observer')
    if hasattr(error, 'local_recovery'):
        from .errors import local_recovery_details
        report['local_recovery'] = local_recovery_details(error.local_recovery)
    if isinstance(error, TVRejected):
        report['luna'] = error.luna
    if isinstance(error, PythonCacheError):
        report['python_cache'] = {'reason': PythonCacheError(error.reason).reason}
    if isinstance(error, PythonPreflightError):
        safe = PythonPreflightError(error.reason, error.available_kib, error.required_kib, error.wam_session_kib)
        report['python_runtime'] = {'reason': safe.reason}
        report['python_runtime'].update({key: getattr(safe, key) for key in
            ('available_kib', 'required_kib', 'wam_session_kib') if getattr(safe, key) is not None})
    if error is not None:
        safe_error = context.failure_summary(report)
        for key in ('luna', 'connection', 'ssh_command', 'python_cache', 'python_runtime', 'root_recovery', 'no_root_observer', 'local_recovery'):
            if key in report:
                report[key] = safe_error.get(key, {})
    report.update(context.history(report, store, profile, error, removal or pending))
    if error is not None and action in ('recover', 'status', 'doctor'):
        report['observation_failure'] = context.failure_summary(report)
    path = store.root / 'reports' / ('diagnostic-' + uuid.uuid4().hex[:12] + '.json')
    private_write(path, json.dumps(report, indent=2).encode())
    return path


def save_result(write, store, action, profile, phase, tv_info=None, *, checks=None, status=None):
    """A failed optional export must not turn successful device work into failure."""
    write = console(write)
    try:
        path = create_report(store, action, profile, phase, tv_info=tv_info, checks=checks, status=status)
        write.report(path)
        return path
    except (OSError, ValueError, TypeError):
        write.error('Could not save a diagnostic file. Include cytv ' + __version__ + ', your desktop OS, edition and failed step: ' + phase + '.')
        return None


def suggest_issue(write, store, action, profile, phase, error, tv_info=None, *, checks=None, status=None):
    write = console(write)
    write.heading('Need help? Open an issue')
    write(ISSUE_URL)
    try:
        path = create_report(store, action, profile, phase, error, tv_info, checks=checks, status=status)
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

"""Issue-ready diagnostics built from allowlisted metadata, never raw logs."""
from datetime import datetime, timezone
import errno
import json
from pathlib import Path
import platform
import traceback
import time
import re
import uuid
from urllib.parse import urlencode

from . import __version__, debloat, diagnostic_context as context
from .state import private_write
from .terminal import console
from .errors import TVConnectionError, DeveloperKeyError, UserError, TVCommandError, TVRejected, PythonPreflightError, PythonCacheError, connection_interrupted, root_recovery_details

ISSUE_URL = 'https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new?template=cytv.yml'
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
        'pending': {'action': context.choice(pending.get('action'), context.PENDING_ACTIONS),
                    'stage': context.choice(pending.get('stage'), (*context.STAGES, 'enable', 'setup', 'verify', 'upload', 'removing', 'stop-helper'))} if pending else None,
        'trace': [{'file': Path(frame.filename).name, 'function': frame.name, 'line': frame.lineno}
                  for frame in traceback.extract_tb(error.__traceback__)[-12:]] if error else [],
        'tv': context.tv_summary(tv_info),
        'checks': context.checks_summary(checks),
        'privacy': 'No addresses, SSH identities, exception text, credentials, app inventory, environment or raw TV logs are collected.',
    }
    if action in ('install', 'debloat'):
        events = context.mapping(context.mapping(tv_info).get('debloat'))
        results = {key: context.choice(events.get(key), debloat.DIAGNOSTIC_RESULTS, None)
                   for key in debloat.SETTINGS}
        results = {key: outcome for key, outcome in results.items() if outcome is not None}
        if results:
            report['debloat'] = results
    if profile:
        if profile.get('root_variant') == 'node012-beta':
            report['root_variant'] = 'node012-beta'
        if profile.get('connection') == 'root-ssh':
            report['connection_mode'] = 'root-ssh'
    from .recovery_state import assess, summary
    if pending and pending.get('activation_restore') in ('verified', 'unverified'):
        report['activation_recovery'] = {'lg_home':pending['activation_restore'],
                                         'retry_required':pending.get('activation_restore_pending') is True}
    partial = context.mapping(tv_info).get('partial_profile_observation') is True
    removal = None
    if profile and not partial:
        report['recovery'] = {**summary(profile, pending), **assess(profile, pending, status)}
        removal = pending or (getattr(store, 'diagnostic_removal', None)
                              if action in ('uninstall', 'recover') else None)
    if removal and removal.get('recovery_protocol')=='clean-removal-v1':
        from .recovery_state import removal_summary
        report['removal']=removal_summary(removal)
    from .failure_help import for_error, report_summary, network_failure_causes
    help = for_error(error, phase, profile, pending)
    if help:
        report['guidance'] = report_summary(help)
    reason = getattr(error, 'reason_code', 'unknown')
    if isinstance(error, TVCommandError):
        reason = error.diagnostic_reason
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
        report['ssh_command'] = {}
        if error.exit_status != -1:
            report['ssh_command']['exit_status'] = error.exit_status
        for key, allowed in context.ROOT_COMMAND_DETAILS:
            value = getattr(error, key, None)
            if isinstance(value, str) and value in allowed:
                report['ssh_command'][key] = value
        recovery = root_recovery_details(getattr(error, 'root_recovery', None))
        if recovery: report['root_recovery'] = recovery
        from .errors import root_driver_details
        driver=root_driver_details(getattr(error,'root_driver',None))
        if driver:report['root_driver']=driver
    from .errors import root_beta_repair_details
    beta_repair = root_beta_repair_details(getattr(error, 'root_beta_repair_failure', None))
    if beta_repair:
        report['root_beta_repair_failure'] = beta_repair
    if action == phase == 'home-diagnostics':
        stage = context.choice(getattr(error, 'home_diagnostic_stage', None),
                               ('start-upload', 'log-read', 'start-unacknowledged'), None)
        if stage:
            report['helper_diagnostics'] = {'failure_stage': stage}
            if stage == 'start-upload':
                report['helper_diagnostics']['state_directory'] = context.choice(
                    getattr(error, 'home_diagnostic_directory', None),
                    ('unavailable', 'access-denied', 'access-available'))
    if hasattr(error, 'no_root_cleanup'):
        from .errors import no_root_cleanup_details
        report['no_root_cleanup'] = no_root_cleanup_details(error.no_root_cleanup)
    if hasattr(error, 'no_root_observer'):
        report['no_root_observer'] = getattr(error, 'no_root_observer')
    if hasattr(error, 'removal_binding'):
        report['removal_binding'] = context.removal_binding_summary(error.removal_binding)
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
        for key in ('luna', 'connection', 'ssh_command', 'python_cache', 'python_runtime', 'root_recovery', 'root_driver', 'no_root_observer', 'no_root_cleanup', 'local_recovery', 'removal_binding'):
            if key in report:
                report[key] = safe_error.get(key, {})
    from .contract_events import merge_events
    from .recovery_state import observation_diagnostics
    report['contract_events'] = merge_events(getattr(error, 'contract_events', []),
        getattr(store, 'contract_events', []), context.mapping(tv_info).get('contract_events', []),
        observation_diagnostics(status))
    report['contract_telemetry'] = context.choice(context.mapping(tv_info).get('contract_telemetry'),
        ('read', 'legacy', 'unavailable'), 'unavailable')
    report.update(context.history(report, store, profile, error, removal or pending, create=not partial))
    if error is not None and action in ('recover', 'status', 'doctor'):
        report['observation_failure'] = context.failure_summary(report)
    # One report-wide first-cause + recent window, including retained and optional
    # observation records. History on disk retains its full original projection.
    containers = [context.mapping(report.get('first_failure')),
                  context.mapping(report.get('previous_attempt_failure')),
                  *report.get('intermediate_failures', []), report,
                  context.mapping(report.get('observation_failure'))]
    # Reconcile counts only inside the current operation above. Retained records
    # own their count/timestamps; equal violation identity is not equal evidence
    # from another operation. Exact copies still occupy one exported location.
    from .contract_events import export_events
    selected = []
    for item in containers:
        for event in export_events(item.get('contract_events', [])):
            if event not in selected:
                selected.append(event)
                while (len(selected) > 32 or
                       len(json.dumps(selected, separators=(',', ':')).encode()) > 16200):
                    del selected[1]
    for item in containers:
        if 'contract_events' not in item: continue
        own = []
        for event in item['contract_events']:
            if event in selected:
                own.append(event)
                selected.remove(event)
        item['contract_events'] = own
    path = store.root / 'reports' / ('diagnostic-' + uuid.uuid4().hex[:12] + '.json')
    private_write(path, json.dumps(report, indent=2).encode())
    return path


def issue_draft(report):
    """Return a title and editable plain text from a local diagnostic export."""
    summary = context.issue_summary(report)
    edition = {'no-root': 'No-root', 'root': 'Root'}.get(summary['edition'], 'unknown')
    goal, phase, reason = (summary[key] for key in ('goal', 'phase', 'reason'))
    subject = goal.replace('-', ' ') if goal != 'unknown' else 'Installer'
    if edition != 'unknown':
        subject = edition + ' ' + subject
    detail = phase if phase not in (goal, 'unknown') else reason
    if detail != 'unknown':
        subject += ': ' + detail.replace('-', ' ').replace('_', ' ').lower()
        if reason not in (detail, 'unknown'):
            subject += ' (' + reason.replace('-', ' ').replace('_', ' ').lower() + ')'

    phase_label = 'Previous attempt phase' if summary['previous_attempt'] else 'Observed phase'
    lines = [
        'Goal: ' + goal,
        'Edition: ' + edition,
        'Installer version: ' + (summary['version'] or 'unknown'),
        phase_label + ': ' + phase,
        'Reason: ' + reason,
        'Last verified outcome: ' + summary['outcome'],
    ]
    for label, item in (('Earlier failure', summary['earlier']), ('Later observation', summary['later'])):
        if item:
            observation = item['action'] + ' at ' + item['phase']
            if item['reason'] != 'unknown':
                observation += ' (' + item['reason'] + ')'
            lines.append(label + ': ' + observation)
    return {'title': '[cytv] ' + subject, 'body': '\n'.join(lines)}


def load_issue_draft(path, action):
    if path is not None:
        try:
            return issue_draft(json.loads(path.read_text(encoding='utf-8')))
        except (OSError, ValueError, RecursionError):
            pass
    return issue_draft({'action': action})


def issue_url(title):
    return ISSUE_URL + '&' + urlencode({'title': title})


def observe_root_python_inventory(remote, profile, tv_info):
    if profile and profile.get('edition') == 'root':
        from .root_passive import collect_runtime_inventory
        tv_info['root_python_inventory'] = collect_runtime_inventory(remote)


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


def suggest_issue(write, store, action, profile, phase, error, tv_info=None, *, checks=None, status=None, ask=None):
    write = console(write)
    console_issue = write.frontend == 'console'
    if not console_issue:
        write.heading('Need help? Open an issue')
        write(ISSUE_URL)
    path = None
    try:
        path = create_report(store, action, profile, phase, error, tv_info, checks=checks, status=status)
        write.heading('Attach this diagnostic report')
        write.report(path)
    except (OSError, ValueError):
        write.error('Could not save a diagnostic file. Include cytv ' + __version__ + ', your desktop OS, edition and failed step: ' + phase + '.')
        if console_issue:
            write('Include the visible error when opening an issue.')
    write('')
    write('Include your steps, expected/actual result and TV model/firmware.')
    if console_issue:
        write.issue(load_issue_draft(path, action), ask=ask)


def _observe_home_diagnostic_directory(remote, directory):
    """Check directory access after a failed upload without writing a test file."""
    try:
        return remote.run(
            f'if [ ! -d "{directory}" ]; then printf unavailable; '
            f'elif [ ! -w "{directory}" ] || [ ! -x "{directory}" ]; then printf access-denied; '
            'else printf access-available; fi', timeout=5).strip()
    except Exception:
        return None  # Keep the original upload failure if this probe also fails.


def collect_home_report(remote, store, profile, write, *, reconnect=None, ask=None):
    """One bounded observation window, exported without raw logs or credentials."""
    from .outcomes import HOME_PRESS, HOME_RESULTS, ask_home_result, home_result_fields

    if profile['edition'] != 'no-root':
        raise UserError('Home Helper diagnostics is available for No-root installations.')
    session = uuid.uuid4().hex
    directory = '/media/developer/apps/usr/palm/applications/com.local.nativehome/state'
    def command(name):
        request = {'cmd': name, 'nonce': session}
        if name == 'diagnostics-start':
            request['durationMs'] = 180000
        remote.upload(directory + '/control.json',
                      json.dumps(request).encode(), mode=0o640)
    log = directory + '/controller.log'
    read_log = (
        f'if [ -f {log}.previous ]; then tail -c 131072 {log}.previous || exit; fi; '
        f'tail -c 131072 {log}'
    )
    records = {}
    triggers = {'started', 'resumed', 'power', 'sample', 'home', 'launch-request', 'launch-result',
                'launch-timeout', 'foreground', 'monitor', 'monitor-reset', 'expired', 'stopped'}
    monitors = {'starting', 'reset', 'screen-watch-connected', 'screen-watch-unavailable',
                'screen-watch-error', 'screen-watch-disconnected'}
    started = complete = announced = False
    beginning = time.monotonic()
    wait_until = 190
    read_count = reconnect_count = 0
    failure_stage = 'start-upload'
    try:
        command('diagnostics-start')
        while True:
            failure_stage = 'log-read'
            try:
                if remote is None:
                    reconnect_count += 1
                    remote = reconnect()
                raw = remote.run(read_log)
                read_count += 1
            except Exception as error:
                if reconnect is None or not (connection_interrupted(error)
                        or isinstance(error, EOFError)
                        or getattr(error, 'errno', None) in (errno.ENETDOWN, errno.ENETUNREACH)
                        or getattr(error, 'reason_code', None) in ('ssh-exit-status-missing', 'operation-timeout')):
                    raise
                # Helper records to disk while SSH is unavailable. Reuse the
                # original nonce and never start a second recording.
                remote = None
                if time.monotonic() - beginning < wait_until - 2:
                    time.sleep(2)
                    if time.monotonic() - beginning < wait_until:
                        continue
                if not started:
                    raise
                write('TV connection was interrupted. Saving an incomplete Home button diagnostic report.')
                break
            failure_stage = None
            for line in raw.splitlines():
                if line in records:
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(item, dict) or item.get('event') != 'home-diagnostic' or item.get('session') != session or not isinstance(item.get('trigger'), str) or item['trigger'] not in triggers:
                    continue
                clean = {'trigger': item['trigger']}
                for name in ('time', 'homeSequence', 'sinceHomeMs', 'foregroundAgeMs', 'launchSequence', 'durationMs', 'controllerPid'):
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
                if item.get('powerState') in ('Active', 'Suspend', 'Active Standby',
                        'Request Power Off', 'Prepare Power Off', 'Request Suspend',
                        'Request Active Standby', 'Prepare Active Standby'):
                    clean['powerState'] = item['powerState']
                clean['foregroundSource'] = 'subscription-cache'
                records[line] = clean
                started = started or clean['trigger'] in ('started', 'resumed')
                complete = complete or clean['trigger'] == 'expired'
            elapsed = time.monotonic() - beginning
            if not started and elapsed >= 5:
                failure_stage = 'start-unacknowledged'
                raise UserError('Helper did not start diagnostics. Update to a release containing diagnostics and start Helper in Home settings, then try again.')
            if complete or elapsed >= wait_until:
                break
            if started and not announced:
                announced = True
                write(HOME_PRESS)
                write('Leave the remote untouched while the report is collected.')
            time.sleep(2)
    except Exception as error:
        if failure_stage:
            error.home_diagnostic_stage = failure_stage
        if failure_stage == 'start-upload' and isinstance(error, TVCommandError):
            error.home_diagnostic_directory = _observe_home_diagnostic_directory(remote, directory)
        raise
    finally:
        if remote is not None:
            try:
                command('diagnostics-stop')
            except Exception:
                pass  # Helper expires the bounded request even if SSH remains unavailable.
    elapsed_ms = int((time.monotonic() - beginning) * 1000)
    destination = None
    if announced and ask is not None:
        destination = ask_home_result(ask, write)
        write(HOME_RESULTS[destination][3])
    path = create_report(store, 'home-diagnostics', profile, 'home-diagnostics-complete')
    report = json.loads(path.read_text())
    report['helper_diagnostics'] = {'schema': 1, 'complete': complete, 'records': list(records.values()),
                                    **home_result_fields(destination)}
    report['helper_diagnostics']['connection'] = {
        'successful_reads': read_count, 'reconnect_attempts': reconnect_count,
        'elapsed_ms': elapsed_ms
    }
    if failure_stage:
        report['helper_diagnostics']['failure_stage'] = failure_stage
    report['privacy'] = 'Contains observed application IDs, routing state and timing. No addresses, keys, app inventory or raw TV logs are collected.'
    private_write(path, json.dumps(report, indent=2).encode())
    return path

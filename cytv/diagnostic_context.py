"""Small, revalidated diagnostic projections. Never recovery authority."""
from contextlib import contextmanager
import json
import os
import re
import stat

from .state import private_write, sync_directory
from .errors import LUNA_STATES, PACKAGE_FAILURE_REASONS

KERNEL_ARCHES = ('armv7l', 'armv7', 'armv8l', 'aarch64', 'arm64', 'x86_64', 'i686', 'unknown')
ROOT_REQUIREMENTS = ('root-user', 'python3', 'luna-send', 'apps-directory',
                     'luna-services-directory', 'python-json', 'python-fcntl', 'python-version', 'node-version')

ROOT_ACTIONS = ('inspect', 'install', 'status', 'remove', 'enable', 'restore', 'uninstall')

REASONS = ('unknown', 'user-error', 'ssh-command-failed', 'ssh-unreachable',
           'ssh-authentication', 'ssh-identity-changed', 'ssh-trust-record', 'ssh-identity-unverified', 'host-runtime',
           'helper-running', 'helper-state-unverified', 'root-requirements',
           'pending-operation', 'root-operation-unconfirmed', 'version-mismatch',
           'inventory-unavailable', 'graphics-unverified', 'root-home-interfaces')
ACTIONS = ('recover', 'install', 'uninstall', 'restore', 'status', 'doctor', 'home-diagnostics',
           'enable-system-updates', 'enable-firmware-access', 'disable-firmware-access',
           'recover-system-rollback', 'replace-system-updater', 'clean-wam-cache')
PHASES = ('launch-helper', 'verify-home-button', 'select-tv', 'inspect-tv', 'select-edition', 'prepare-payload', 'ssh-connect',
          'inspect-installation', 'pair-tv', 'read-inventory', 'install-packages',
          'install-helper', 'install-home', 'configure-helper', 'install-root',
          'install-root-updater', 'verify-root-updater', 'verify-root-recovery',
          'stop-old-helper', 'activate-root', 'launch-root', 'remove-existing-root',
          'archive-root-state', 'doctor-complete', 'install-complete', 'preflight',
          'prepare-python-runtime', *ACTIONS)
STATES = ('pending', 'complete', 'recovery_required', 'unknown', 'fresh', 'installed',
          'unsupported', 'conflict', 'migration_required')
STAGES = ('unknown', 'blocked', 'reserved', 'root-deploy', 'root-updater', 'supervisor',
          'readback', 'complete', 'absent', 'incomplete-state', 'installed-recovery-only',
          'uninstalled-state-retained', 'pending', 'coordinator-upload', 'coordinator-submitted')
CODES = ('unknown_operation', 'operation_pending', 'verified', 'installation_requires_recovery',
         'operation_requires_recovery', 'recovery_evidence_required', 'continuation_requires_recovery',
         'historical_completion_is_not_current')
COMPONENTS = {'com.gathin.tvhome': 'home', 'com.local.nativehome': 'helper',
              'com.cleanyourtv.root.preview': 'root', 'com.cleanyourtv.root.updater': 'root_updater',
              'com.cleanyourtv.system.updater': 'system_updater'}
HELPER_STATES = ('running', 'stopped', 'stale', 'uncertain', 'unknown')


def choice(value, allowed, default='unknown'):
    return value if type(value) is str and value in allowed else default


def mapping(value):
    return value if type(value) is dict else {}


def version(value):
    return value if type(value) is str and re.fullmatch(r'\d{1,5}(?:\.\d{1,5}){1,2}(?:-\d{1,6})?', value) else None


def metadata(value):
    value = mapping(value)
    result = {}
    model = value.get('modelName')
    if type(model) is str and re.fullmatch(r'(?=.*\d)(?=.*[A-Z])[A-Z0-9][A-Z0-9._-]{1,47}', model):
        result['modelName'] = model
    for key in ('sdkVersion', 'firmwareVersion'):
        if version(value.get(key)):
            result[key] = value[key]
    return result


def root_diagnostics_summary(value):
    value=mapping(value);result={}
    if version(value.get('runtime_release')):result['runtime_release']=value['runtime_release']
    result['components']={key:item for key,item in mapping(value.get('components')).items()
                          if key in ('root','root_updater','system_updater') and version(item)}
    result['component_reads']={key:choice(item,('read','missing','unsafe','unavailable'))
        for key,item in mapping(value.get('component_reads')).items() if key in ('root','root_updater','system_updater')}
    log=mapping(value.get('health_log'))
    result['health_log']={'status':choice(log.get('status'),('read','missing','unsafe','unavailable'))}
    if 'scope' in log:
        result['health_log']['scope']=choice(log['scope'],('historical-tail','since-enable'))
    if 'health_refusal' in log:
        result['health_log']['health_refusal']=choice(log['health_refusal'],('generic','transaction-mismatch',
            'binding-restored','generation-mismatch','token-mismatch','boot-mismatch','phase-inactive','failsafe-present'))
    if type(log.get('supervisor_error')) is bool:result['health_log']['supervisor_error']=log['supervisor_error']
    return result


def tv_summary(value):
    value = mapping(value)
    result = metadata(value)
    if 'root_diagnostics' in value:
        result['root_diagnostics'] = root_diagnostics_summary(value['root_diagnostics'])
    if 'setup_outcome' in value:
        from .outcomes import summary
        result['setup_outcome'] = summary(value['setup_outcome'])
    for key, allowed in (('helper_state', HELPER_STATES), ('kernel_arch', KERNEL_ARCHES),
                         ('userland_abi', ('arm32', 'arm64', 'other', 'unknown')),
                         ('graphics_resolution', ('1280x720', '1920x1080'))):
        if key in value:
            result[key] = choice(value[key], allowed)
    if type(value.get('arm32_supported')) is bool:
        result['arm32_supported'] = value['arm32_supported']
    if value.get('home_backend') in ('system-profile', 'c1-native-gate'):
        result['home_backend'] = value['home_backend']
    if 'root_requirements' in value:
        checks = mapping(value['root_requirements'])
        from .root_capabilities import CALLS
        result['root_requirements'] = {key: choice(checks[key], ('pass', 'fail', 'unknown'))
                                       for key in (*ROOT_REQUIREMENTS,*CALLS) if key in checks}
    if 'root_capabilities' in value:
        from .root_capabilities import CALLS, REASONS
        result['root_capabilities'] = {key: choice(mapping(value['root_capabilities']).get(key), REASONS) for key in CALLS}
    if 'root_capability_codes' in value:
        from .root_capabilities import CALLS
        codes = mapping(value['root_capability_codes'])
        result['root_capability_codes'] = {key: codes[key] for key in CALLS
            if type(codes.get(key)) is int and -(2**31)<=codes[key]<2**31}
    if 'components' in value:
        result['components'] = {key: item for key, item in mapping(value['components']).items()
                                 if key in COMPONENTS.values() and version(item)}
    return result


def collect_metadata(remote, info):
    # Existing read-only system-property endpoint; failure never blocks setup.
    from .graphics import URI
    try:
        reply = remote.luna(URI, {'keys': ['modelName', 'firmwareVersion', 'sdkVersion']}, timeout=5)
        if mapping(reply).get('returnValue') is True:
            info.update(metadata(reply))
    except Exception:
        pass


def checks_summary(value):
    from .checks import LABELS, STATUS
    return {key: choice(mapping(item).get('status'), STATUS) for key, item in mapping(value).items() if key in LABELS}


def worker_summary(value):
    value = mapping(value)
    result = {'exception_type': choice(value.get('exception_type'),
              ('CalledProcessError', 'TimeoutExpired', 'ValueError', 'RuntimeError', 'OSError',
               'PermissionError', 'FileNotFoundError', 'TypeError', 'KeyError'))}
    for key, low, high in (('exit_status', -255, 255), ('errno', 0, 4095)):
        item = value.get(key)
        if type(item) is int and low <= item <= high:
            result[key] = item
    return result


def product_summary(value):
    value = mapping(value)
    result = {key: choice(value[key], allowed) for key, allowed in
              (('state', STATES), ('stage', STAGES), ('code', CODES)) if key in value}
    if 'failure' in value:
        result['failure'] = worker_summary(value['failure'])
    if 'passive' in value:
        passive=mapping(value['passive'])
        result['passive']={'schema':1,**{key:choice(passive[key],allowed) for key,allowed in (
            ('status',('read','missing','unsafe','inconsistent','unavailable')),
            ('operation',('consistent-not-admission',)),('worker',('unclassified','exception-recorded')),
            ('python',('system-default-unverified','private-bytes-match-unexecuted'))) if key in passive}}
    for key in ('home_changed', 'current', 'can_resume', 'verified'):
        if type(value.get(key)) is bool:
            result[key] = value[key]
    return result


def status_summary(value):
    value = mapping(value)
    device = mapping(value.get('device', value))
    result = {}
    if 'assessment' in value:
        from .recovery_state import assessment_summary
        result['assessment'] = assessment_summary(value['assessment'])
    components = {key: item for key, item in mapping(value.get('components')).items()
                  if key in COMPONENTS.values() and version(item)}
    if 'components' in value:
        result['components'] = components
    apps = device.get('apps')
    if type(apps) is list:
        for app in apps[:4096]:
            app = mapping(app)
            name = COMPONENTS.get(app.get('id')) if type(app.get('id')) is str else None
            if name and version(app.get('version')):
                components[name] = app['version']
        result['components'] = components
    if 'observation_phase' in value:
        result['observation_phase']=choice(value['observation_phase'],('before-enable',))
    if 'helper_state' in device:
        result['helper_state'] = choice(device['helper_state'], HELPER_STATES)
    if 'product' in device:
        result['product'] = product_summary(device['product'])
    if 'deployment_stage' in value or 'deployment_stage' in device:
        result['deployment_stage'] = choice(value.get('deployment_stage', device.get('deployment_stage')), STAGES)
    if type(value.get('can_resume_root_setup')) is bool:
        result['can_resume_root_setup'] = value['can_resume_root_setup']
    updater = mapping(device.get('system_updater'))
    if updater:
        result['system_updater'] = {key: updater[key] for key in ('present', 'bootstrap_complete', 'disabled') if type(updater.get(key)) is bool}
    runtime = mapping(device.get('result', device))
    for key in ('guardian_active', 'journal_exists', 'recovery_integrity_verified', 'home_enabled'):
        if type(runtime.get(key)) is bool:
            result[key] = runtime[key]
    recovery = mapping(runtime.get('recovery'))
    if type(recovery.get('integrity_verified')) is bool:
        result['recovery_integrity_verified'] = recovery['integrity_verified']
    intent = mapping(runtime.get('intent'))
    if type(intent.get('enabled')) is bool:
        result['home_enabled'] = intent['enabled']
    return result


def failure_summary(value):
    """Revalidate persisted evidence too; no free-text fields cross this boundary."""
    value = mapping(value)
    result = {'action': choice(value.get('action'), ACTIONS),
              'phase': choice(value.get('phase'), PHASES),
              'reason_code': choice(value.get('reason_code'), REASONS)}
    error_types = ('RootCapabilityError', 'UserError', 'TVCommandError', 'TVRejected', 'PythonCacheError',
                   'PythonPreflightError', 'DeveloperKeyError', 'TVConnectionError',
                   'AuthenticationException', 'BadHostKeyException', 'NoValidConnectionsError',
                   'OSError', 'RuntimeError', 'ValueError', 'TimeoutError', 'Exception')
    result['error_type'] = choice(value.get('error_type'), error_types, 'Exception')
    if 'guidance' in value:
        from .failure_help import report_summary
        result['guidance'] = report_summary(value['guidance'])
    command = mapping(value.get('ssh_command'))
    if type(command.get('exit_status')) is int and -1 <= command['exit_status'] <= 255:
        result['ssh_command'] = {'exit_status': command['exit_status']}
    for key, allowed in (('root_action', ROOT_ACTIONS),
                         ('root_boundary', ('coordinator-stage', 'python-select', 'driver'))):
        if key in command and type(command[key]) is str and command[key] in allowed:
            result.setdefault('ssh_command', {})[key] = command[key]
    if 'tv' in value:
        result['tv'] = tv_summary(value['tv'])
    if version(value.get('cytv_version')):
        result['cytv_version'] = value['cytv_version']
    timestamp = value.get('timestamp_utc')
    if type(timestamp) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00', timestamp):
        result['timestamp_utc'] = timestamp
    luna = mapping(value.get('luna'))
    if luna:
        clean = {'operation': choice(luna.get('operation'), ('package-install', 'package-remove', 'package-status',
                  'helper-disable', 'eim-delete-device', 'application-launch', 'luna-call'), 'luna-call'),
                 'state': choice(luna.get('state'), LUNA_STATES)}
        if 'reason' in luna:
            clean['reason'] = choice(luna.get('reason'), PACKAGE_FAILURE_REASONS)
        for key in ('error_code', 'details_error_code', 'status_value'):
            item = luna.get(key)
            clean[key] = item if type(item) is int and -(2**31) <= item < 2**31 else None
        clean['return_value'] = luna.get('return_value') if type(luna.get('return_value')) is bool else None
        result['luna'] = clean
    from .errors import PythonCacheError, PythonPreflightError, DeveloperKeyError, TVConnectionError
    if 'python_cache' in value:
        result['python_cache'] = {'reason': PythonCacheError(mapping(value['python_cache']).get('reason')).reason}
    if 'python_runtime' in value:
        data = mapping(value['python_runtime'])
        safe = PythonPreflightError(data.get('reason'), data.get('available_kib'), data.get('required_kib'), data.get('wam_session_kib'))
        result['python_runtime'] = {'reason': safe.reason}
        result['python_runtime'].update({key: getattr(safe, key) for key in ('available_kib', 'required_kib', 'wam_session_kib') if getattr(safe, key) is not None})
    connection = mapping(value.get('connection'))
    if connection.get('protocol') == 'developer-key':
        result['connection'] = {'protocol': 'developer-key', 'reason_code': DeveloperKeyError('', connection.get('reason_code')).reason_code}
    elif connection.get('protocol') == 'ssap':
        code = connection.get('close_code')
        safe = TVConnectionError('', close_code=code if type(code) is int else None, reason_code=connection.get('reason_code'))
        result['connection'] = {'protocol': 'ssap', 'reason_code': safe.reason_code, 'close_code': safe.close_code}
    from .errors import root_recovery_details
    recovery = root_recovery_details(value.get('root_recovery'))
    if recovery:
        result['root_recovery'] = recovery
    if 'checks' in value:
        # Stored projections are id -> status, not UI events.
        result['checks'] = checks_summary({key: {'status': item} for key, item in mapping(value['checks']).items()})
    if 'status' in value:
        result['status'] = status_summary(value['status'])
    return result


def read_record(path):
    if path.is_symlink():
        raise ValueError('Indirect diagnostic record')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 65536:
            raise ValueError('Invalid diagnostic record')
        if os.name != 'nt' and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise ValueError('Untrusted diagnostic record')
        value = json.loads(stream.read(65537))
        if type(value) is not dict:
            raise ValueError('Invalid diagnostic record')
        return value


@contextmanager
def operation_context(store, profile):
    """Snapshot while the normal TV lock is held, before another session can start."""
    store.diagnostic_created = None
    try:
        yield
    finally:
        try:
            store.diagnostic_pending = store.pending(profile)
        except (OSError, ValueError):
            store.diagnostic_pending = {'action': 'unknown', 'stage': 'unknown'}


def history(report, store, profile, error, pending):
    result = {'first_failure': None, 'failure_history': 'not-recorded'}
    if not profile:
        return result
    try:
        directory = store.device_dir(profile) / 'diagnostic-failures'
        if directory.is_symlink():
            raise ValueError('Indirect diagnostic directory')
        directory.mkdir(mode=0o700, exist_ok=True)
        identifier = mapping(pending).get('diagnostic_id')
        if type(identifier) is str and re.fullmatch(r'[a-f0-9]{32}', identifier):
            path = directory / (identifier + '.json')
            if (error is not None and getattr(store, 'diagnostic_created', None) == identifier
                    and report['action'] == getattr(store, 'diagnostic_action', None)):
                try:
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    pass
                else:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(json.dumps(failure_summary(report)).encode())
                        stream.flush()
                        os.fsync(stream.fileno())
                    sync_directory(directory)
            if path.exists() or path.is_symlink():
                result['first_failure'] = failure_summary(read_record(path))
                result['failure_history'] = 'recorded'
        elif not pending:
            path = directory / 'previous-attempt.json'
            if error is not None and report['action'] == 'install':
                private_write(path, json.dumps(failure_summary(report)).encode())
            if path.exists() or path.is_symlink():
                result['previous_attempt_failure'] = failure_summary(read_record(path))
    except (OSError, ValueError, TypeError):
        result['failure_history'] = 'unavailable'
    return result


def clear_previous_attempt(store, profile):
    try:
        directory = store.device_dir(profile) / 'diagnostic-failures'
        if not directory.is_symlink():
            (directory / 'previous-attempt.json').unlink(missing_ok=True)
    except OSError:
        pass  # Diagnostic bookkeeping must not change an operation's outcome.

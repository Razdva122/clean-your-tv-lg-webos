#!/usr/bin/env python3
"""Recovery provisioning; may initialize an absent Home override to verified LG Home."""
import argparse
import hashlib
import fcntl
import json
import os
import re
from pathlib import Path
import stat
import select
import time
import subprocess
from python_binding import verify_binding

NAME = 'com.cleanyourtv.root.preview.service'
LEGACY_NODE_BETA = False
LEASE_NAME = 'com.webos.cleanyourtv.root.lease'
SERVICE = Path('/media/developer/apps/usr/palm/services') / NAME
STATE = Path('/var/lib/clean-your-tv-root')
BASE = Path('/var/luna-service2-dev')
PRIVATE_SERVICE = STATE/'service'
RUNNER = STATE/'run-recovery-service'
PRIVATE_FILES = ('service.js','startup-diagnostics.js','app-inventory.js','handlers.js','services.json','package.json','activity.json','boot-recover.sh')
RECEIVER_CAPABILITIES = ['theme-receiver-v1']
WALLPAPER_CAPABILITIES = RECEIVER_CAPABILITIES + ['wallpaper-media-v1']
COMPOSITOR_CAPABILITIES = WALLPAPER_CAPABILITIES + ['c1-keyfilter-v1']
LEGACY_NODE_COMPOSITOR_CAPABILITIES = WALLPAPER_CAPABILITIES + ['c1-keyfilter-v2']

def snapshot_capabilities(saved):
    capabilities = saved.get('capabilities', [])
    ordinary = ([], RECEIVER_CAPABILITIES, WALLPAPER_CAPABILITIES)
    # An OTA can retain an older registration contract. Add only the
    # screensaver methods and keep that contract intact for rollback.
    with_screensaver = tuple(base + ['screensaver-v1'] for base in ordinary)
    if capabilities not in ordinary + (COMPOSITOR_CAPABILITIES, LEGACY_NODE_COMPOSITOR_CAPABILITIES) + with_screensaver:
        raise ValueError('Unknown recovery capabilities')
    return capabilities
SYSTEM_FILES = tuple(Path(x) for x in ('/usr/bin/node','/usr/palm/services/jsservicelauncher/bootstrap-node.js','/usr/palm/services/jsservicelauncher/bootstrap.js'))
RUNTIME = STATE / 'runtime'
FILES = {'service': BASE/'services.d'/(NAME+'.service'),
         'role': BASE/'roles.d'/(NAME+'.service.json'),
         'client': BASE/'client-permissions.d'/(NAME+'.service.json'),
         'api': BASE/'api-permissions.d'/(NAME+'.api.json')}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def secure(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Unsafe root file: '+str(path))
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unsafe parent directory: '+str(parent))
    return path.read_bytes()

def write(path, data, mode=0o600):
    if isinstance(data, str): data = data.encode()
    temporary = path.with_name(path.name+'.root-preview-tmp')
    fd = os.open(str(temporary), os.O_WRONLY|os.O_CREAT|os.O_EXCL, mode)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
        directory = os.open(str(path.parent), os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if temporary.exists(): temporary.unlink()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()

def use_lg_local_activity():
    if LEGACY_NODE_BETA:
        return True
    if not os.path.lexists(STATE/'home-backend.json'):
        return False
    from runtime import c1_gate, c1_keyfilter
    return c1_keyfilter.reboot_resume_supported(c1_gate.selection(STATE))


def runner_bytes(*, local_activity=None):
    if local_activity is None:
        local_activity = use_lg_local_activity()
    # Follow the firmware's bootstrap argument contract, without evaluating a
    # writable Homebrew wrapper or modifying the system run-js-service script.
    # Legacy webos-service can exit idle while Activity Manager stalls dispatch.
    # LG's local activity mode keeps its request lifecycle without that round trip.
    return ('#!/bin/sh\nset -eu\n[ "$#" -eq 0 ] || exit 2\n'
            'cd '+str(PRIVATE_SERVICE)+'\n'
            'export NODE_PATH=/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules\n'
            'exec /usr/bin/node '+('' if LEGACY_NODE_BETA else '--require '+str(PRIVATE_SERVICE/'startup-diagnostics.js')+' ')+'/usr/palm/services/jsservicelauncher/bootstrap-node.js '
            +('--disable-activity-creation ' if local_activity else '')+'-- '
            +str(STATE/'bootstrap.pid')+' /var/palm/ls2-dev '+str(PRIVATE_SERVICE)+'\n').encode()

def prepare_private_service():
    for path in SYSTEM_FILES:
        secure(path)
    # release.json was copied into the private root state before installation.
    release = json.loads(secure(STATE/'release.json'))
    from deploy import checked_file
    contents = {}
    for name in PRIVATE_FILES:
        data = checked_file(SERVICE, name)
        key = 'usr/palm/services/'+NAME+'/'+name
        if sha(data) != release.get('files',{}).get(key):
            raise ValueError('Installed recovery payload mismatch: '+name)
        contents[name] = data
    if PRIVATE_SERVICE.is_symlink(): raise ValueError('Indirect private service')
    PRIVATE_SERVICE.mkdir(mode=0o700,exist_ok=True)
    if PRIVATE_SERVICE.stat().st_mode & 0o022: raise ValueError('Writable private service directory')
    for name,data in contents.items():
        path=PRIVATE_SERVICE/name
        if os.path.lexists(path):
            if secure(path)!=data: raise ValueError('Private recovery service drift: '+name)
        else: write(path,data,0o700 if name=='boot-recover.sh' else 0o600)
    if os.path.lexists(RUNNER):
        if secure(RUNNER)!=runner_bytes(): raise ValueError('Private runner drift')
    else: write(RUNNER,runner_bytes(),0o700)


def plan(original, capabilities=None):
    capabilities = snapshot_capabilities({'capabilities': [] if capabilities is None else capabilities})
    expected = 'Exec=/usr/bin/run-js-service -n '+str(SERVICE)
    if original['service'].splitlines().count(expected) != 1:
        raise ValueError('Unexpected installed service launcher')
    role = json.loads(original['role'])
    if role.get('appId') != NAME: raise ValueError('Unexpected installed role')
    role['allowedNames'] = [NAME]
    role['permissions'] = [{'service':NAME,
        'inbound':['com.webos.lunasend-*','com.webos.service.activitymanager','com.cleanyourtv.root.preview','com.cleanyourtv.root.preview-*'],
        'outbound':['com.webos.service.activitymanager','com.palm.activitymanager']}]
    control = ['status','restore','enable','confirm','listApps']
    if 'theme-receiver-v1' in capabilities:
        control += ['themeReceiverStart','themeReceiverStatus','themeReceiverRead','themeReceiverStop']
    if 'wallpaper-media-v1' in capabilities:
        control += ['wallpaperCacheStart','wallpaperCacheWrite','wallpaperCacheCommit','wallpaperCacheKeepAlive','wallpaperCacheStop']
    clients = {NAME:['activity.operation'],'com.cleanyourtv.root.preview':[NAME+'.control'],'com.cleanyourtv.root.preview-*':[NAME+'.control']}
    if 'screensaver-v1' in capabilities:
        control += ['screensaverStatus','screensaverConfigure','screensaverPreview','screensaverActivity','screensaverEligible','screensaverStop']
        clients[NAME].append('application.launcher')
        role['permissions'][0]['outbound'] += ['com.webos.applicationManager','com.webos.service.tvpower']
    apis = {NAME+'.control':[NAME+'/'+x for x in control],'activities.callbacks':[NAME+'/boot'],NAME+'.admin':[NAME+'/'+x for x in ('status','restore','register','unregister')]}
    compositor = capabilities in (COMPOSITOR_CAPABILITIES, LEGACY_NODE_COMPOSITOR_CAPABILITIES)
    if compositor:
        names=[line for line in original['service'].splitlines() if line.startswith('Name=')]
        if names not in (['Name='+NAME],['Name='+NAME+';']):
            raise ValueError('Unexpected compositor activation names')
        role['allowedNames'].append(LEASE_NAME)
        senders = ['com.webos.surfacemanager', 'com.webos.starfish.keyfilters', 'com.webos.lunasend-*']
        role['permissions'].append({'service':LEASE_NAME, 'inbound':senders, 'outbound':[]})
        # Running W21 compositor clients already hold the named stock group
        # 'all'. A policy scan does not refresh their cached client groups.
        apis['all'] = [LEASE_NAME+'/c1Lease', LEASE_NAME+'/c1Home']
        apis[LEASE_NAME+'.adapter-status'] = [LEASE_NAME+'/c1AdapterStatus']
        clients['com.webos.lunasend-*'] = [LEASE_NAME+'.adapter-status']
        if capabilities == LEGACY_NODE_COMPOSITOR_CAPABILITIES:
            # W19's stock legacy LS2 role reaches these methods via 'private'.
            # The alias and broker still accept only the two compositor senders.
            apis['private'] = apis['all']
    result = {'service': original['service'].replace(expected,'Exec='+str(RUNNER)).encode(),
            'role':encoded(role), 'client':encoded(clients), 'api':encoded(apis)}
    if compositor:
        # LS2 reads Name as a semicolon-delimited GLib string list. Keep the
        # SDK manifest's existing service-file path and exact rollback shape.
        result['service']=result['service'].replace(names[0].encode(),('Name='+NAME+';'+LEASE_NAME).encode())
    return result

def manifest():
    callback = PRIVATE_SERVICE/'boot-recover.sh'
    if b'/var/lib/clean-your-tv-root/runtime/cli.py boot' not in secure(callback):
        raise ValueError('Unexpected boot callback')
    verify_binding(STATE)
    binding = [STATE/name for name in ('python_binding.py','python_boot.js','package_data.py','package_identity.py','startup_guard.py','updater/store.py','updater/package.py','python-launcher','python-runtime.json') if os.path.lexists(STATE/name)]
    paths = binding + [RUNNER] + [PRIVATE_SERVICE/name for name in PRIVATE_FILES] + sorted(RUNTIME.glob('*.py'))
    if any(os.path.lexists(STATE/name) for name in ('home-backend.json', 'c1-gate', 'c1-keyfilter', 'runtime/c1_gate.py', 'runtime/c1_keyfilter.py', 'runtime/c1-home-gate', 'runtime/c1-keyfilter-guard')):
        from runtime import c1_gate
        selected = c1_gate.selection(STATE)
        compositor = selected.get('routing') == 'compositor-keyfilter-v1'
        native = RUNTIME/('c1-keyfilter-guard' if compositor else 'c1-home-gate')
        if compositor:
            paths.append(RUNTIME/'c1-home-filter.js')
            embedded = [RUNTIME/name for name in ('embedded-home.qml', 'embedded-home.js')]
            # Historical compositor bundles did not ship the embedded adapter.
            # Bind both assets when available, and require them for its selection.
            if selected.get('schema') == 4 or any(os.path.lexists(path) for path in embedded):
                paths += embedded
        if sha(secure(native)) != selected['native_sha256']:
            raise ValueError('Experimental native recovery identity changed')
        paths += [STATE/'home-backend.json', native]
    if RUNTIME/'cli.py' not in paths: raise ValueError('Missing runtime')
    return {'version':1,'mode':'recovery-only','boot_callback':str(callback),
            'files':{str(path):sha(secure(path)) for path in paths}}

def apply():
    if os.geteuid() != 0: raise ValueError('Root required')
    prepare_private_service()
    if json.loads(secure(PRIVATE_SERVICE/'services.json')).get('id') != NAME: raise ValueError('Wrong installed service')
    pending = manifest()
    original = {key:secure(path).decode() for key,path in FILES.items()}
    release = json.loads(secure(STATE/'release.json'))
    capabilities = snapshot_capabilities(release)
    updated = plan(original, capabilities)
    STATE.mkdir(mode=0o700, exist_ok=True)
    snapshot = STATE/'ls2-provision-snapshot.json'
    if snapshot.exists() or snapshot.is_symlink() or (STATE/'recovery-provision.json').exists():
        raise ValueError('Provision already exists; inspect or rollback first')
    saved = {'version':1,'service':NAME,'files':{str(path):{'original':original[key],
        'original_sha256':sha(original[key].encode()),'installed_sha256':sha(updated[key]),
        'mode':stat.S_IMODE(path.stat().st_mode),'uid':path.stat().st_uid,'gid':path.stat().st_gid}
        for key,path in FILES.items()}}
    if capabilities: saved['capabilities'] = capabilities
    write(snapshot,encoded(saved))
    write(STATE/'recovery-provision.pending.json',encoded(pending))
    for key,path in FILES.items():
        mode = saved['files'][str(path)]['mode']
        write(path,updated[key],mode)
        os.chown(path,saved['files'][str(path)]['uid'],saved['files'][str(path)]['gid'])
    return {'returnValue':True,'next':'Refresh LS2 registration, then finalize. Trials remain disabled.'}

def repair_pending(allow_original=False):
    """Upgrade only incomplete recovery provisioning, never an active trial."""
    if os.path.lexists(STATE/'recovery-provision.json') or os.path.lexists(STATE/'profile-trial.json'):
        raise ValueError('Only never-activated provisioning may be repaired')
    path=STATE/'ls2-provision-snapshot.json'
    saved=json.loads(secure(path))
    if saved.get('phase') is not None or saved.get('service')!=NAME or set(saved['files'])!={str(p) for p in FILES.values()}:
        raise ValueError('Unexpected pending snapshot')
    original={key:saved['files'][str(file)]['original'] for key,file in FILES.items()}
    updated=plan(original, snapshot_capabilities(saved))
    for key,file in FILES.items():
        entry=saved['files'][str(file)]
        if sha(entry['original'].encode())!=entry['original_sha256'] or sha(secure(file)) not in (entry['installed_sha256'],entry.get('previous_installed_sha256'),entry['original_sha256'] if allow_original else None):
            raise ValueError('Pending provision drift')
        newhash=sha(updated[key])
        if newhash!=entry['installed_sha256']:
            if entry.get('previous_installed_sha256'): raise ValueError('Only one pending repair supported')
            entry['previous_installed_sha256']=entry['installed_sha256']
            entry['installed_sha256']=newhash
    write(path,encoded(saved))
    if allow_original:write(STATE/'recovery-provision.pending.json',encoded(manifest()))
    for key,file in FILES.items():
        entry=saved['files'][str(file)]
        write(file,updated[key],entry['mode']);os.chown(file,entry['uid'],entry['gid'])
    return {'returnValue':True,'repaired_pending':True}


def resume_pending():
    return repair_pending(allow_original=True)


class RecoveryRPCError(ValueError):
    def __init__(self, reason, code=None):
        super().__init__('Recovery RPC failed: '+reason)
        self.details = {'reason': reason}
        if type(code) is int and -(2**31) <= code < 2**31:
            self.details['luna_error_code'] = code


def startup_record():
    try:
        path = STATE/'recovery-service.json'
        if path.lstat().st_size > 32768: return None
        value = json.loads(secure(path))
        return value if isinstance(value, dict) and value.get('schema') == 1 else None
    except (OSError, ValueError):
        return None


def rpc(method, *, writer=None):
    if method in ('register','unregister'):
        import activity
        return activity.manage(method,secure,writer or write)
    home_calls = {
        'home-read': ('com.webos.settingsservice/getSystemSettings', {'category':'general','keys':['defaultApps']}),
        'home-profiles': ('com.webos.service.systemprofile/getProfiles', {'names':['defaultApps','idleApp'],'subscribe':False}),
        'home-stock': ('com.webos.service.applicationmanager/setDefaultApp', {'category':'home','appId':'com.webos.app.home'}),
    }
    if method not in ('status','restore') and method not in home_calls:
        raise ValueError('Unsupported recovery method')
    uri, payload = home_calls.get(method, (NAME+'/'+method, {}))
    uri = 'luna://'+uri
    try:
        process = subprocess.Popen(['/usr/bin/luna-send','-n','1',uri,json.dumps(payload)],
                                   stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except OSError as error:
        raise RecoveryRPCError('client-start-failed') from error
    try:
        # This TV exits luna-send early if stdin closes before its first reply.
        deadline = time.monotonic()+(610 if method == 'restore' else 5 if method in home_calls else 45)
        data, total = b'', 0
        streams = [process.stdout, process.stderr]
        while time.monotonic() < deadline:
            ready = select.select(streams, [], [], max(0, deadline-time.monotonic()))[0]
            if not ready: break
            for stream in ready:
                chunk = os.read(stream.fileno(), 4096)
                if not chunk:
                    if stream is process.stdout:
                        reason = 'invalid-reply' if data else 'client-exited'
                        raise RecoveryRPCError(reason)
                    streams.remove(stream)
                    continue
                total += len(chunk)
                if total > 65536: raise RecoveryRPCError('oversized-client-output')
                if stream is process.stderr: continue  # Drain, but never export raw errors.
                data += chunk
                try: reply = json.loads(data)
                except ValueError: continue
                if not isinstance(reply,dict) or type(reply.get('returnValue')) is not bool:
                    raise RecoveryRPCError('invalid-reply')
                if reply['returnValue'] is False:
                    error = RecoveryRPCError('negative-reply', reply.get('errorCode'))
                    text = reply.get('errorText')
                    text = text[:1024].lower() if isinstance(text, str) else ''
                    for category, phrases in (('permission-denied', ('denied methods call', 'permission denied', 'access denied')),
                                              ('service-missing', ('service does not exist', 'service is not registered')),
                                              ('method-missing', ('unknown method', 'method does not exist'))):
                        if any(phrase in text for phrase in phrases):
                            error.details['luna_reason'] = category
                            break
                    raise error
                return reply
        reason = 'client-exited' if process.poll() is not None else 'timeout'
        raise RecoveryRPCError(reason)
    except RecoveryRPCError as error:
        code = process.poll()  # Before cleanup, so our terminate() is not reported as the cause.
        if type(code) is int and 0 <= code <= 255: error.details['client_exit_status'] = code
        raise
    finally:
        if process.poll() is None: process.terminate()
        # Never re-buffer arbitrary output through communicate() during cleanup.
        for stream in (process.stdin, process.stdout, process.stderr):
            try: stream.close()
            except OSError: pass
        try: process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=1)

def refresh():
    executable = next((path for path in (Path('/usr/bin/ls-control'),Path('/usr/sbin/ls-control')) if path.is_file()),None)
    if executable is None: raise ValueError('ls-control unavailable')
    subprocess.run([str(executable),'scan-services'],check=True,timeout=15,
                   stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {'returnValue':True,'operation':'scan-services','effective_registration_verified':False}


def require_home_interfaces():
    """Read-only capability gate, usable before any package or Root state exists.

    An absent settings override is valid; prepare_stock_home materializes it
    later only after checking the actual stock profiles. Never infer a route
    when the firmware cannot supply its effective profile readback.
    """
    try:
        settings = rpc('home-read')
        reply = rpc('home-profiles')
        defaults = settings['settings']['defaultApps']
        profiles = reply['profiles']
        routes = [profiles['defaultApps']['categories']['home'], profiles['idleApp']['appId']]
        if not isinstance(defaults,dict): raise ValueError('invalid-defaults')
        if 'home' in defaults: routes.append(defaults['home'])
        if (settings.get('returnValue') is not True or reply.get('returnValue') is not True
                or type(profiles['idleApp']['support']) is not bool
                or any(not isinstance(value,str) or not value or value.strip()!=value for value in routes)):
            raise ValueError('invalid-routing-readback')
    except (OSError,RuntimeError,ValueError,KeyError,TypeError) as error:
        raise RuntimeError('Required Home routing interfaces are unavailable or invalid; installation was not started') from error


def prepare_stock_home():
    """Setup only: materialize an absent override, never infer a SAM readback.

    A submitted write is reconciled by observation, never repeated. The explicit
    stock override remains after removal; it selects the same original LG Home.
    """
    if any(os.path.lexists(STATE/name) for name in ('home-backend.json', 'c1-gate', 'c1-keyfilter', 'runtime/c1_gate.py', 'runtime/c1_keyfilter.py', 'runtime/c1-home-gate', 'runtime/c1-keyfilter-guard')):
        from runtime import c1_gate
        selected = c1_gate.selection(STATE)
        if selected.get('routing') == 'compositor-keyfilter-v1':
            from runtime import c1_keyfilter as backend
        else:
            backend = c1_gate
        if backend.probe() != selected['admission']:
            raise ValueError('C1 admission changed during provisioning')
        proof = backend.validate_native(backend.native(['--status'], STATE))
        if not proof['stock_verified'] or proof['mounted']:
            raise ValueError('Original C1 Home is not verified')
        return
    stock = 'com.webos.app.home'
    receipt = STATE/'stock-home-initialization.json'
    def settings():
        reply = rpc('home-read')
        try: value = reply['settings']['defaultApps']
        except (KeyError, TypeError) as error: raise ValueError('Incomplete Home settings readback') from error
        if (not isinstance(value,dict) or ('home' in value and
                (not isinstance(value['home'],str) or not value['home'] or value['home'].strip()!=value['home']))):
            raise ValueError('Invalid Home settings readback')
        return value

    current = settings()
    has_receipt = os.path.lexists(receipt)
    pending = json.loads(secure(receipt)) if has_receipt else None
    if has_receipt and (
            not isinstance(pending,dict) or set(pending) != {'schema','phase','defaultApps','profiles'}
            or type(pending['schema']) is not int or pending['schema'] != 1
            or pending['phase'] not in ('submitted','verified')
            or not isinstance(pending['defaultApps'],dict) or 'home' in pending['defaultApps']):
        raise ValueError('Invalid stock Home initialization evidence; keep recovery data')
    if pending is None and 'home' in current: return
    # Even a dangling marker is ambiguous. Never alter established recovery or
    # an existing routing transaction to retrofit support onto retained code.
    blocked = [STATE/name for name in ('recovery-provision.json','profile-trial.json',
               'persistent-intent.json','persistent-binding.json','boot-continuation.json','profile-candidate.stage')]
    blocked.append(Path('/var/webos-profile/override/clean-your-tv-root.json'))
    if pending is None and any(os.path.lexists(path) for path in blocked):
        raise ValueError('Home initialization requires never-activated provisioning')
    try:
        profiles = rpc('home-profiles')['profiles']
        if (profiles['defaultApps']['categories']['home'] != stock
                or profiles['idleApp']['appId'] != stock or profiles['idleApp']['support'] is not True):
            raise ValueError('Home initialization requires stock profiles')
    except (KeyError, TypeError) as error:
        raise ValueError('Incomplete stock profiles') from error
    if pending is None:
        pending = {'schema':1,'phase':'submitted','defaultApps':current,'profiles':profiles}
        write(receipt,encoded(pending))  # Durable intent before the only write.
        try: rpc('home-stock')
        except RecoveryRPCError: pass  # A missing reply is not proof of failure.
        current = settings()
        profiles = rpc('home-profiles')['profiles']
    if current != dict(pending['defaultApps'],home=stock) or profiles != pending['profiles']:
        raise ValueError('Stock Home initialization unconfirmed; keep recovery data, do not replay')
    if pending['phase'] != 'verified': write(receipt,encoded(dict(pending,phase='verified')))


def register_firmware_access():
    from python_binding import command
    reply=subprocess.run([command(STATE),str(RUNTIME/'cli.py'),'provision-firmware-access'],check=True,timeout=30,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    envelope=json.loads(reply.stdout)
    result=envelope.get('result') if isinstance(envelope,dict) and envelope.get('returnValue') is True else None
    return isinstance(result,dict) and result.get('returnValue') is True and result.get('permissions_installed') is True


def finalize(*, record_failure=True, firmware_permissions=True, writer=None):
    before = startup_record()
    phase = 'manifest'
    try:
        expected = json.loads(secure(STATE/'recovery-provision.pending.json'))
        if manifest() != expected: raise ValueError('Runtime changed since provisioning')
        phase = 'stock-home'
        prepare_stock_home()
        phase = 'status'
        reply = rpc('status')
        if reply.get('root') is not True:
            raise ValueError('Recovery callback process is not root')
        phase = 'register'
        reply = rpc('register', writer=writer) if writer else rpc('register')
        if reply.get('root') is not True or reply.get('registered') is not True or reply.get('activityName') != NAME+'.recovery':
            raise ValueError('Recovery activity not verified')
        phase = 'startup-hook'
        import startup_hook
        startup_hook.install(secure,writer or write)
        phase = 'publish'
        (writer or write)(STATE/'recovery-provision.json',encoded(expected))
        phase = 'firmware-permissions'
        firmware_ready = False
        if firmware_permissions:
            try: firmware_ready=register_firmware_access()
            except Exception: pass  # Optional settings must not block core Home/recovery setup.
        return {'returnValue':True,'mode':'recovery-only','activity':reply,'firmware_permissions_registered':bool(firmware_ready)}
    except Exception as error:
        report = {'schema':1, 'phase':phase, 'reason':'failed'}
        attempt = os.environ.get('CYTV_ROOT_INSTALL_ATTEMPT', '')
        import re
        if re.fullmatch('[a-f0-9]{32}', attempt): report['attempt'] = attempt
        if isinstance(error, RecoveryRPCError): report.update(error.details)
        after = startup_record()
        report['startup_state'] = 'unavailable' if after is None else 'stale'
        if after is not None and after != before and after.get('phase') in ('starting','exited'):
            report['startup_state'] = after['phase']
            milestone = after.get('startup_milestone')
            if (milestone in ('status-registered', 'status-requested', 'status-response-returned')
                    and (before is None or after.get('attempt') != before.get('attempt')
                         or milestone != before.get('startup_milestone'))):
                report['startup_milestone'] = milestone
            code = after.get('exit_status')
            if type(code) is int and 0 <= code <= 255: report['startup_exit_status'] = code
            exception = after.get('exception', {})
            if isinstance(exception, dict):
                if exception.get('name') in ('Error','TypeError','SyntaxError','ReferenceError','RangeError'):
                    report['exception_name'] = exception['name']
                if exception.get('code') in ('MODULE_NOT_FOUND','ERR_DLOPEN_FAILED','EACCES','EPERM','ENOENT'):
                    report['exception_code'] = exception['code']
        if record_failure:
            try: write(STATE/'recovery-failure.json',encoded(report))
            except (OSError, ValueError): pass
        else:
            error.beta_repair_failure = {'stage': phase, **{
                key: report[key] for key in ('reason', 'luna_reason', 'luna_error_code',
                    'startup_state', 'startup_exit_status') if key in report}}
        raise


def verify_retained_repair_registration():
    snapshot = json.loads(secure(STATE/'ls2-provision-snapshot.json'))
    entries = snapshot['files']
    if (snapshot.get('version') != 1 or snapshot.get('service') != NAME
            or snapshot.get('phase') is not None
            or snapshot_capabilities(snapshot) != COMPOSITOR_CAPABILITIES
            or set(entries) != {str(path) for path in FILES.values()}):
        raise ValueError('Original Root LS2 registration required')
    original = {name: entries[str(path)]['original'] for name, path in FILES.items()}
    updated = plan(original, COMPOSITOR_CAPABILITIES)
    for name, path in FILES.items():
        entry = entries[str(path)]
        raw = secure(path)
        metadata = path.stat()
        if (sha(original[name].encode()) != entry['original_sha256']
                or raw != updated[name] or sha(raw) != entry['installed_sha256']
                or (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode))
                != (entry['uid'], entry['gid'], entry['mode'])):
            raise ValueError('Original Root LS2 registration changed')


def retained_repair_write(path, data, mode=0o600):
    # The deployment and provisioning locks fence the old writer. Only a
    # prefix of this exact output may be left by an interrupted atomic write.
    temporary = path.with_name(path.name+'.root-preview-tmp')
    if isinstance(data, str):
        data = data.encode()
    if os.path.lexists(temporary):
        if not data.startswith(secure(temporary)):
            raise ValueError('Unrecognized interrupted Beta recovery write')
        temporary.unlink()
    write(path, data, mode)


def verify_retained_support(pins):
    from deploy import SUPPORT_FILES
    release = secure(STATE/'release.json')
    bundle = secure(STATE/'bundle.json')
    if tuple(map(sha, (release, bundle))) != pins:
        raise ValueError('Original Root install receipt does not match')
    files = json.loads(bundle)['files']
    for name in SUPPORT_FILES:
        if sha(secure(STATE/name)) != files.get(name):
            raise ValueError('Original Root support changed')
    return json.loads(release)


def repair_beta_recovery(checkpoint=lambda stage: None):
    return repair_retained_recovery(checkpoint)


def repair_root_recovery(pins, checkpoint=lambda stage: None):
    return repair_retained_recovery(checkpoint, pins=pins)


def repair_retained_recovery(checkpoint, *, pins=None, native_product=False):
    from deploy import APP, verify_payload
    from package_identity import bootstrap_inventory
    from runtime import c1_keyfilter

    checkpoint('retained-release')
    beta = pins is None
    if LEGACY_NODE_BETA != beta:
        raise ValueError('Wrong Root recovery support variant')
    release = json.loads(secure(STATE/'release.json')) if beta else verify_retained_support(pins)
    version = '0.20.0' if beta else '0.23.0' if native_product else '0.22.0'
    if (release.get('application_id'), release.get('version'), release.get('runtime_variant'),
            release.get('home_backend'), release.get('routing'), release.get('compositor_admission')) != (
            APP, version, 'node012-beta' if beta else None,
            'c1-native-gate', 'compositor-keyfilter-v1', 3):
        raise ValueError('Unsupported retained Root package')
    checkpoint('deployment-stage')
    deployment = json.loads(secure(STATE/'deploy.json'))
    stage = deployment.get('stage')
    if (deployment != {'version': 1, 'app': APP, 'stage': stage}
            or stage not in ('provision-finalize-starting', 'installed-recovery-only')):
        raise ValueError('Original Root provisioning stage required')
    checkpoint('original-timeout')
    failure = json.loads(secure(STATE/'recovery-failure.json'))
    if (failure.get('schema'), failure.get('phase'), failure.get('reason'),
            failure.get('startup_state'), failure.get('startup_exit_status')) != (1, 'status', 'timeout', 'exited', 0):
        raise ValueError('Original Root recovery timeout required')
    checkpoint('routing-selection')
    if any(os.path.lexists(STATE/name) for name in ('profile-trial.json', 'persistent-intent.json',
            'persistent-binding.json', 'boot-continuation.json', 'profile-candidate.stage')):
        raise ValueError('Active or retained Home routing prevents Root repair')
    selection = c1_keyfilter.selection(STATE)
    if not selection or selection['schema'] != 3 or selection['native_sha256'] != release.get('native_sha256'):
        raise ValueError('Original Root compositor selection required')
    checkpoint('installed-package')
    bootstrap_inventory(STATE)
    if not beta:
        verify_payload(release)
    if native_product:
        # Authenticate the historical runtime and its private service copy
        # independently of the mutable recovery-provision manifest.
        files = json.loads(secure(STATE/'bundle.json'))['files']
        runtime = {str(path.relative_to(STATE)) for path in RUNTIME.glob('*.py')}
        if runtime != {name for name in files if name.startswith('runtime/') and name.endswith('.py')}:
            raise ValueError('Original Root runtime inventory changed')
        runtime.update(('runtime/c1-keyfilter-guard', 'runtime/c1-home-filter.js'))
        for name in runtime:
            if sha(secure(STATE/name)) != files.get(name):
                raise ValueError('Original Root runtime changed')
        for name in PRIVATE_FILES:
            expected = release['files'].get('usr/palm/services/'+NAME+'/'+name)
            if sha(secure(PRIVATE_SERVICE/name)) != expected:
                raise ValueError('Original private Root service changed')
    checkpoint('ls2-registration')
    verify_retained_repair_registration()
    checkpoint('runner')
    if not beta and not native_product and use_lg_local_activity():
        raise ValueError('The original runner already used local request activities')
    expected_runner = runner_bytes(local_activity=True)
    old_runner = runner_bytes(local_activity=False)
    if (secure(RUNNER) not in (old_runner, expected_runner)
            or native_product and stat.S_IMODE(RUNNER.stat().st_mode) != 0o700):
        raise ValueError('Retained Root runner changed')
    checkpoint('pending-proof')
    observed = manifest()
    old_manifest = dict(observed, files=dict(observed['files'], **{str(RUNNER): sha(old_runner)}))
    new_manifest = dict(observed, files=dict(observed['files'], **{str(RUNNER): sha(expected_runner)}))
    pending = STATE/'recovery-provision.pending.json'
    saved_manifest = json.loads(secure(pending))
    ready = STATE/'recovery-provision.json'
    have_ready = os.path.lexists(ready)
    if (saved_manifest not in (old_manifest, new_manifest)
            or stage == 'installed-recovery-only' and not have_ready
            or have_ready and (observed != new_manifest or saved_manifest != new_manifest
                               or json.loads(secure(ready)) != new_manifest)):
        raise ValueError('Retained Root recovery manifest changed')
    checkpoint('stock-home')
    prepare_stock_home()

    # Runner first allows retry after either atomic write. Recheck every other
    # manifest member before accepting a mixture of the two known runner bytes.
    if observed != new_manifest:
        checkpoint('write-runner')
        retained_repair_write(RUNNER, expected_runner, 0o700)
    if saved_manifest != new_manifest:
        checkpoint('write-pending-proof')
        retained_repair_write(pending, encoded(new_manifest))
    if not have_ready:
        checkpoint('manifest')
        finalize(record_failure=False, firmware_permissions=False, writer=retained_repair_write)
    checkpoint('final-status')
    status = rpc('status')
    # LS2 handlers wrap the Python CLI envelope in their own result.
    runtime = status.get('result')
    result = runtime.get('result') if isinstance(runtime, dict) else None
    recovery = result.get('recovery') if isinstance(result, dict) else None
    if (status.get('root') is not True
            or not isinstance(runtime, dict) or runtime.get('returnValue') is not True
            or not isinstance(recovery, dict) or recovery.get('integrity_verified') is not True):
        raise ValueError('Repaired Root recovery status could not be verified')
    if native_product:
        checkpoint('stock-home')
        effective, intent = result.get('effective'), result.get('intent')
        if (result.get('backend') != 'c1-native-gate' or not isinstance(effective, dict)
                or effective.get('routing') != 'compositor-keyfilter-v1'
                or effective.get('stock_verified') is not True
                or any(effective.get(key) is not False
                       for key in ('mounted', 'healthy', 'filter_installed', 'routing_active'))
                or type(effective.get('guardian_pid')) is not int or effective['guardian_pid'] != 0
                or not isinstance(intent, dict) or intent.get('enabled') is not False
                or intent.get('phase') != 'disabled'):
            raise ValueError('Stock Home status could not be verified')
        prepare_stock_home()
    if stage != 'installed-recovery-only':
        checkpoint('write-deployment-stage')
        retained_repair_write(STATE/'deploy.json', encoded(
            {'version': 1, 'app': APP, 'stage': 'installed-recovery-only'}))
    return {'returnValue': True, 'status_verified': True, 'home_changed': False}


def repair_native_product(owner, operation, pins, checkpoint):
    from deploy import APP, install_failure_details
    from installation import pending_journals
    from runtime import c1_keyfilter

    checkpoint('deploy-lease')
    journal = 'product-' + operation + '.json'
    request_name = 'request-' + operation
    lease = owner.status()
    if not lease or lease['owner'] != 'product' or lease['journal'] != journal:
        raise ValueError('Original native Root product reservation required')
    def check():
        if owner.status() != lease:
            raise ValueError('Original native Root product reservation changed')
        pending_journals('deploy')

    with owner.operation('product', journal, resume=lease['id'], check=check) as current:
        request = owner.store.read(request_name)
        completion = {'returnValue': True, 'installed': APP, 'home_changed': False}
        failed = (isinstance(request, dict) and request.get('state') == 'recovery_required'
                  and request.get('stage') == 'root-deploy'
                  and request.get('code') == 'installation_requires_recovery'
                  and current['stage'] == 'root-deploy' and not current['terminal'])
        complete = (isinstance(request, dict) and request.get('state') == 'complete'
                    and request.get('stage') == 'complete' and request.get('code') == 'verified'
                    and request.get('result') == completion
                    and (current['stage'], current['terminal']) in (('root-deploy', False), ('complete', True)))
        if (not (failed or complete) or request.get('operation') != operation
                or request.get('lease') != current['id'] or request.get('action') != 'install'
                or request.get('home_changed') is not False or current != lease
                or not isinstance(request.get('clean_predecessor'), str)
                or not re.fullmatch('[a-f0-9]{32}', request['clean_predecessor'])
                or request['clean_predecessor'] == operation):
            raise ValueError('Original failed native Root request required')
        failure = request.get('failure')
        driver = install_failure_details(failure.get('root_driver')) if isinstance(failure, dict) else {}
        # These retained driver frames are specific to the 0.23.0 provisioning loop.
        if driver != {'exception_type': 'CalledProcessError', 'exit_status': 1,
                      'frames': [{'file': 'deploy.py', 'line': 315}, {'file': 'deploy.py', 'line': 141}]}:
            raise ValueError('Original native Root provisioning failure required')

        checkpoint('provision-lock')
        fd = os.open(STATE/'provision.lock', os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner.store.uid
                    or info.st_nlink != 1 or info.st_mode & 0o077):
                raise ValueError('Unsafe Root provision lock')
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            deploy_path, failure_path = STATE/'deploy.json', STATE/'recovery-failure.json'
            deployment = json.loads(secure(deploy_path))
            if complete and deployment.get('stage') != 'installed-recovery-only':
                raise ValueError('Completed native Root provisioning stage required')
            if deployment.get('stage') == 'provision-finalize-starting':
                # This historical path never bound the child's failure to an
                # attempt ID. Require it to fall within the original journal
                # interval rather than accepting an older failure record.
                secure(failure_path)
                request_path = Path(owner.store.root)/(request_name+'.json')
                if not (deploy_path.stat().st_mtime_ns <= failure_path.stat().st_mtime_ns
                        <= request_path.stat().st_mtime_ns):
                    raise ValueError('Original native Root failure chronology changed')
            checkpoint('stock-home')
            with c1_keyfilter.operation(STATE):
                intent = c1_keyfilter.read_intent(STATE)
                if (intent['enabled'] or intent['phase'] != 'disabled'
                        or os.path.lexists(STATE/'c1-keyfilter/pending.json')):
                    raise ValueError('Active or retained Home routing prevents Root repair')
                result = repair_retained_recovery(checkpoint, pins=pins, native_product=True)
                checkpoint('close-deploy-lease')
                if failed:
                    request.update(stage='complete', state='complete', code='verified', result=completion)
                    owner.store.write(request_name, request)
                if not current['terminal']:
                    owner.stage(current, 'complete', terminal=True)
        finally:
            os.close(fd)
        return dict(result, operation=operation)


def retained_repair_command(pins=None, *, product_operation=None):
    stage = 'device'

    def checkpoint(value):
        nonlocal stage
        stage = value

    try:
        from deploy import require_device, require_node
        from installation import Ownership, device_operation, pending_journals
        require_device()
        require_node()
        checkpoint('deploy-lease')
        owner = Ownership()
        if product_operation is not None:
            print(json.dumps(repair_native_product(owner, product_operation, pins, checkpoint)))
            return

        def existing_deploy():
            lease = owner.status()
            if (not lease or lease['owner'] != 'deploy' or lease['journal'] != 'deploy.json'
                    or lease['terminal'] and (pins is None or lease['stage'] != 'installed-recovery-only')):
                raise ValueError('Original Root deploy reservation required')
            return lease

        if pins is None:
            lease_context = device_operation('deploy', recovery=True, ownership=owner, check=existing_deploy)
        else:
            lease_context = owner.operation('deploy', 'deploy.json', resume=existing_deploy()['id'],
                                            check=lambda: pending_journals('deploy'))
        with lease_context as lease:
            checkpoint('provision-lock')
            fd = os.open(STATE/'provision.lock', os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                result = repair_retained_recovery(checkpoint, pins=pins)
            finally:
                os.close(fd)
            checkpoint('close-deploy-lease')
            if pins is not None and not lease['terminal']:
                owner.stage(lease, 'installed-recovery-only', terminal=True)
    except Exception as error:
        detail = {'stage': stage, 'reason': 'failed'}
        if isinstance(error, RecoveryRPCError):
            detail.update(error.details)
        detail.update(getattr(error, 'beta_repair_failure', {}))
        key = 'root_beta_repair_failure' if pins is None else 'root_retained_repair_failure'
        print(json.dumps({'returnValue': False, key: detail}), flush=True)
        raise SystemExit(1) from None
    print(json.dumps(result))


def disable_trials():
    # Serialize readiness revocation with the runtime's trial publication lock.
    # begin() rechecks this manifest after acquiring that same lock.
    fd = os.open(STATE/'profile-trial.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        readiness = STATE/'recovery-provision.json'
        if readiness.exists(): readiness.unlink()
        directory = os.open(STATE, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally: os.close(fd)

def verify_restored_files(saved):
    if (saved.get('version') != 1 or saved.get('service') != NAME
            or saved.get('phase') != 'rolled-back'
            or set(saved['files']) != {str(p) for p in FILES.values()}
            or os.path.lexists(STATE/'recovery-provision.json')):
        raise ValueError('Restored LS2 snapshot required')
    for path, entry in saved['files'].items():
        file = Path(path)
        if sha(entry['original'].encode()) != entry['original_sha256'] or sha(secure(file)) != entry['original_sha256']:
            raise ValueError('Restored LS2 file drift: '+path)
        info = file.stat()
        if (stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid) != (entry['mode'], entry['uid'], entry['gid']):
            raise ValueError('Restored LS2 metadata drift: '+path)


def verify_embedded_activation_retired(saved):
    """Prove restored files and no live/activatable lease alias, not API grants.

    Some hubs reject queryServicePermissions locally in LSCall. An ordinary
    privileged request consults their live activation table instead. Only the
    exact hub missing-service result authorizes this embedded removal path.
    """
    if saved is None:
        raise ValueError('Restored LS2 snapshot required')
    verify_restored_files(saved)
    from runtime.transport import call
    refresh()
    deadline = time.monotonic() + 3
    expected = dict(returnValue=False, errorCode=-1,
                    errorText='Service does not exist: '+LEASE_NAME+'.')
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('LS2 alias activation retirement unverified')
        reply = call('luna://com.webos.cleanyourtv.root.lease/c1AdapterStatus', {},
                     timeout=min(1, remaining), named=True, allow_failure=True)
        if (isinstance(reply, dict) and reply == expected
                and reply.get('returnValue') is False
                and type(reply.get('errorCode')) is int):
            verify_restored_files(saved)
            return
        time.sleep(min(.1, remaining))


def verify_beta_removal_registration(rpc, saved=None):
    """Check the live hub before submitting a legacy preview package removal."""
    if os.path.lexists(STATE/'home-backend.json'):
        from runtime.c1_gate import selection
        selected = selection(STATE)
        if selected and selected['schema'] == 4:
            return verify_embedded_activation_retired(saved)
    expected = {}
    if saved is not None:
        verify_restored_files(saved)
        for group, methods in json.loads(saved['files'][str(FILES['api'])]['original']).items():
            for method in methods:
                if method.startswith(NAME+'/'):
                    expected.setdefault(method[len(NAME):], set()).add(group)

    def api(service):
        reply = rpc('com.webos.service.bus/queryServicePermissions', {'service': service})
        methods = reply.get('api') if isinstance(reply, dict) and reply.get('returnValue') is True else None
        if not isinstance(methods, dict) or any(
                not isinstance(method, str) or not isinstance(groups, list)
                or not all(isinstance(group, str) for group in groups)
                for method, groups in methods.items()):
            raise ValueError('LS2 permission readback unverified')
        return methods

    def restored():
        # W19P reports generic wildcard grants even for an absent alias.
        if {'/c1Lease', '/c1Home', '/c1AdapterStatus'}.intersection(api(LEASE_NAME)):
            return False
        if not expected:
            return True
        actual = api(NAME)
        return all(groups.issubset(actual.get(method, ())) for method, groups in expected.items())

    if restored():
        return
    # scan-services only queues a signal. On a retry the controls checkpoint
    # may already be present, so request a fresh scan when readback is stale.
    refresh()
    deadline = time.monotonic() + 3
    while not restored():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('LS2 registration restore unverified')
        time.sleep(min(.1, remaining))


def rollback(restored=None):
    saved = json.loads(secure(STATE/'ls2-provision-snapshot.json'))
    if saved.get('version') != 1 or saved.get('service') != NAME or set(saved['files']) != {str(p) for p in FILES.values()}:
        raise ValueError('Invalid provision snapshot')
    if saved.get('phase') == 'rolled-back':
        verify_restored_files(saved)
        import system_permissions
        system_permissions.remove(secure)
        import startup_hook
        startup_hook.remove(secure)
        return {'returnValue':True,'already_rolled_back':True,'next':'Refresh LS2 registration before package removal.'}
    if saved.get('phase') not in (None, 'restoring'):
        raise ValueError('Unknown provisioning phase')
    if saved.get('phase') == 'restoring' and os.path.lexists(STATE/'recovery-provision.json'):
        raise ValueError('Unexpected readiness during rollback')
    # Refuse any drift before canceling activity or touching files. A partial apply
    # can contain original or installed bytes, both exactly recorded here.
    for path, entry in saved['files'].items():
        if sha(entry['original'].encode()) != entry['original_sha256'] or sha(secure(Path(path))) not in (entry['original_sha256'],entry['installed_sha256'],entry.get('previous_installed_sha256')):
            raise ValueError('LS2 file drift: '+path)
    if saved.get('phase') != 'restoring':
        disable_trials()
        reply = rpc('restore') if restored is None else {'result':restored}
        runtime = reply.get('result')
        if not isinstance(runtime,dict) or runtime.get('returnValue') is not True or runtime.get('result') not in ('restored','absent'):
            raise ValueError('Recovery is not terminal; keep boot activity registered')
        rpc('unregister')
        saved['phase'] = 'restoring'
        write(STATE/'ls2-provision-snapshot.json',encoded(saved))
    import system_permissions
    system_permissions.remove(secure)
    import startup_hook
    startup_hook.remove(secure)
    for path,entry in saved['files'].items():
        write(Path(path),entry['original'],entry['mode'])
        os.chown(path,entry['uid'],entry['gid'])
    saved['phase'] = 'rolled-back'
    write(STATE/'ls2-provision-snapshot.json',encoded(saved))
    pending = STATE/'recovery-provision.pending.json'
    if pending.exists(): pending.unlink()
    return {'returnValue':True,'next':'Refresh LS2 registration; uninstall package only after recovery succeeds.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan','apply','refresh','finalize','rollback','repair_pending','resume_pending','repair_beta_recovery','repair_root_recovery'])
    parser.add_argument('pins', nargs='*')
    parser.add_argument('--product-operation')
    args = parser.parse_args()
    command = args.command
    if args.product_operation is not None and (command != 'repair_root_recovery'
            or not re.fullmatch('[0-9a-f]{32}', args.product_operation)):
        parser.error('Original native Root operation required')
    if command == 'repair_root_recovery':
        if len(args.pins) != 2 or any(not re.fullmatch('[0-9a-f]{64}', pin) for pin in args.pins):
            parser.error('Original Root release and bundle digests required')
    elif args.pins:
        parser.error('Only retained Root repair takes digests')
    if os.geteuid() != 0 and command != 'plan': raise ValueError('Root required')
    if command == 'plan':
        print(json.dumps({'service':NAME,'files':{k:str(v) for k,v in FILES.items()},
                          'runner':str(RUNNER),'activity':json.loads((SERVICE/'activity.json').read_text()),
                          'sequence':['install package and runtime','apply','refresh LS2','finalize'],
                          'rollback':['restore runtime','cancel owned activity','restore exact LS2 snapshots','refresh LS2']} ,indent=2))
    elif command == 'repair_beta_recovery':
        retained_repair_command()
    elif command == 'repair_root_recovery':
        retained_repair_command(tuple(args.pins), product_operation=args.product_operation)
    else:
        fd = os.open(STATE/'provision.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            print(json.dumps(globals()[command]()))
        finally: os.close(fd)

if __name__ == '__main__':
    main()

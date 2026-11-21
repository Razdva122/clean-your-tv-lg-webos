"""Schema2 C1 and schema3 capability-admitted experimental compositor routing.

The native guardian owns stop/input/control/broker leases. This interpreter owns
only the configd inverse transaction and conservative lifecycle return hints.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import time
import uuid
try: from . import c1_gate as legacy
except ImportError: import c1_gate as legacy

STATE = legacy.STATE
APP = legacy.APP
BACKEND = legacy.BACKEND
ROUTING = 'compositor-keyfilter-v1'
KEY = 'com.webos.surfacemanager.keyFilters'
STOCK = 'com.webos.app.home'
LIVE_TV = 'com.webos.app.livetv'
# Identical stock short-Home handler in LG W20P and W20H firmware 04.64.00.
WEBOS5_RIBBON_SYSTEM_UI_SHA256 = 'c61f1a202c8237eeb9ad51fa49b26f23d21d39af9aa5639a69e5a1c504585e67'
CARD = '_WEBOS_WINDOW_TYPE_CARD'
HOME = '_WEBOS_WINDOW_TYPE_HOME'
SCREENSAVER = ('com.webos.app.screensaver', '_WEBOS_WINDOW_TYPE_SCREENSAVER')
STOCK_APPINFO = Path('/usr/palm/applications/com.webos.app.home/appinfo.json')
MOUNTINFO = Path('/proc/self/mountinfo')
INPUT_BINDINGS = Path('/home/root/.config/lginputhook/keybinds.json')
OTHER_HOME_STATE = tuple(Path(p) for p in ('/media/developer/cleanyourtv',
    '/var/lib/luma-home', '/var/lib/webosbrew/homechooser'))
secure = legacy.secure
atomic = legacy.atomic
boot_identity = legacy.boot_identity
verify_ready = legacy.verify_ready


def luna(uri,payload,timeout=5,allow_failure=False):
    # The controller runs as a standalone private runtime script, independently
    # of the provisioning process's package search path and working directory.
    try: from .transport import call
    except ImportError: from transport import call
    if allow_failure:
        return call(uri,payload,timeout=timeout,allow_failure=True)
    return call(uri,payload,timeout=timeout)


def admission_valid(value):
    """A recorded observation, not a compatibility claim or model allowlist."""
    if not isinstance(value,dict) or set(value)!={'model','firmware','webos','target_sha256','target'}:
        return False
    target=value['target']
    return (isinstance(value['model'],str) and re.fullmatch(r'[A-Za-z0-9._-]{1,128}',value['model']) is not None
        and isinstance(value['firmware'],str) and legacy.VERSION.fullmatch(value['firmware']) is not None
        and isinstance(value['webos'],str) and legacy.VERSION.fullmatch(value['webos']) is not None
        and isinstance(value['target_sha256'],str) and legacy.DIGEST.fullmatch(value['target_sha256']) is not None
        and isinstance(target,dict) and set(target)=={'dev','ino','size','mtime_ns'}
        and all(type(v) is int and 0<=v<2**63 for v in target.values()) and target['ino']>0 and target['size']>=52)


def selection(root=STATE, uid=0):
    path = Path(root)/'home-backend.json'
    if not os.path.lexists(path):
        if os.path.lexists(Path(root)/'c1-keyfilter'):
            raise ValueError('Missing compositor selection; retain recovery evidence')
        return None
    value = json.loads(secure(path, uid, 8192))
    if (not isinstance(value, dict) or set(value) != {'schema','backend','experimental','routing','native_sha256','admission'}
            or type(value['schema']) is not int or value['schema'] not in (2,3)
            or value['backend'] != BACKEND or value['routing'] != ROUTING or value['experimental'] is not True
            or not isinstance(value['native_sha256'],str) or not legacy.DIGEST.fullmatch(value['native_sha256'])
            or not (legacy.admission_valid(value['admission']) if value['schema']==2 else admission_valid(value['admission']))):
        raise ValueError('Invalid compositor selection; retain recovery evidence')
    return value


def shutdown_probe():
    # Identify the running manager. Installed tools alone can be leftovers
    # from another init system and cannot establish a shutdown contract.
    init = Path('/proc/1/exe').resolve(strict=True)
    adapter = {
        'systemd': ('systemd-is-system-running-v1', '/bin/systemctl'),
        'init.upstart': ('upstart-shutdown-jobs-v1', '/sbin/initctl'),
    }.get(init.name)
    if adapter is None:
        return None
    probe, command = adapter
    command = Path(command)
    info = command.lstat()
    if command.parent.lstat().st_uid != 0 or info.st_uid != 0:
        return None
    if probe == 'upstart-shutdown-jobs-v1':
        # Match the native adapter's fallback and its non-symlink initctl.
        try:
            Path('/bin/systemctl').lstat()
        except FileNotFoundError:
            pass
        else:
            return None
        if not stat.S_ISREG(info.st_mode):
            return None
        legacy.trusted_directory(command.parent)
        for job in ('shutdown', 'reboot'):
            secure(Path('/etc/init') / (job + '.conf'))
    for path in (init, command.resolve(strict=True)):
        legacy.trusted_directory(path.parent)
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                or info.st_mode & 0o022 or not info.st_mode & 0o111):
            return None
    return probe


def reboot_resume_supported(descriptor, root=STATE, uid=0):
    """Read-only prerequisites. Actual continuation still requires a normal boot mark."""
    if not isinstance(descriptor, dict) or descriptor.get('schema') != 3:
        return False
    try:
        probe = shutdown_probe()
        if probe is None:
            return False
        # Check the boot identity source without creating a volatile session.
        boot_identity()
        proof = native(['--capabilities'], root, uid, timeout=1)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return False
    return (isinstance(proof, dict)
            and set(proof) == {'returnValue', 'backend', 'routing', 'protocol',
                               'resumable_guard', 'boot_retirement', 'shutdown_probes'}
            and proof['returnValue'] is True and proof['backend'] == BACKEND and proof['routing'] == ROUTING
            and type(proof['protocol']) is int and proof['protocol'] == 1
            and proof['resumable_guard'] is True and proof['boot_retirement'] is True
            and isinstance(proof['shutdown_probes'], list)
            and all(isinstance(name, str) for name in proof['shutdown_probes'])
            and probe in proof['shutdown_probes'])


def require_stock_home_destination():
    # On the verified webOS 5.6.2 firmware the stock key filter follows
    # defaultApps.home, independently of our configd filter or native Home file.
    reply = luna('luna://com.webos.settingsservice/getSystemSettings',
                 {'category': 'general', 'keys': ['defaultApps']}, allow_failure=True)
    settings = reply.get('settings')
    defaults = settings.get('defaultApps') if isinstance(settings, dict) else None
    if isinstance(defaults, str):
        try:
            defaults = json.loads(defaults)
        except (ValueError, RecursionError):
            defaults = None
    if (reply.get('returnValue') is not True or not isinstance(defaults, dict)
            or defaults.get('home') not in (STOCK, 'com.webos.app.fullhome')):
        raise ValueError('Explicit LG Home destination not verified')


def boot_session():
    from intent_runtime import boot_identity as startup_identity
    return startup_identity()


def validate_chain(value):
    if not isinstance(value,list) or len(value)>128:
        raise ValueError('Unknown configd filter chain')
    # Preserve arbitrary bounded JSON fields on foreign entries. Do not coerce
    # strings, missing chains, duplicate ownership, or malformed objects.
    if len(json.dumps(value, allow_nan=False).encode())>16384:
        raise ValueError('Oversized configd filter chain')
    for entry in value:
        if (not isinstance(entry,dict) or not isinstance(entry.get('file'),str)
                or not entry['file'].startswith('/') or len(entry['file'])>1024
                or not isinstance(entry.get('handler'),str)
                or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]{0,127}',entry['handler'])):
            raise ValueError('Malformed configd filter entry')
    return value


def read_chain():
    reply=luna('luna://com.webos.service.config/getConfigs', {'configNames':[KEY]})
    if not isinstance(reply,dict) or reply.get('returnValue') is not True or not isinstance(reply.get('configs'),dict):
        raise ValueError('Cannot read configd filter chain')
    return validate_chain(reply['configs'].get(KEY))


def write_chain(value,volatile=False):
    payload={'configs':{KEY:validate_chain(value)}}
    if volatile: payload['volatile']=True
    reply=luna('luna://com.webos.service.config/setConfigs', payload)
    if not isinstance(reply,dict) or reply.get('returnValue') is not True:
        raise ValueError('Configd did not acknowledge filter write')


VENDOR_FILTER = re.compile(r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js')
PRIVATE_FILTER = re.compile(r'/var/lib/clean-your-tv-(?:root(?:-updater)?|system-updater|python)(?:/|$)')
PACKAGE_FILTER = re.compile(r'/media/developer/apps/usr/palm/(applications|services)/([^/]+)(?:/|$)')


def stock_chain(chain):
    chain=validate_chain(chain)
    if (not chain or sum(e['file'].endswith('/systemUi.js') and e['handler']=='handleSystemKeys' for e in chain)!=1
            or any(not VENDOR_FILTER.fullmatch(e['file']) for e in chain)):
        raise ValueError('Stock Qt Home filter chain not verified')
    return chain


def removal_vendor_chain(chain, removed_apps):
    """Prove LG's part of the chain while keeping third-party entries opaque."""
    chain = validate_chain(chain)
    removed_services = {
        app + ('.renewal' if app == 'com.gathin.tvhome' else '.service')
        for app in removed_apps
    }
    for entry in chain:
        path = '/' + os.path.normpath(entry['file']).lstrip('/')
        package = PACKAGE_FILTER.match(path)
        if (entry['handler'] == 'cytvC1HomeKey' or PRIVATE_FILTER.match(path)
                or package and package[2] in (
                    removed_apps if package[1] == 'applications' else removed_services
                )):
            raise ValueError('CYTV filter remains during removal')
    return stock_chain([entry for entry in chain if VENDOR_FILTER.fullmatch(entry['file'])])


def vendor_script(path):
    # LG commonly aliases /usr/lib/qt5 to /usr/lib. Resolve that alias, then
    # apply the existing ownership/no-symlink checks to the actual vendor tree.
    canonical=Path(path).resolve(strict=True)
    if (canonical.name!=Path(path).name or not re.fullmatch(
            r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js',str(canonical))):
        raise ValueError('Key filter resolves outside the vendor tree')
    return secure(canonical,limit=256*1024)


def stock_bsp_overlay(mounts, overlay, critical):
    """Verify the two immutable backing images of the LG BSP overlay."""
    fields, _, _, _, options = overlay
    bsp = Path('/overlay/bsppart/bsp/usr')
    lower = 'lowerdir=' + str(bsp) + ':/usr'
    # LG can report the mount as rw while the overlay superblock is read-only.
    if (fields[3] != '/' or not re.fullmatch(r'0:[0-9]+', fields[2])
            or 'ro' not in options or 'rw' in options
            or [option for option in options
                if option.startswith(('lowerdir', 'datadir', 'upperdir', 'workdir'))] != [lower]):
        return False
    images = {}
    for entry, target, filesystem, _, flags in mounts:
        if not (target == '/' or str(bsp) == target or str(bsp).startswith(target + '/')):
            continue
        if (target not in ('/', '/overlay/bsppart') or target in images
                or entry[3] != '/' or filesystem != 'squashfs'
                or not re.fullmatch(r'179:[0-9]+', entry[2])
                or int(entry[2].split(':')[1]) >= 256
                or any('ro' not in access or 'rw' in access
                       for access in (entry[5].split(','), flags))):
            return False
        images[target] = tuple(map(int, entry[2].split(':')))
    if len(images) != 2 or images['/'] == images['/overlay/bsppart']:
        return False

    legacy.trusted_directory(bsp)
    overlay_device = tuple(map(int, fields[2].split(':')))
    for path, expected in zip((*critical, bsp), (images['/'], overlay_device, images['/overlay/bsppart'])):
        device = os.stat(path, follow_symlinks=False).st_dev
        if (os.major(device), os.minor(device)) != expected:
            return False
    return True


def require_generic_environment(chain=None, *, removed_apps=None):
    """Read-only admission. Never repair a foreign route, input or vendor file."""
    missing=luna('luna://com.webos.service.systemprofile/getProfiles',
                 {'names':['defaultApps','idleApp'],'subscribe':False},allow_failure=True)
    if (not isinstance(missing,dict) or missing.get('returnValue') is not False
            or type(missing.get('errorCode')) is not int or missing['errorCode']!=-1
            or missing.get('errorText')!='Service does not exist: com.webos.service.systemprofile.'):
        raise ValueError('System Profile absence was not confirmed')
    if any(os.path.lexists(p) for p in OTHER_HOME_STATE):
        raise ValueError('Another Home integration is present; preserve its state')
    if os.path.lexists(INPUT_BINDINGS):
        bindings=json.loads(secure(INPUT_BINDINGS,limit=65536))
        if not isinstance(bindings,dict) or '773' in bindings:
            raise ValueError('Foreign Home input binding; no takeover attempted')
    critical=(str(legacy.TARGET),str(STOCK_APPINFO.parent))
    mountinfo=MOUNTINFO.read_text()
    if len(mountinfo)>1024*1024: raise ValueError('Oversized mount table')
    mounts=[]
    for line in mountinfo.splitlines():
        fields=line.split()
        if len(fields)<10 or ' - ' not in line: raise ValueError('Unknown mount topology')
        separator=fields.index('-')
        if separator<6 or len(fields)!=separator+4: raise ValueError('Unknown mount topology')
        target=re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),fields[4])
        filesystem,source,options=fields[separator+1:]
        mounts.append((fields,target,filesystem,source,options.split(',')))
    system_image=False
    for mount in mounts:
        fields,target,filesystem,source,options=mount
        if target!='/' and any(p==target or p.startswith(target+'/') for p in critical):
            if (target=='/usr' and not system_image and filesystem=='overlay'
                    and stock_bsp_overlay(mounts,mount,critical)):
                system_image=True
                continue
            # webOS can mount its whole immutable /usr image separately. This
            # is not a bind/overlay takeover of Home. Admit only an internal
            # MMC squashfs root, with both Home paths on that exact device;
            # additional covering mounts (including stacked /usr) still refuse.
            if (target=='/usr' and not system_image and fields[3]=='/'
                    and re.fullmatch(r'179:[0-9]+',fields[2])
                    and int(fields[2].split(':')[1])<256
                    and filesystem=='squashfs'
                    and re.fullmatch(r'/dev/mmcblk[0-9]+p[0-9]+',source)
                    and all('ro' in access and 'rw' not in access
                            for access in (fields[5].split(','),options))):
                device=tuple(map(int,fields[2].split(':')))
                if all((os.major(s.st_dev),os.minor(s.st_dev))==device
                       for s in (os.stat(p,follow_symlinks=False) for p in critical)):
                    system_image=True
                    continue
            raise ValueError('Native Home is covered by a mount; no takeover attempted')
    app=json.loads(secure(STOCK_APPINFO,limit=65536))
    if (not isinstance(app,dict) or app.get('id')!=STOCK or app.get('type')!='native'
            or app.get('main') not in (str(legacy.TARGET),'file://'+str(legacy.TARGET))):
        raise ValueError('Stock native Home manifest not verified')
    chain = read_chain() if chain is None else chain
    chain = stock_chain(chain) if removed_apps is None else removal_vendor_chain(chain, removed_apps)
    for entry in chain:
        script=vendor_script(entry['file'])
        if entry['file'].endswith('/systemUi.js') and (
                b'Qt.Key_Super_L' not in script or not re.search(rb'function\s+handleSystemKeys\s*\(',script)):
            raise ValueError('Unknown Qt Home filter contract')
    try: from .emergency_reader import open_remote, query
    except ImportError: from emergency_reader import open_remote, query
    fd=open_remote()
    try:
        keys=query(fd,0x21,128)  # EVIOCGBIT(EV_KEY): advertised Home and Back.
        if any(not keys[code//8] & (1<<(code%8)) for code in (773,412)):
            raise ValueError('Emergency Home/Back input capabilities not verified')
    finally:
        os.close(fd)


def filter_entry(root=STATE):
    return {'file':str(Path(root)/'runtime/c1-home-filter.js'),'handler':'cytvC1HomeKey'}


def reconcile(chain, root, enabled):
    chain=validate_chain(chain)
    own=filter_entry(root)
    related=[entry for entry in chain if entry['file']==own['file'] or entry['handler']==own['handler']]
    if related and related != [own]:
        raise ValueError('Modified or duplicate owned filter; retain evidence')
    rest=[entry for entry in chain if entry != own]
    return [own]+rest if enabled else rest


def filter_present(root):
    chain=read_chain()
    return reconcile(chain,root,False)!=chain


def change_chain(root, enabled, uid=0):
    before=read_chain()
    generic=selection(root,uid)['schema']==3
    after=reconcile(before,root,enabled)
    if enabled:
        if generic:
            stock_chain(before)
        else:
            # On C1, replace third-party compositor hooks with the stock LG
            # chain plus CYTV. Off removes CYTV from that current chain.
            after=[filter_entry(root), *removal_vendor_chain(after[1:], (APP,))]
    directory=private_directory(root,uid)
    pending=directory/'pending.json'
    if os.path.lexists(pending):
        saved=json.loads(secure(pending,uid,65536))
        if (not isinstance(saved,dict) or set(saved)!={'schema','before','after','entry'}
                or type(saved['schema']) is not int or saved['schema']!=1 or saved['entry']!=filter_entry(root)):
            raise ValueError('Unknown pending filter transaction; retain evidence')
        reconcile(saved['before'],root,False)
        reconcile(saved['after'],root,False)
    if before==after:
        if not enabled and os.path.lexists(pending):
            if read_chain()!=before: raise ValueError('Concurrent filter recovery edit')
            pending.unlink()
        return

    receipt=directory/'ownership.json'
    own=filter_entry(root)
    if own in before:
        try: ownership=json.loads(secure(receipt,uid,4096))
        except FileNotFoundError: raise ValueError('Unknown owned filter; retain evidence')
        if (not isinstance(ownership,dict) or set(ownership)!={'schema','entry','token'}
                or type(ownership['schema']) is not int or ownership['schema']!=1
                or ownership['entry']!=own or not isinstance(ownership['token'],str)
                or not legacy.TOKEN.fullmatch(ownership['token'])):
            raise ValueError('Invalid filter ownership; retain evidence')
    if enabled:
        intent=read_intent(root,uid)
        atomic(receipt,dict(schema=1,entry=own,token=intent['token']),uid)
    pending=directory/'pending.json'
    # Durable inverse precedes every possible configd effect. Never restore an
    # old entire chain: the next operation reconciles the current foreign edits.
    atomic(pending, dict(schema=1,before=before,after=after,entry=filter_entry(root)),uid)
    if read_chain()!=before:
        raise ValueError('Concurrent configd edit; retain pending evidence')
    # Do not silently reinterpret retained schema2 persistent transactions.
    if generic:
        write_chain(after,volatile=True)
    else:
        write_chain(after)
    if read_chain()!=after:
        raise ValueError('Configd readback mismatch; retain pending evidence')
    pending.unlink()


def probe(*, removed_apps=None, retire_orphan=False):
    if os.geteuid()!=0 or sys.platform!='linux':
        raise ValueError('Compositor admission requires an existing root TV session')
    # Keep schema2 admission isolated from schema1 checkpoint prerequisites.
    before=legacy.TARGET.stat()
    data=legacy.native_home()
    info=luna('luna://com.webos.service.tv.systemproperty/getSystemInfo',
              {'keys':['modelName','firmwareVersion','sdkVersion']})
    known_c1=True
    try:
        value=legacy.admit(info,data)
    except ValueError:
        known_c1=False
        import struct
        value={key:info.get(field) for key,field in (('model','modelName'),('firmware','firmwareVersion'),('webos','sdkVersion'))} if isinstance(info,dict) else {}
        candidate=dict(value,target_sha256='0'*64,target=dict(dev=0,ino=1,size=len(data),mtime_ns=0))
        if (not isinstance(info,dict) or info.get('returnValue') is not True or struct.calcsize('P')!=4
                or len(data)<52 or data[:7]!=b'\x7fELF\x01\x01\x01' or data[18:20]!=b'\x28\0'
                or not admission_valid(candidate)):
            raise ValueError('Experimental compositor requires verified Qt Home capabilities and ARM32 native Home') from None
    if removed_apps is not None:
        chain = read_chain()
        remaining = reconcile(chain, STATE, False) if retire_orphan else chain
        require_generic_environment(remaining, removed_apps=removed_apps)
    elif known_c1:
        # Activation replaces third-party compositor hooks on C1. Verify the
        # LG portion here before any package or configd changes.
        require_generic_environment(removed_apps=(APP,))
    else:
        require_generic_environment()
    after=legacy.TARGET.stat()
    identity=lambda st: dict(dev=st.st_dev,ino=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns)
    if identity(before)!=identity(after) or not before.st_mode & 0o111:
        raise ValueError('Native Home changed during compositor admission')
    observed = read_chain()
    if removed_apps is not None:
        if observed != chain:
            raise ValueError('Concurrent configd edit during Home filter readback')
        if chain != remaining:
            # Schema 2 could leave a persistent configd entry after its state
            # directory disappeared. The fenced remover authorizes this inverse.
            write_chain(remaining)
            if read_chain() != remaining:
                raise ValueError('Configd readback mismatch during orphan filter recovery')
    return dict(value,target_sha256=hashlib.sha256(data).hexdigest(),target=identity(after))


def private_directory(root, uid=0):
    directory=Path(root)/'c1-keyfilter'
    legacy.trusted_directory(directory,uid)
    info=directory.lstat()
    if info.st_uid!=uid or stat.S_IMODE(info.st_mode)!=0o700:
        raise ValueError('Unsafe compositor state directory')
    return directory


def write_config(root, admission, token, uid=0):
    target=admission['target']
    data=('CYTV-C1-KEYFILTER-1\ntoken '+token+'\nboot '+boot_identity()+'\n'+
          ''.join(key+' '+str(target[key])+'\n' for key in ('dev','ino','size','mtime_ns'))).encode()
    atomic(private_directory(root,uid)/'config',data,uid,raw=True)


def write_intent(root, enabled, token, phase, uid=0, *, session=None):
    value=dict(schema=1,enabled=enabled,token=token,phase=phase,boot=boot_identity())
    if session is not None:
        if not valid_resume_session(value, session):
            raise ValueError('Invalid compositor boot session')
        value['session'] = session
    atomic(private_directory(root,uid)/'intent.json',value,uid)
    return value


def valid_resume_session(intent, session):
    return (intent['enabled'] and intent['phase'] == 'active'
            and isinstance(session, str)
            and re.fullmatch(re.escape(intent['boot']) + r':session-[0-9a-f]{32}', session) is not None)


def read_intent(root=STATE, uid=0):
    value=json.loads(secure(private_directory(root,uid)/'intent.json',uid,4096))
    if (not isinstance(value,dict) or set(value)-{'session'}!={'schema','enabled','token','phase','boot'}
            or type(value['schema']) is not int or value['schema']!=1 or type(value['enabled']) is not bool
            or value['phase'] not in ('disabled','starting','active','trial','recovering')
            or not isinstance(value['token'],str) or not legacy.TOKEN.fullmatch(value['token'])
            or not isinstance(value['boot'],str) or str(uuid.UUID(value['boot']))!=value['boot']
            or ('session' in value and not valid_resume_session(value, value['session']))):
        raise ValueError('Invalid compositor intent')
    return value


def prepare(root, native_sha256, admission, uid=0):
    root=Path(root)
    if (not isinstance(native_sha256,str) or not legacy.DIGEST.fullmatch(native_sha256)
            or not admission_valid(admission)):
        raise ValueError('Invalid compositor admission')
    legacy.trusted_directory(root,uid)
    if any(os.path.lexists(root/name) for name in ('home-backend.json','c1-gate','c1-keyfilter')):
        raise ValueError('Backend already prepared; retain evidence')
    (root/'c1-keyfilter').mkdir(mode=0o700)
    token=uuid.uuid4().hex
    write_config(root,admission,token,uid)
    write_intent(root,False,token,'disabled',uid)
    value=dict(schema=2 if legacy.admission_valid(admission) else 3,backend=BACKEND,experimental=True,routing=ROUTING,
               native_sha256=native_sha256,admission=admission)
    atomic(root/'home-backend.json',value,uid)
    return value


def binary(root=STATE, uid=0, *, capabilities=False):
    saved=selection(root,uid)
    if saved is None: raise ValueError('Compositor backend not selected')
    private_directory(root,uid)
    path=Path(root)/'runtime/c1-keyfilter-guard'
    raw=secure(path,uid,4*1024*1024)
    if hashlib.sha256(raw).hexdigest()!=saved['native_sha256'] or not path.stat().st_mode & 0o111:
        raise ValueError('Verified compositor guardian unavailable')
    # Old binaries can take the state lock on unknown commands. A command
    # literal in the verified bytes permits the query, but grants no capability.
    if capabilities and b'--capabilities\0' not in raw:
        raise ValueError('Guardian capability query unavailable')
    return path


def native(args, root=STATE, uid=0, timeout=12, *, allow_ui_failure=False):
    helper = binary(root, uid, capabilities=True) if args == ['--capabilities'] else binary(root, uid)
    reply=subprocess.run([str(helper),*args],stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C'},timeout=timeout,check=False)
    if len(reply.stdout)>16384:
        raise ValueError('Native compositor recovery failed; retain evidence')
    if reply.returncode:
        error = ValueError('Native compositor recovery failed; retain evidence')
        if args != ['--restore']:
            raise error
        try:
            value = json.loads(reply.stdout)
        except (ValueError, RecursionError):
            raise error from None
        if (not isinstance(value, dict) or value.get('returnValue') is not False
                or value.get('backend') != BACKEND or value.get('routing') != ROUTING):
            raise error
        reason = value.get('reason')
        error.native_reason = reason
        if not allow_ui_failure or reply.returncode != 1:
            raise error
        try:
            validate_native(dict(value, returnValue=True))
        except ValueError as invalid:
            invalid.native_reason = reason
            raise
        if reason == 'effect_busy':
            error = ValueError('Native compositor effect lock unavailable; retain evidence')
            error.native_reason = reason
            raise error
        if reason != 'ui_release_failed':
            raise error
        if not stopped_stock(value):
            error = ValueError('Native stop retirement unverified; retain evidence')
            error.native_reason = reason
            error.restore_check = 'native-stop-unverified'
            raise error
        return value
    value=json.loads(reply.stdout)
    if args==['--capabilities']:
        return value  # Only reboot_resume_supported interprets this read-only reply.
    if args==['--selfcheck']:
        expected=dict(returnValue=True,backend=BACKEND,routing=ROUTING,selfcheck=True)
        if not isinstance(value,dict) or value!=expected or value.get('selfcheck') is not True or value.get('returnValue') is not True:
            raise ValueError('Incomplete native compositor selfcheck')
        return value
    return validate_native(value)


def validate_native(value):
    if (not isinstance(value,dict) or set(value)!={'returnValue','backend','routing','state','mounted','healthy','stock_verified','stopped','token','guardian_pid','reason','profiles'}
            or value.get('returnValue') is not True
            or value.get('backend')!=BACKEND or value.get('routing')!=ROUTING or value.get('profiles',{}) is not None
            or value.get('state') not in ('stock','armed','stopped','blocked','reconnecting')
            or any(type(value.get(k)) is not bool for k in ('mounted','healthy','stock_verified','stopped'))
            or value['mounted'] or not isinstance(value.get('token'),str) or not legacy.TOKEN.fullmatch(value['token'])
            or type(value.get('guardian_pid')) is not int or value['guardian_pid']<0
            or not isinstance(value.get('reason'),str) or not re.fullmatch(r'[a-z0-9_-]{0,80}',value['reason'])
            or value['healthy'] and (value['state']!='armed' or value['stopped'] or value['guardian_pid']<=1 or value['stock_verified'])
            or value['stock_verified'] and (value['guardian_pid'] or value['healthy'])
            or value['state']=='armed' and not value['healthy']
            or value['state']=='reconnecting' and (value['stopped'] or value['stock_verified']
                                                   or value['guardian_pid']<=1 or value['reason']!='none')):
        raise ValueError('Incomplete or inconsistent compositor guardian proof')
    return value


def status(root=STATE, uid=0):
    if selection(root,uid) is None: raise ValueError('Compositor backend not selected')
    value=dict(validate_native(native(['--status'],root,uid)))
    chain=read_chain()
    clean=reconcile(chain,root,False)==chain
    value['stock_verified']=value['stock_verified'] and clean
    value['healthy']=value['healthy'] and bool(chain and chain[0]==filter_entry(root))
    value['filter_installed']=not clean
    value['routing_active']=value['healthy'] and not value['stopped']
    intent=read_intent(root,uid)
    active=value['healthy'] and not value['stopped'] and intent['token']==value['token'] and intent['phase'] in ('active','trial')
    reconnecting = (value['state']=='reconnecting' and value['filter_installed']
                    and intent['phase']=='active' and intent['enabled'] and value['token']==intent['token'])
    phase=(intent['phase'] if active else 'input-reconnecting' if reconnecting
           else 'disabled' if value['stock_verified'] else 'recovering')
    try: recovery=verify_ready()
    except (OSError,ValueError,RuntimeError,ImportError): recovery={'integrity_verified':False}
    return dict(backend=BACKEND,routing=ROUTING,experimental=True,effective=value,
        intent=dict(intent,phase=phase,enabled=bool((active or reconnecting) and intent['enabled'])),recovery=recovery,
        candidate=APP,update_home_resume_available=False,persistent_enable_available=recovery.get('integrity_verified') is True)


@contextmanager
def operation(root=STATE,uid=0, *, name='operation.lock'):
    import fcntl
    path=private_directory(root,uid)/name
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode & 0o077:
            raise ValueError('Unsafe compositor operation lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally: os.close(fd)



class ReturnPolicy:
    """A return hint is cancellable and never itself permission to launch."""
    def __init__(self,token):
        self.token=token; self.content=None; self.pending=None; self.generation=0

    def event(self,value,now):
        self.generation+=1
        pending = self.pending
        self.pending = None
        if not isinstance(value, dict):
            return
        event, app = value.get('event'), value.get('appId')
        valid_app = isinstance(app, str) and re.fullmatch(r'[A-Za-z0-9._-]{1,255}', app)
        if event == 'foreground':
            previous = self.content
            self.content = None
            if not valid_app:
                return
            window = value.get('windowType')
            if app == STOCK and window in (CARD, HOME):
                self.pending = pending or (previous or STOCK, now + 1.0)
            elif app not in (APP, STOCK) and window == CARD:
                self.content = app
        elif valid_app and event in ('stop', 'close') and value.get('windowType', CARD) == CARD:
            # SAM can omit the type on termination. Use the preceding CARD
            # observation, and keep the original deadline across stop/close.
            if pending and pending[0] == app and app != STOCK:
                self.pending = pending
            elif event == 'stop' and app == self.content:
                self.pending = (app, now + 1.0)
                self.content = None

    def due(self,now):
        return self.pending is not None and now >= self.pending[1]


def can_return(surfaces,power,proof,token,foreground=None):
    try: validate_native(proof)
    except ValueError: return False
    if (not proof['healthy'] or proof['stopped'] or proof['token']!=token
            or not isinstance(power,dict) or power.get('returnValue') is not True or power.get('state')!='Active'
            or not isinstance(surfaces,dict) or surfaces.get('returnValue') is not True): return False
    if (not isinstance(foreground,dict) or foreground.get('returnValue') is not True
            or not isinstance(foreground.get('appId'),str) or foreground['appId'] not in ('',STOCK)):
        return False
    rows=surfaces.get('foregroundAppInfo')
    if not isinstance(rows,list) or len(rows)>128: return False
    if not rows:
        return isinstance(foreground,dict) and foreground.get('returnValue') is True and foreground.get('appId')==''
    return stock_surfaces(rows)


def stock_surfaces(rows, *, allow_screensaver=False, background=None):
    for row in rows:
        # The single-display broker may omit displayId and visible.
        if (not isinstance(row,dict) or type(row.get('displayId',0)) is not int or row.get('displayId',0)!=0
                or type(row.get('visible',True)) is not bool or row.get('pip',False) is not False
                or row.get('multiview',False) is not False or row.get('viewType','normal')!='normal'):
            return False
        app, window = row.get('appId'), row.get('windowType')
        if allow_screensaver and (app, window) == SCREENSAVER:
            continue
        if background is not None and (app, window) == (background, CARD):
            continue
        if app != STOCK or window not in (CARD, HOME):
            return False
    return True


def process_start(pid):
    # /proc stat comm may contain spaces and parentheses.
    raw=Path('/proc')/str(pid)/'stat'
    fields=raw.read_text().rsplit(')',1)[1].split()
    return int(fields[19])


def stop_controller(root,uid, *, allow_reused_pid=False):
    path=private_directory(root,uid)/'controller.json'
    try: value=json.loads(secure(path,uid,4096))
    except FileNotFoundError: return
    generic=selection(root,uid)['schema']==3
    fields={'pid','start','token','boot'} if generic else {'pid','start','token'}
    if (not isinstance(value,dict) or set(value)!=fields
            or type(value['pid']) is not int or value['pid']<=1 or type(value['start']) is not int
            or not isinstance(value['token'],str) or not legacy.TOKEN.fullmatch(value['token'])):
        raise ValueError('Unknown lifecycle controller identity; retain evidence')
    if generic:
        if not isinstance(value['boot'],str) or str(uuid.UUID(value['boot']))!=value['boot']:
            raise ValueError('Unknown lifecycle controller boot; retain evidence')
        if value['boot']!=boot_identity():
            # Native routing has already stopped. A controller from a previous
            # boot cannot own any current PID; never wait for or signal it.
            path.unlink()
            return
    pid=value['pid']
    try:
        if process_start(pid)!=value['start']:
            if allow_reused_pid:
                path.unlink()
                return
            raise ValueError('Lifecycle controller PID changed; retain evidence')
        # The native stop latch makes the controller exit on its next bounded
        # status read. Never signal a PID across a check/kill race on old kernels
        # without pidfd; uncertainty keeps the inert filter and recovery record.
        end=time.monotonic()+3
        while time.monotonic()<end:
            try:
                if process_start(pid)!=value['start']: break
                # A zombie no longer executes a launch and may await its parent.
                state=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[0]
                if state=='Z': break
            except FileNotFoundError: break
            time.sleep(.05)
        else: raise ValueError('Lifecycle controller did not retire')
    except ProcessLookupError: pass
    except FileNotFoundError: pass
    path.unlink()


def stopped_stock(proof):
    return (proof['state'] == 'stopped' and proof['stopped'] and proof['stock_verified']
            and not proof['healthy'] and proof['guardian_pid'] == 0)


def uses_webos5_ribbon_handler(chain):
    for entry in stock_chain(chain):
        if entry['file'].endswith('/systemUi.js') and entry['handler'] == 'handleSystemKeys':
            return hashlib.sha256(vendor_script(entry['file'])).hexdigest() == WEBOS5_RIBBON_SYSTEM_UI_SHA256
    return False


def verify_webos5_ribbon_route(chain):
    if not uses_webos5_ribbon_handler(chain):
        raise ValueError('Stock LG Home ribbon handler unverified; retain evidence')
    reply = luna('luna://com.webos.settingsservice/getSystemSettings',
                 {'category': 'general', 'keys': ['defaultApps']})
    settings = reply.get('settings') if isinstance(reply, dict) else None
    defaults = settings.get('defaultApps') if isinstance(settings, dict) else None
    if isinstance(defaults, str):
        defaults = json.loads(defaults)
    if (not isinstance(reply, dict) or reply.get('returnValue') is not True
            or not isinstance(defaults, dict) or defaults.get('home') != STOCK):
        raise ValueError('Stock LG Home ribbon destination unverified; retain evidence')


def restore_for_removal(root, uid):
    with operation(root, uid):
        return restore_locked(root, uid, for_removal=True)


def has_resume_session(root, uid):
    try:
        return 'session' in read_intent(root, uid)
    except (OSError, ValueError):
        return False


def can_restore_routing_only(root, uid):
    if has_resume_session(root, uid):
        return True
    try:
        require_stock_home_destination()
        return True
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return False


def restore_locked(root,uid, *, for_removal=False, explicit_restore=False, routing_only=False):
    verify_destination = routing_only or (
        explicit_restore and not for_removal and has_resume_session(root, uid)
        and reboot_resume_supported(selection(root, uid), root, uid))
    ui_failure = None
    try:
        if verify_destination:
            native(['--restore-routing'],root,uid)
        elif for_removal or explicit_restore:
            restored = native(['--restore'], root, uid, allow_ui_failure=True)
            if restored['returnValue'] is False:
                ui_failure = restored
        else:
            native(['--restore'],root,uid)
    except Exception as error:
        if not for_removal and not getattr(error, 'restore_check', None):
            error.restore_check = 'native-restore-unverified'
        raise
    check = 'native-stop-unverified'
    try:
        after=validate_native(native(['--status'],root,uid))
        if ui_failure is not None and (not stopped_stock(after) or after['token'] != ui_failure['token']):
            raise ValueError('Native stop retirement unverified; retain evidence')
        selected = selection(root, uid)
        generic = selected['schema'] == 3
        if after['healthy'] or not after['stopped'] or after['guardian_pid']:
            raise ValueError('Native stop retirement unverified; retain evidence')
        if not generic and not after['stock_verified']:
            if not for_removal:
                check = 'stock-home-unverified'
            raise ValueError('Native stop retirement unverified; retain evidence')
        if not for_removal:
            check = 'intent-write-failed'
        write_intent(root,False,after['token'],'recovering',uid)
        if not for_removal:
            check = 'controller-stop-unverified'
        # Some TVs reuse the kernel boot ID after reboot. A different process
        # start time proves the recorded controller is gone, even on those TVs.
        stop_controller(root, uid, allow_reused_pid=for_removal and generic and stopped_stock(after))
        check = 'stock-routing-unverified'
        change_chain(root,False,uid)
        if not after['stock_verified']:
            if not for_removal:
                check = 'stock-home-unverified'
            raise ValueError('Home identity changed; owned filter removed, recovery evidence retained')
        if verify_destination:
            stock_chain(read_chain())
            require_stock_home_destination()
            current = validate_native(native(['--status'], root, uid))
            if not stopped_stock(current) or current['token'] != after['token']:
                raise ValueError('Stock LG Home routing unverified; retain evidence')
        elif ui_failure is not None:
            check = 'stock-foreground-unverified'
            foreground = luna('luna://com.webos.applicationManager/getForegroundAppInfo', {})
            app = (foreground.get('appId') if isinstance(foreground, dict)
                   and foreground.get('returnValue') is True else None)
            # On webOS 5 SAM can report the Live TV card under the stock Home ribbon.
            ribbon = (for_removal and generic and app == LIVE_TV
                      and selected['admission']['webos'].startswith('5.'))
            # webOS 6 keeps the content card in SAM while stock Home is an
            # independent HOME surface above it (#440).
            overlay = (for_removal and generic and selected['admission']['webos'].startswith('6.')
                       and isinstance(app, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,254}', app)
                       and app != STOCK and not app.startswith('com.cleanyourtv.')
                       and app not in ('com.local.nativehome', 'com.gathin.tvhome', SCREENSAVER[0], LIVE_TV))
            if app != STOCK and not (ribbon or overlay):
                raise ValueError('Stock LG Home foreground unverified; retain evidence')
            # SAM can report LG Home underneath an application overlay. The LG
            # screensaver can also cover its stock card after idle (#615).
            check = 'stock-surface-unverified'
            surfaces = luna('luna://com.webos.surfacemanager/getForegroundAppInfo', {})
            rows = surfaces.get('foregroundAppInfo') if isinstance(surfaces, dict) else None
            if (not isinstance(rows, list) or not 1 <= len(rows) <= 128
                    or surfaces.get('returnValue') is not True
                    or not stock_surfaces(rows, allow_screensaver=not (ribbon or overlay),
                                          background=app if ribbon or overlay else None)
                    or not any(row['appId'] == STOCK and row.get('visible', True) is True
                               and (not (ribbon or overlay) or row['windowType'] == HOME) for row in rows)
                    or overlay and (len(rows) != 2 or sum(row['appId'] == app for row in rows) != 1)):
                raise ValueError('Stock LG Home surface unverified; retain evidence')
            check = 'stock-routing-unverified'
            chain = read_chain()
            if ribbon:
                verify_webos5_ribbon_route(chain)
            if overlay:
                stock_chain(chain)
                foreground = luna('luna://com.webos.applicationManager/getForegroundAppInfo', {})
                if (not isinstance(foreground, dict) or foreground.get('returnValue') is not True
                        or foreground.get('appId') != app):
                    raise ValueError('Content foreground changed during stock Home verification')
            current = native(['--status'], root, uid)
            if (not stopped_stock(current) or current['token'] != after['token']
                    or reconcile(chain, root, False) != chain or (ribbon or overlay) and read_chain() != chain):
                raise ValueError('Stock LG Home routing unverified; retain evidence')
    except Exception as error:
        if ui_failure is not None:
            error.native_reason = ui_failure['reason']
        if ui_failure is not None or not for_removal:
            error.restore_check = check
        raise
    try:
        write_intent(root,False,after['token'],'disabled',uid)
    except Exception as error:
        if not for_removal:
            error.restore_check = 'intent-write-failed'
        raise
    return 'restored'


def read_handshake(fd,expected,children,seconds=8):
    end=time.monotonic()+seconds; response=b''
    while time.monotonic()<end:
        if any(child.poll() is not None for child in children): break
        if select.select([fd],[],[],min(.1,max(0,end-time.monotonic())))[0]:
            chunk=os.read(fd,256)
            if not chunk: break
            response+=chunk
            if len(response)>128 or b'\n' in response: break
    if response!=expected or any(child.poll() is not None for child in children):
        raise ValueError('Independent compositor protection startup unverified')


def start_controller(root,uid,token,control_fd,log):
    from python_binding import command
    ready_read,ready_write=os.pipe()
    child=None
    try:
        child=subprocess.Popen([command(root),str(Path(root)/'runtime/c1_keyfilter.py'),
            '--watch',token,str(control_fd),str(ready_write)],pass_fds=(control_fd,ready_write),
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
        os.close(ready_write); ready_write=None
        record=dict(pid=child.pid,start=process_start(child.pid),token=token)
        if selection(root,uid)['schema']==3: record['boot']=boot_identity()
        atomic(private_directory(root,uid)/'controller.json',record,uid)
        read_handshake(ready_read,('WATCH '+token+'\n').encode(),[child])
        return child
    except BaseException:
        if child is not None and child.poll() is None:
            child.terminate()
            try: child.wait(timeout=2)
            except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=1)
        raise
    finally:
        os.close(ready_read)
        if ready_write is not None: os.close(ready_write)


def rotate_boot_config(root, uid, admission, prior_token, token):
    # Use the native guardian's state lock. A direct Restore may latch Off
    # independently of the Python operation lock.
    with operation(root, uid, name='lock'):
        directory = private_directory(root, uid)
        config = secure(directory/'config', uid, 512)
        if not config.startswith(b'CYTV-C1-KEYFILTER-1\ntoken ' + prior_token.encode('ascii') + b'\n'):
            raise ValueError('Preceding compositor token changed')
        try:
            stop = secure(directory/'stopped', uid, 160)
        except FileNotFoundError:
            pass
        else:
            match = re.fullmatch(rb'([0-9a-f]{32}) ([a-z_]{1,63})\n', stop)
            if match is None or (match[1] == prior_token.encode('ascii') and match[2] != b'normal_shutdown'):
                raise ValueError('Preceding compositor stop requires explicit Enable')
        write_config(root, admission, token, uid)


def enable_locked(root,uid,seconds, *, session=None, resume_token=None):
    descriptor=selection(root,uid)
    if descriptor is None: raise ValueError('Compositor backend not selected')
    if verify_ready().get('integrity_verified') is not True:
        raise ValueError('Verified recovery manifest required')
    current=validate_native(native(['--status'],root,uid))
    if current['healthy'] or current['guardian_pid'] or not current['stock_verified']:
        raise ValueError('Restore previous compositor attempt before enabling')
    # Existing own entries, including interrupted attempts, require explicit Off.
    before=read_chain()
    if reconcile(before,root,False)!=before or os.path.lexists(Path(root)/'c1-keyfilter/pending.json'):
        raise ValueError('Restore interrupted filter transaction before enabling')
    if probe()!=descriptor['admission']:
        raise ValueError('C1 admission changed')
    resumable = reboot_resume_supported(descriptor, root, uid)
    if session is not None and not resumable:
        raise ValueError('Compositor boot resume capability changed')
    if resumable:
        try:
            require_stock_home_destination()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            if resume_token is not None or uses_webos5_ribbon_handler(before):
                raise
            # Existing generic same-session activation still has guard leases
            # and emergency Stop. It has no authority to arm on another boot.
            session = None
    from helper_bridge import require_idle
    require_idle()
    helper=binary(root,uid)
    # Verify the filter is protected before configd is allowed to read it.
    secure(Path(root)/'runtime/c1-home-filter.js',uid,65536)
    if resume_token is not None:
        from boot_gate import observation
        if observation() != (True, False) or boot_session() != session:
            raise ValueError('Normal compositor startup proof changed')
    token=uuid.uuid4().hex
    if resume_token is not None:
        rotate_boot_config(root, uid, descriptor['admission'], resume_token, token)
    else:
        write_config(root,descriptor['admission'],token,uid)
    write_intent(root,seconds==0,token,'starting',uid)
    fds=[]; children=[]
    try:
        change_chain(root,True,uid)
        input_read,input_write=os.pipe(); fds.extend([input_read,input_write])
        control_read,control_write=os.pipe(); fds.extend([control_read,control_write])
        ready_read,ready_write=os.pipe(); fds.extend([ready_read,ready_write])
        log=os.open(private_directory(root,uid)/'native.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
        fds.append(log)
        info=os.fstat(log)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode & 0o077:
            raise ValueError('Unsafe compositor recovery log')
        controller=start_controller(root,uid,token,control_write,log); children.append(controller)
        os.close(control_write); fds.remove(control_write)
        from python_binding import command
        observer=subprocess.Popen([command(root),str(Path(root)/'runtime/emergency_reader.py'),
            str(input_write),'--reconnect-on-disconnect' if seconds else '--recover-input'],
            pass_fds=(input_write,),stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
        children.append(observer)
        os.close(input_write); fds.remove(input_write)
        guard_mode = '--guard-resumable' if session is not None else '--guard'
        if not seconds: guard_mode += '-reconnect'
        guard=subprocess.Popen([str(helper),guard_mode,token,str(input_read),str(control_read),str(ready_write),str(seconds)],
            pass_fds=(input_read,control_read,ready_write),stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            env={'PATH':'/usr/bin:/bin','LANG':'C'},start_new_session=True,close_fds=True)
        children.append(guard)
        for fd in (input_read,control_read,ready_write): os.close(fd); fds.remove(fd)
        read_handshake(ready_read,('ARMED '+token+'\n').encode(),children)
        after=validate_native(native(['--status'],root,uid))
        if not after['healthy'] or after['token']!=token:
            raise ValueError('Guardian stopped during activation')
        write_intent(root,seconds==0,token,'trial' if seconds else 'active',uid,session=session)
        result=status(root,uid)
        if not result['effective']['healthy']: raise ValueError('Compositor lease not active')
        return result
    except BaseException:
        try:
            if resume_token is None:
                if session is not None:
                    restore_locked(root, uid, routing_only=True)
                else:
                    restore_locked(root, uid, explicit_restore=True)
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=1)
        raise
    finally:
        for fd in fds: os.close(fd)


def resume_after_boot(root, uid, intent, session):
    # Consume the previous session's authorization before any new filter write.
    # An interruption must not allow the boot callback to submit Enable again.
    write_intent(root, False, intent['token'], 'recovering', uid)
    chain = read_chain()
    if reconcile(chain, root, False) != chain:
        raise ValueError('Previous compositor filter is still present')
    stock_chain(chain)
    retired = validate_native(native(['--retire-boot', intent['token']], root, uid))
    eligible = (retired['state'], retired['stopped'], retired['reason']) in (
        ('stock', False, 'boot_retired'), ('stopped', True, 'normal_shutdown'))
    if (not eligible or not retired['stock_verified'] or retired['token'] != intent['token']
            or retired['guardian_pid']):
        raise ValueError('Previous compositor guardian retirement unverified')
    stop_controller(root, uid, allow_reused_pid=True)
    return enable_locked(root, uid, 0, session=session, resume_token=intent['token'])


def boot_resume_observation(root, uid):
    from boot_gate import wait
    try:
        intent = read_intent(root, uid)
        previous = intent.get('session')
        if previous is not None:
            session = boot_session()
            if session != previous:
                # Off can acquire the operation lock while startup is still pending.
                return intent, session, wait()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        pass
    return None, None, False


def execute(mode,transaction=None,root=STATE,uid=0):
    if mode=='status': return status(root,uid)
    resumable = mode in ('boot', 'enable') and reboot_resume_supported(selection(root, uid), root, uid)
    previous, session, normal = (boot_resume_observation(root, uid)
                                 if mode == 'boot' and resumable else (None, None, False))
    resumed = None
    with operation(root,uid):
        if mode=='boot' and not os.path.lexists(Path(root)/'c1-keyfilter/pending.json'):
            try:
                intent = read_intent(root, uid)
                # ActivityManager can deliver recovery while Home is already
                # armed. Keep only a verified activation from this boot.
                if (intent['enabled'] and intent['phase'] == 'active'
                        and intent['boot'] == boot_identity() and intent != previous):
                    current = status(root, uid)
                    if (current['intent'] == intent
                            and current['recovery'].get('integrity_verified') is True):
                        return current
                if resumable and normal and intent == previous:
                    from boot_gate import observation
                    if observation() == (True, False) and boot_session() == session:
                        resumed = resume_after_boot(root, uid, intent, session)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                pass  # Unverified activation still needs stock Home recovery.
        if resumed is None and mode in ('restore','boot'):
            if mode == 'boot' and resumable and (previous is not None or can_restore_routing_only(root, uid)):
                return restore_locked(root, uid, routing_only=True)
            return restore_locked(root,uid,explicit_restore=mode=='restore')
        if mode in ('enable','trial','intent-trial','emergency-trial'):
            if mode == 'enable' and resumable:
                return enable_locked(root, uid, 0, session=boot_session())
            return enable_locked(root,uid,0 if mode=='enable' else 60)
    if resumed is not None:
        # Startup policy owns its own operation lock and validates the new
        # session again before a UI effect. Its failure cannot undo activation.
        try:
            startup_after_boot(resumed, root=root, uid=uid)
        except Exception:
            pass
        return resumed
    raise ValueError('Unsupported compositor lifecycle operation')


def startup_load_policy(root, uid):
    from intent_runtime import startup_load
    return startup_load(lambda: json.loads(secure(Path(root)/'startup-policy.json', uid, 4096)))


def startup_is_active(value):
    intent, proof = value['intent'], value['effective']
    return (intent['enabled'] is True and intent['phase'] == 'active'
            and proof['healthy'] is True and proof['stopped'] is False
            and proof['token'] == intent['token']
            and value['recovery'].get('integrity_verified') is True)


def startup_status(root=STATE, uid=0):
    return dict(sources=startup_load_policy(root, uid), active=startup_is_active(status(root, uid)))


def startup_configure(sources, root=STATE, uid=0):
    from intent_runtime import startup_validate
    sources = startup_validate(sources)
    with operation(root, uid):
        startup_load_policy(root, uid)  # An unreadable old policy remains recovery evidence.
        current = status(root, uid)
        if not startup_is_active(current):
            raise ValueError('Change Home is off or recovery is unverified')
        atomic(Path(root)/'startup-policy.json', dict(version=2, sources=sources), uid)
        return dict(sources=sources, active=True)


def startup_entry(args, root=STATE, uid=0):
    if args == ['status']:
        return startup_status(root, uid)
    if args == ['configure']:
        raw = sys.stdin.buffer.read(2049)
        if len(raw) > 2048:
            raise ValueError('Oversized startup sources')
        return startup_configure(json.loads(raw), root, uid)
    raise ValueError('Unknown startup operation')


def startup_require_session(value, expected):
    from boot_gate import observation
    intent = value['intent']
    if (not startup_is_active(value) or intent != expected
            or intent['boot'] != boot_identity()
            or not valid_resume_session(intent, intent.get('session'))
            or intent['session'] != boot_session()
            or observation() != (True, False)):
        raise ValueError('Inactive native startup session')


def startup_source(reply, deadline):
    from intent_runtime import startup_CHANNEL, startup_YOUTUBE
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        return None
    rows = reply.get('foregroundAppInfo')
    if not isinstance(rows, list) or len(rows) != 1:
        return None
    row = rows[0]
    if (not isinstance(row, dict) or row.get('windowType') != CARD
            or type(row.get('displayId', 0)) is not int or row.get('displayId', 0) != 0
            or row.get('visible', True) is not True or row.get('pip', False) is not False
            or row.get('multiview', False) is not False or row.get('viewType', 'normal') != 'normal'):
        return None
    app = row.get('appId')
    if app == LIVE_TV:
        return 'tv'
    if app == startup_YOUTUBE:
        return 'youtube'
    if app == startup_CHANNEL:
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Native startup deadline')
        metadata = luna('luna://com.webos.applicationManager/getAppInfo', {'id':app},
                             timeout=min(.5, remaining))
        if not isinstance(metadata, dict) or metadata.get('returnValue') is not True:
            return None
        info = metadata.get('appInfo')
        store = '/media/cryptofs/apps/usr/palm/applications/'+app
        expected = dict(id=app, type='web', vendor='LifeStream ltd.', folderPath=store,
                        activeFolderPath=store)
        if (isinstance(info, dict) and all(info.get(k) == v for k, v in expected.items())
                and info.get('CPApp') is True and info.get('internalInstallationOnly') is True):
            return 'tv'
    # HDMI, unknown apps, LG Home and current Root are never startup permission.
    return None


def startup_receipt(root, uid):
    path = private_directory(root, uid)/'startup-attempt.json'
    try:
        value = json.loads(secure(path, uid, 4096))
    except FileNotFoundError:
        return path, None
    if (not isinstance(value, dict) or set(value) != {'schema','boot','session','token'}
            or type(value['schema']) is not int or value['schema'] != 1
            or not isinstance(value['boot'], str)
            or re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value['boot']) is None
            or not isinstance(value['token'], str) or not legacy.TOKEN.fullmatch(value['token'])
            or not valid_resume_session(dict(enabled=True,phase='active',boot=value['boot']), value['session'])):
        raise ValueError('Invalid startup launch receipt; retain evidence')
    return path, value


def startup_after_boot(result, root=STATE, uid=0):
    """Call outside the operation lock only after authenticated boot resumption.

    The session is consumed before the native launch barrier. A lost launch
    acknowledgement must never become a second attempt that steals foreground.
    """
    try:
        with operation(root, uid):
            expected = result['intent']
            startup_require_session(result, expected)
            startup_require_session(status(root, uid), expected)
            path, prior = startup_receipt(root, uid)
            attempt = dict(schema=1, boot=expected['boot'], session=expected['session'], token=expected['token'])
            if prior is not None and prior['session'] == attempt['session']:
                return 'already-attempted'
            sources = startup_load_policy(root, uid)
            deadline = time.monotonic()+1.5
            reply = luna('luna://com.webos.surfacemanager/getForegroundAppInfo', {}, timeout=.5)
            selected = startup_source(reply, deadline)
            if time.monotonic() >= deadline or not sources.get(selected, False):
                return 'preserved'
            # Recheck both lifecycle and presentation at the submission boundary.
            startup_require_session(status(root, uid), expected)
            fresh = luna('luna://com.webos.surfacemanager/getForegroundAppInfo', {}, timeout=.5)
            if fresh != reply or time.monotonic() >= deadline:
                return 'preserved'
            startup_require_session(status(root, uid), expected)
            if time.monotonic() >= deadline:
                return 'preserved'
            atomic(path, attempt, uid)
            launch_return(root, uid, expected['token'])
            return 'launched'
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError):
        return 'unavailable'


def return_ready(root,uid,token,changed):
    # Every RPC can deliver a lifecycle change concurrently. Discard the entire
    # delayed hint after any such message, including unknown/partial messages.
    intent=read_intent(root,uid)
    if intent['token']!=token or intent['phase'] not in ('active','trial'): return False
    power=luna('luna://com.webos.service.tvpower/power/getPowerState',{},timeout=.3)
    if changed(): return False
    surfaces=luna('luna://com.webos.surfacemanager/getForegroundAppInfo',{},timeout=.3)
    if changed(): return False
    foreground=luna('luna://com.webos.applicationManager/getForegroundAppInfo',{},timeout=.3)
    if changed(): return False
    proof=validate_native(native(['--status'],root,uid,timeout=.3))
    if changed(): return False
    if selection(root,uid)['schema']==3 and (not filter_present(root) or changed()): return False
    intent=read_intent(root,uid)
    return (intent['token']==token and intent['phase'] in ('active','trial')
            and can_return(surfaces,power,proof,token,foreground))


def launch_return(root,uid,token):
    # Native statelock serializes this fixed Root launch against stop/restore.
    # A stale controller cannot issue a free-standing LS2 launch after Off.
    proof=validate_native(native(['--home',token],root,uid,timeout=2.5))
    if not proof['healthy'] or proof['stopped'] or proof['token']!=token:
        raise ValueError('Lifecycle launch barrier lost the active token')
    return proof


def watch(token,control,ready,root=STATE,uid=0):
    """Persistent LS2 controller; loss of subscription retires CONTROL lease."""
    if not legacy.TOKEN.fullmatch(token): raise ValueError('Invalid controller token')
    # Fixed subscription only; stdin remains open for old luna-send versions.
    child=subprocess.Popen(['/usr/bin/luna-send','-i','luna://com.webos.applicationManager/getAppLifeEvents',
        '{"subscribe":true}'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    os.set_blocking(control,False)
    policy=ReturnPolicy(token); buffer=b''; initialized=False; armed=False; started=time.monotonic()
    def send(data):
        if os.write(control,data)!=len(data): raise ValueError('Partial controller health write')
    try:
        while child.poll() is None:
            now=time.monotonic()
            if not initialized and now-started>5: raise ValueError('Lifecycle subscription timeout')
            if select.select([child.stdout],[],[],.1)[0]:
                data=os.read(child.stdout.fileno(),8192)
                if not data: raise ValueError('Lifecycle subscription ended')
                buffer+=data
                if len(buffer)>65536: raise ValueError('Oversized lifecycle subscription')
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    if not line.strip(): continue
                    value=json.loads(line)
                    if not isinstance(value,dict) or value.get('returnValue') is not True:
                        raise ValueError('Lifecycle subscription failed')
                    if not initialized:
                        if value.get('subscribed') is not True: raise ValueError('Lifecycle subscription not acknowledged')
                        send(b'READY\n')
                        if os.write(ready,('WATCH '+token+'\n').encode())!=len('WATCH '+token+'\n'):
                            raise ValueError('Controller readiness write failed')
                        os.close(ready); ready=None; initialized=True
                    if 'event' in value: policy.event(value,time.monotonic())
            if not initialized: continue
            intent=read_intent(root,uid)
            if intent['token']!=token or intent['phase'] not in ('starting','active','trial'):
                raise ValueError('Lifecycle intent inactive')
            # At most a brief startup grace while the parent starts the guard.
            proof=validate_native(native(['--status'],root,uid,timeout=.3))
            live=proof['token']==token and proof['healthy'] and not proof['stopped']
            if selection(root,uid)['schema']==3 and not filter_present(root):
                raise ValueError('Volatile compositor filter lost; explicit Enable required')
            if live: armed=True
            recovering = proof['token']==token and proof['state']=='reconnecting'
            if not live and not recovering and (armed or time.monotonic()-started>8):
                raise ValueError('Controller token inactive')
            send(b'PING\n')
            if recovering:
                policy.pending=None
            if live and policy.due(time.monotonic()):
                policy.pending=None
                generation=policy.generation
                changed=lambda: generation!=policy.generation or bool(buffer.strip()) or bool(select.select([child.stdout],[],[],0)[0])
                if return_ready(root,uid,token,changed):
                    send(b'PING\n')
                    launch_return(root,uid,token)
    finally:
        try: send(b'LOST\n')
        except OSError: pass
        os.close(control)
        if ready is not None: os.close(ready)
        if child.poll() is None: child.terminate()
        try: child.communicate(timeout=1)
        except subprocess.TimeoutExpired: child.kill(); child.communicate()


if __name__=='__main__':
    if os.geteuid()!=0 or len(sys.argv)!=5 or sys.argv[1]!='--watch':
        raise SystemExit('Root and private controller channels required')
    watch(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]))

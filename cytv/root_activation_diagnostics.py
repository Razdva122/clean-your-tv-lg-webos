"""Passive, bounded retained-Root observations; never recovery authority.

The host sends this stdlib-only source through verified Python's stdin. No retained
module is imported and no TV file is written. The cursor is ephemeral host data,
not report content or proof that another activation cannot run concurrently.
"""
import json

COMPOSITOR_STOPS = ('broker_expired', 'controller_expired', 'controller_lost', 'escape',
                    'explicit_off', 'external_stop', 'home_changed', 'home_failed',
                    'input_expired', 'input_lost', 'journal_failed', 'lease_expired',
                    'lg_home', 'malformed_input', 'ready_failed', 'signal',
                    'state_busy', 'trial_expired')

PROGRAM = r'''
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = '/var/lib/clean-your-tv-root'
INSTALLED = '/media/developer/apps'
BOOT = '/proc/sys/kernel/random/boot_id'
TOKEN = rb'[a-f0-9]{32}'
BOOT_ID = rb'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'
COMPOSITOR_STOPS = COMPOSITOR_STOP_VALUES
COMPONENTS = {'root':'com.cleanyourtv.root.preview',
              'root_updater':'com.cleanyourtv.root.updater',
              'system_updater':'com.cleanyourtv.system.updater'}
REASONS = ('transaction-mismatch','binding-restored','generation-mismatch',
           'token-mismatch','boot-mismatch','phase-inactive','failsafe-present')
LIMIT = 65536


def read(path, uid, tail=False, *, private=False, limit=LIMIT):
    path=Path(path)
    for parent in (path.parent,*path.parent.parents):
        info=parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,uid)
                or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise ValueError('unsafe')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1
                or info.st_mode & (0o077 if private or tail else 0o022) or not tail and info.st_size>limit):
            raise ValueError('unsafe')
        start=max(0,info.st_size-limit) if tail else 0
        os.lseek(fd,start,os.SEEK_SET);raw=b''
        while len(raw)<info.st_size-start:
            chunk=os.read(fd,info.st_size-start-len(raw))
            if not chunk:raise ValueError('changed')
            raw+=chunk
        after=os.fstat(fd);current=path.lstat()
        if ((current.st_dev,current.st_ino)!=(info.st_dev,info.st_ino)
                or any(getattr(info,k)!=getattr(after,k) for k in
                       ('st_size','st_mode','st_nlink','st_uid','st_mtime_ns','st_ctime_ns'))):
            raise ValueError('changed')
        return raw,info,start
    finally:os.close(fd)


def version(value):
    return value if type(value) is str and re.fullmatch(r'\d{1,5}(?:\.\d{1,5}){1,2}(?:-\d{1,6})?',value) else None


def unique_json(raw):
    def pairs(items):
        value = dict(items)
        if len(value) != len(items):
            raise ValueError('duplicate key')
        return value
    return json.loads(raw, object_pairs_hook=pairs)


def compositor_identity(directory, uid):
    info = directory.lstat()
    if info.st_uid != uid or not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('unsafe compositor directory')
    config, config_info, _ = read(directory/'config', uid, private=True, limit=512)
    intent, intent_info, _ = read(directory/'intent.json', uid, private=True, limit=4096)
    match = re.fullmatch(rb'CYTV-C1-KEYFILTER-1\ntoken ('+TOKEN+rb')\nboot ('+BOOT_ID+
                         rb')\ndev [0-9]{1,20}\nino [0-9]{1,20}\nsize [0-9]{1,20}\nmtime_ns [0-9]{1,20}\n', config)
    if not match:
        raise ValueError('invalid config')
    token, boot = (item.decode('ascii') for item in match.groups())
    value = unique_json(intent)
    if (type(value) is not dict or set(value) != {'schema', 'enabled', 'token', 'phase', 'boot'}
            or type(value['schema']) is not int or value['schema'] != 1 or type(value['enabled']) is not bool
            or value['phase'] not in ('disabled', 'starting', 'active', 'trial', 'recovering')):
        raise ValueError('invalid intent')
    stamp = tuple((item.st_dev, item.st_ino, item.st_ctime_ns) for item in (info, config_info, intent_info))
    return (token, boot), (value['token'], value['boot']), (stamp, config, intent)


def guardian_release(directory, uid, token):
    try:
        raw, _, offset = read(directory/'native.log', uid, tail=True)
    except (OSError, ValueError):
        return None
    lines = raw.split(b'\n')[bool(offset):-1]
    keys = {'returnValue', 'backend', 'routing', 'state', 'mounted', 'healthy',
            'stock_verified', 'stopped', 'token', 'guardian_pid', 'reason', 'profiles'}
    for line in reversed(lines):
        if len(line) > 1024 or not line.startswith(b'{'):
            continue
        try:
            value = unique_json(line)
        except (ValueError, RecursionError):
            continue
        if (type(value) is dict and set(value) == keys and value['returnValue'] is False
                and value['backend'] == 'c1-native-gate' and value['routing'] == 'compositor-keyfilter-v1'
                and value['state'] == 'stopped' and value['mounted'] is False and value['healthy'] is False
                and type(value['stock_verified']) is bool and value['stopped'] is True
                and value['token'] == token and type(value['guardian_pid']) is int and value['guardian_pid'] == 0
                and value['reason'] == 'ui_release_failed' and value['profiles'] is None):
            return 'ui_release_failed'
    return None


def stop_records(directory, uid):
    records = []
    for name in ('outcome', 'stopped'):
        try:
            raw, info, _ = read(directory/name, uid, private=True, limit=160)
        except FileNotFoundError:
            records.append(None)
        else:
            records.append((raw, info.st_dev, info.st_ino, info.st_mode, info.st_uid,
                            info.st_nlink, info.st_mtime_ns, info.st_ctime_ns))
    return records


def compositor(directory, uid, cursor):
    try:
        identity, intent, before = compositor_identity(directory, uid)
        if intent != identity:
            return {'status':'inconsistent'}, None
        with open(BOOT, 'rb') as stream:
            boot = stream.read(38)
        if not re.fullmatch(BOOT_ID+rb'\n', boot):
            raise ValueError('invalid kernel boot identity')
        token = identity[0]
        if identity[1].encode('ascii') + b'\n' != boot:
            return {'status':'stale'}, None
        reasons = set()
        stale = False
        stops = stop_records(directory, uid)
        for record in stops:
            if record is None:
                continue
            match = re.fullmatch(rb'('+TOKEN+rb') ([a-z_]{1,63})\n', record[0])
            if not match:
                raise ValueError('invalid stop record')
            seen, reason = (item.decode('ascii') for item in match.groups())
            if seen != token:
                stale = True
            else:
                if reason not in COMPOSITOR_STOPS:
                    raise ValueError('unknown stop reason')
                reasons.add(reason)
        release = guardian_release(directory, uid, token) if reasons else None
        try:
            after_stops = stop_records(directory, uid)
            after = compositor_identity(directory, uid)[2]
        except (OSError, ValueError, RecursionError):
            return {'status':'inconsistent'}, None
        if before != after or stops != after_stops or len(reasons) > 1:
            return {'status':'inconsistent'}, None
        if not reasons:
            return {'status':'stale' if stale else 'missing'}, list(identity)
        previous = cursor.get('compositor') if type(cursor) is dict else None
        started = (type(previous) is list and len(previous) == 2
                   and previous[0] != token and previous[1] == identity[1])
        result = {'status':'read', 'scope':'since-enable' if started else 'retained',
                  'original_stop':reasons.pop()}
        if release:
            result['guardian_release'] = release
        return result, list(identity)
    except FileNotFoundError:
        return {'status':'missing'}, None
    except (OSError, ValueError, RecursionError):
        return {'status':'unsafe'}, None


def snapshot(root=ROOT, installed=INSTALLED, uid=0, cursor=None):
    root=Path(root);installed=Path(installed)
    out={'components':{},'component_reads':{}}
    for key,app in COMPONENTS.items():
        try:
            raw,_,_=read(installed/('usr/palm/applications/'+app+'/appinfo.json'),uid)
            value=json.loads(raw)
            if type(value) is not dict or value.get('id')!=app or not version(value.get('version')):raise ValueError('invalid')
            out['components'][key]=value['version'];out['component_reads'][key]='read'
        except FileNotFoundError:out['component_reads'][key]='missing'
        except (OSError,ValueError,TypeError):out['component_reads'][key]='unsafe'
    try:
        value=json.loads(read(root/'release.json',uid)[0])
        if type(value) is dict and version(value.get('version')):out['runtime_release']=value['version']
    except (OSError,ValueError,TypeError):pass
    try:
        raw,info,start=read(root/'emergency.log',uid,tail=True)
        # Verify a bounded overlap before attributing appended records.
        # The bounded cursor never leaves private in-memory host context.
        end=info.st_size
        same=(type(cursor) is dict and cursor.get('device')==info.st_dev and cursor.get('inode')==info.st_ino
              and type(cursor.get('size')) is int and start<=cursor['size']<=end)
        if same and cursor['size']==end:
            same=(cursor.get('mtime_ns')==info.st_mtime_ns and cursor.get('ctime_ns')==info.st_ctime_ns)
        if same:
            offset=cursor['size']-start
            anchor=cursor.get('start')
            same=(type(anchor) is int and start<=anchor<=cursor['size'])
            if same:
                prefix=raw[anchor-start:offset]
                same=cursor.get('digest')==hashlib.sha256(prefix).hexdigest()
        scope='since-enable' if same else 'historical-tail'
        data=raw[offset:] if same else raw
        lines=data.split(b'\n')
        if (same and cursor.get('line_boundary') is not True) or (not same and start):
            lines=lines[1:]
        lines=lines[:-1]  # Only complete terminated records.
        health={'status':'read','scope':scope}
        for line in lines:
            if line==b'ValueError: Inactive or stale health context':health['health_refusal']='generic'
            try:value=json.loads(line)
            except (ValueError,UnicodeError):continue
            if type(value) is not dict:continue
            reason=value.get('reason')
            if value.get('event')=='health-context-rejected' and type(reason) is str and reason in REASONS:
                health['health_refusal']=reason
            if value.get('event')=='emergency-recovery' and reason=='supervisor_error':health['supervisor_error']=True
        out['health_log']=health
        out['cursor']={'device':info.st_dev,'inode':info.st_ino,'size':end,'start':end-min(4096,len(raw)),'digest':hashlib.sha256(raw[-4096:]).hexdigest(),'line_boundary':not end or raw.endswith(b'\n'),'mtime_ns':info.st_mtime_ns,'ctime_ns':info.st_ctime_ns}
    except FileNotFoundError:out['health_log']={'status':'missing'}
    except (OSError,ValueError,TypeError):out['health_log']={'status':'unsafe'}
    out['compositor'], identity = compositor(root/'c1-keyfilter', uid, cursor)
    if identity is not None:
        out.setdefault('cursor', {})['compositor'] = identity
    return out

if __name__=='__main__':
    if sys.version_info < (3, 9):
        raise ValueError('Unsupported observation interpreter')
    print(json.dumps(snapshot(cursor=json.loads(sys.argv[1]))))
'''.replace('COMPOSITOR_STOP_VALUES', repr(COMPOSITOR_STOPS))


def collect(remote, python, cursor=None):
    # Absolute, already selected/verified interpreter; no retained runtime imports.
    import shlex
    source=PROGRAM.encode()
    raw=remote.run('env -u PYTHONHOME -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 '+shlex.quote(python)+' -I -B - '+shlex.quote(json.dumps(cursor)),data=source,timeout=15)
    if len(raw)>16384:raise ValueError('oversized observation')
    value=json.loads(raw)
    if type(value) is not dict:raise ValueError('invalid observation')
    return value



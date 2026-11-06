"""Passive, bounded retained-Root observations; never recovery authority.

The host sends this stdlib-only source through verified Python's stdin. No retained
module is imported and no TV file is written. The cursor is ephemeral host data,
not report content or proof that another activation cannot run concurrently.
"""
import json

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
COMPONENTS = {'root':'com.cleanyourtv.root.preview',
              'root_updater':'com.cleanyourtv.root.updater',
              'system_updater':'com.cleanyourtv.system.updater'}
REASONS = ('transaction-mismatch','binding-restored','generation-mismatch',
           'token-mismatch','boot-mismatch','phase-inactive','failsafe-present')
LIMIT = 65536


def read(path, uid, tail=False):
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
                or info.st_mode & (0o077 if tail else 0o022) or not tail and info.st_size>LIMIT):
            raise ValueError('unsafe')
        start=max(0,info.st_size-LIMIT) if tail else 0
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
        out['cursor']={'device':info.st_dev,'inode':info.st_ino,'size':end,'start':end-min(4096,len(raw)),'digest':hashlib.sha256(raw[-4096:]).hexdigest(),'line_boundary':not end or raw.endswith(b'\n')}
    except FileNotFoundError:out['health_log']={'status':'missing'}
    except (OSError,ValueError,TypeError):out['health_log']={'status':'unsafe'}
    return out

if __name__=='__main__':
    print(json.dumps(snapshot(cursor=json.loads(sys.argv[1]))))
'''


def collect(remote, python, cursor=None):
    # Absolute, already selected/verified interpreter; no retained runtime imports.
    import shlex
    source=PROGRAM.encode()
    raw=remote.run('env -u PYTHONHOME -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 '+shlex.quote(python)+' -I -B - '+shlex.quote(json.dumps(cursor)),data=source,timeout=15)
    if len(raw)>16384:raise ValueError('oversized observation')
    value=json.loads(raw)
    if type(value) is not dict:raise ValueError('invalid observation')
    return value



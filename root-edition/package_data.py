"""Bounded installed-package DATA reads; never authorize execution from this tree.

Unanchored reads keep strict own leaves. Independently pinned reads tolerate
ordinary SDK rwx drift; private readers stay strict. The shared packages container
and pinned DATA reads through the exact services container permit observed owner 501;
UID 1001 on the exact packages/services containers is accepted only for independently
pinned DATA; this grants no execution authority.
Directory descriptors bind every open and are checked again after reading; concurrent
package replacement fails shut.
"""
import os
import hashlib
import re
from pathlib import Path
import stat

INSTALLED=Path('/media/developer/apps')
OWNERS=frozenset(('com.cleanyourtv.root.preview','com.cleanyourtv.root.updater',
                  'com.cleanyourtv.system.updater','com.cleanyourtv.installer',
                  'com.cleanyourtv.screensaver'))


def read(path,limit=65536,uid=0,installed=INSTALLED):
    """Strict unanchored DATA; writable own leaves require read_verified."""
    return _read(path,limit,uid,installed,False)


def read_verified(path, *, sha256, limit=65536, uid=0, installed=INSTALLED):
    """Only independently pinned SDK DATA may tolerate ordinary rwx drift."""
    if not isinstance(sha256,str) or not re.fullmatch('[a-f0-9]{64}',sha256):
        raise ValueError('Independent package digest required')
    raw=_read(path,limit,uid,installed,True)
    if hashlib.sha256(raw).hexdigest()!=sha256:raise ValueError('Package DATA digest mismatch')
    return raw


def _read(path,limit,uid,installed,verified):
    path,installed=Path(path),Path(installed)
    if not path.is_absolute() or '..' in path.parts or not installed.is_absolute():raise ValueError('Unsafe package path')
    relative=path.relative_to(installed).parts
    if (len(relative)<5 or relative[:2]!=('usr','palm') or relative[2] not in ('applications','services','packages')
            or relative[3] not in (OWNERS if relative[2]!='services' else {n+'.service' for n in OWNERS})):
        raise ValueError('Foreign package path')
    shared={installed,*list(installed.parents)[:-1],installed/'usr',installed/'usr/palm',installed/'usr/palm'/relative[2]}
    descriptors=[];bindings=[]
    def directory(info,name):
        # Shared SDK metadata storage is DATA, distinct from strict package leaves.
        owners=(0,uid,501) if (name==installed/'usr/palm/packages' or
                              (verified and name==installed/'usr/palm/services')) else (0,uid)
        if verified and name in (installed/'usr/palm/packages',installed/'usr/palm/services'):
            owners=(*owners,1001)
        special=info.st_mode&0o7000
        if name in shared:special&=~stat.S_ISVTX  # Shared /tmp may be legitimately sticky.
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in owners or (special or (not verified and name not in shared and info.st_mode&0o022)):
            raise ValueError('Unsafe package directory')
    def identity(info):return (info.st_dev,info.st_ino)
    def file_identity(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    def regular(info):
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_mode&0o7000 or (not verified and info.st_mode&0o022)
                or info.st_nlink!=1 or info.st_size>limit):raise ValueError('Unsafe package file')
    try:
        current=Path(path.anchor)
        fd=os.open(current,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);descriptors.append(fd)
        info=os.fstat(fd);directory(info,current);bindings.append((current,identity(info)))
        for part in path.parts[1:-1]:
            current=current/part
            fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);descriptors.append(fd)
            info=os.fstat(fd);directory(info,current);bindings.append((current,identity(info)))
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);descriptors.append(fd)
        before=os.fstat(fd);regular(before)
        chunks=[];size=0
        while True:
            chunk=os.read(fd,min(65536,limit+1-size))
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
            if size>limit:raise ValueError('Oversized package file')
        after=os.fstat(fd);regular(after)
        now=path.lstat();regular(now)
        if size!=before.st_size or file_identity(before)!=file_identity(after) or file_identity(before)!=file_identity(now):
            raise ValueError('Package file replaced during read')
        for name,expected in bindings:
            now=name.lstat();directory(now,name)
            if identity(now)!=expected:raise ValueError('Package directory replaced during read')
        return b''.join(chunks)
    finally:
        for fd in reversed(descriptors):os.close(fd)

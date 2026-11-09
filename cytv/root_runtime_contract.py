"""Check selected installer code before enabling an installed profile Root runtime."""
import hashlib
import json
import re

from . import package
from .errors import UserError

MISMATCH = 'Root runtime differs from this installer. Reinstall Root using this installer. Recovery data was kept.'
INVALID = 'Root runtime support is missing or changed. Use a complete installer build.'
VERIFIED = 'CYTV_SELECTED_RUNTIME_VERIFIED'

# Current host-owned stdlib source only. Retained manifests and executable modules
# are never imported or treated as the expected version; no TV file is written.
PROGRAM = r'''
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat


def read(path, uid):
    for parent in (path.parent,*path.parent.parents):
        info=parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,uid)
                or info.st_mode&0o022 and not (info.st_uid==0 and info.st_mode&stat.S_ISVTX)):
            raise ValueError('unsafe')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1
                or info.st_mode&0o022 or info.st_size>4*1024*1024):
            raise ValueError('unsafe')
        raw=b''
        while len(raw)<info.st_size:
            chunk=os.read(fd,info.st_size-len(raw))
            if not chunk:raise ValueError('changed')
            raw+=chunk
        after=os.fstat(fd);current=path.lstat()
        if ((current.st_dev,current.st_ino)!=(info.st_dev,info.st_ino)
                or any(getattr(info,k)!=getattr(after,k) for k in
                       ('st_size','st_mode','st_nlink','st_uid','st_mtime_ns','st_ctime_ns'))):
            raise ValueError('changed')
        return raw
    finally:os.close(fd)


def matches(expected, root='/var/lib/clean-your-tv-root', uid=0):
    try:
        if not isinstance(expected,dict) or not 0<len(expected)<=128:return False
        for name,digest in expected.items():
            relative=PurePosixPath(name)
            if (relative.is_absolute() or str(relative)!=name or '..' in relative.parts or '\\' in name
                    or not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest)):
                return False
            if hashlib.sha256(read(Path(root)/name,uid)).hexdigest()!=digest:return False
        return True
    except (OSError,ValueError,TypeError):return False
'''


def verify(installer):
    """Fail closed on old support while preserving transport/storage failures."""
    if not getattr(installer,'_graphics_paths',None):
        installer.select_graphics()
    folder=package.safe_name(installer._graphics_paths['root'])
    outer=installer.manifest.get('files',{})
    def checked(name):
        path=installer.payload.resolve()/package.safe_name(folder+'/'+name)
        if any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('indirect support')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=outer.get(folder+'/'+name):
            raise ValueError('changed support')
        return raw
    try:
        manifest=json.loads(checked('bundle.json'))
        files=manifest['files']
        if not isinstance(files,dict) or not isinstance(manifest.get('package'),str):
            raise ValueError('invalid support')
        names=set(files)-{manifest['package'],'release.json','SHA256SUMS'}
        required={'deploy.py','python_binding.py','runtime/cli.py','runtime/device_adapter.py',
                  'runtime/persistent_health.py','runtime/emergency_trial.py'}
        if not required<=names or len(names)>128:raise ValueError('incomplete support')
        expected={}
        for name in sorted(names):
            digest=files[name]
            if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):
                raise ValueError('invalid support digest')
            if hashlib.sha256(checked(name)).hexdigest()!=digest:
                raise ValueError('changed support')
            expected[name]=digest
    except (OSError,ValueError,TypeError,KeyError):
        raise UserError(INVALID) from None
    python=installer._python()
    source=PROGRAM+'\nprint("CYTV_SELECTED_RUNTIME_VERIFIED" if matches('+repr(expected)+') else "CYTV_SELECTED_RUNTIME_MISMATCH")\n'
    reply=installer.remote.run(installer._python_command([python,'-I','-B','-']),data=source.encode(),timeout=60)
    if reply.strip()!=VERIFIED:
        raise UserError(MISMATCH,reason_code='installer-runtime-mismatch')

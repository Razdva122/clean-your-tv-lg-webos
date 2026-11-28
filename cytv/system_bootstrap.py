"""Authenticate a retained root SSH bootstrap upload before explicit continuation."""
import hashlib
import json
import re

from .errors import UserError
from .root_staging import ROOT

VERIFY = r"""
import hashlib,json,os,stat,sys
from pathlib import Path
stage=Path(sys.argv[1]); expected=json.load(sys.stdin)
if os.geteuid()!=0:raise ValueError('root required')
for parent in reversed(stage.parents):
    try:info=parent.lstat()
    except FileNotFoundError:print('absent');sys.exit(0)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or (info.st_mode&0o022 and parent!=Path('/tmp')):
        raise ValueError('unsafe staging parent')
    if parent==Path('/tmp') and info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX:
        raise ValueError('unsafe temporary root')
if not os.path.lexists(stage):
    print('absent');sys.exit(0)
seen=set()
allowed_dirs={stage}
for key in expected:
    allowed_dirs.update(parent for parent in (stage/key).parents if parent==stage or stage in parent.parents)
for root,dirs,files in os.walk(stage,followlinks=False):
    for folder in (Path(root), *(Path(root)/name for name in dirs)):
        info=folder.lstat()
        if folder not in allowed_dirs or not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077:
            raise ValueError('unsafe staging directory')
    for name in files:
        path=Path(root)/name
        key=str(path.relative_to(stage))
        with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as src:
            info=os.fstat(src.fileno())
            if (key not in expected or not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_nlink!=1
                    or info.st_mode&0o022 or info.st_size!=expected[key][0]):
                raise ValueError('unexpected staged file')
            h=hashlib.sha256()
            for chunk in iter(lambda:src.read(65536),b''):h.update(chunk)
            if h.hexdigest()!=expected[key][1]:raise ValueError('staged file changed')
        seen.add(key)
allow_partial=len(sys.argv)==3 and sys.argv[2]=='partial'
if seen!=set(expected) and not allow_partial:raise ValueError('incomplete staging')
print('verified')
"""


def retained_stage(installer, stage, bundle, files, *, allow_partial=False):
    if not isinstance(stage, str) or not re.fullmatch(r'(?:/tmp|'+re.escape(ROOT)+r')/cytv-system-updater-[a-f0-9]{32}',stage):
        raise UserError('The original update setup receipt could not be verified.', reason_code='pending-operation')
    expected={}
    for name in (*files,'bundle.json'):
        raw=(bundle/name).read_bytes()
        expected[name]=[len(raw),hashlib.sha256(raw).hexdigest()]
    args=[installer._python(),'-I','-B','-c',VERIFY,stage]
    if allow_partial:args.append('partial')
    reply=installer.remote.run(installer._python_command(args),data=json.dumps(expected).encode(),timeout=60).strip()
    if reply not in ('verified','absent'):
        raise UserError('The original update setup files could not be verified.', reason_code='pending-operation')
    return stage if reply=='verified' else None

"""Exact offline payload inventories; no downloading or device-side execution."""
import hashlib
import json
from pathlib import Path
import re
import tarfile
from cytv import python_runtime as runtime

MAX_MANIFEST = 4 * 1024 * 1024

def safe_name(name):
    if (not isinstance(name, str) or len(name)>512 or not re.fullmatch(r'[A-Za-z0-9_+.,@=/-]+', name)
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Unsafe payload path')
    return name

def read_file(path):
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file() or path.stat().st_nlink!=1:
        raise ValueError('Indirect payload file')
    return path.read_bytes()

def inventory(root):
    root=Path(root); result={}
    if any(p.is_symlink() for p in (root,*root.parents)) or not root.is_dir(): raise ValueError('Indirect payload directory')
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_file() or path.is_dir()): raise ValueError('Unsafe payload entry')
        if path.is_file():
            name=safe_name(path.relative_to(root).as_posix());raw=read_file(path)
            result[name]={'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}
    return result

def checked_bundle(root):
    root=Path(root); actual=inventory(root)
    manifest=json.loads(read_file(root/'bundle.json'))
    expected=manifest.get('files')
    if not isinstance(expected,dict) or set(actual)!=set(expected)|{'bundle.json'}: raise ValueError('Bundle inventory mismatch')
    for name,digest in expected.items():
        safe_name(name)
        if not re.fullmatch('[0-9a-f]{64}',str(digest)) or actual[name]['sha256']!=digest: raise ValueError('Bundle hash mismatch')
    return actual

def validate_runtime(archive, binding):
    if binding.get('schema')!=1 or binding.get('archive_sha256')!=runtime.SHA256: raise ValueError('Invalid runtime binding')
    expected=binding.get('files'); records={}; total=0
    if not isinstance(expected,dict) or len(expected)>runtime.MAX_FILES: raise ValueError('Invalid runtime inventory')
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            name=safe_name(member.name)
            if name in records or len(records)>runtime.MAX_FILES*2 or not (member.isdir() or member.isreg()): raise ValueError('Unsafe runtime archive')
            records[name]=None
            if member.isdir(): continue
            total+=member.size
            if total>runtime.MAX_UNPACKED: raise ValueError('Runtime exceeds size limit')
            raw=tar.extractfile(member).read()
            digest=hashlib.sha256(raw).hexdigest()
            if name=='.cytv-runtime.json':
                if json.loads(raw)!=binding: raise ValueError('Runtime binding mismatch')
            elif expected.get(name)!=digest: raise ValueError('Runtime hash mismatch')
            records[name]={'sha256':digest,'size':member.size,'mode':member.mode}
    files={n:r for n,r in records.items() if r is not None}
    if set(files)!=set(expected)|{'.cytv-runtime.json'} or not files.get('bin/python3.13',{}).get('mode',0)&0o111: raise ValueError('Runtime inventory mismatch')
    return files

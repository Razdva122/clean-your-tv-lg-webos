"""Bounded inspection of our reproducible IPK format, never extract or execute it."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile

APP = 'com.cleanyourtv.root.preview'
PREFIX = 'usr/palm/applications/' + APP + '/'
SERVICE = 'usr/palm/services/' + APP + '.service/'
INFO = 'usr/palm/packages/' + APP + '/packageinfo.json'


def members(raw):
    if raw[:8] != b'!<arch>\n': raise ValueError('Invalid IPK')
    result = {}; offset = 8
    while offset < len(raw):
        header = raw[offset:offset+60]
        if len(header) != 60 or header[58:] != b'`\n': raise ValueError('Invalid ar header')
        name = header[:16].decode('ascii').strip().rstrip('/')
        try: size = int(header[48:58])
        except ValueError: raise ValueError('Invalid ar size')
        if size < 0 or name in result or offset+60+size > len(raw): raise ValueError('Invalid ar member')
        result[name] = raw[offset+60:offset+60+size]; offset += 60+size+size%2
    if offset != len(raw) or set(result) != {'debian-binary','control.tar.gz','data.tar.gz'} or result['debian-binary'] != b'2.0\n':
        raise ValueError('Unexpected IPK inventory')
    return result


def archive(raw):
    result = {}; total = 0; seen=set(); directories=set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as stream:
        for member in stream:
            name = member.name; path = PurePosixPath(name)
            if (path.is_absolute() or str(path) != name or '..' in path.parts
                    or '\\' in name or '\x00' in name or name in seen or member.size > 32*1024*1024):
                raise ValueError('Unsafe IPK payload')
            seen.add(name)
            if member.isdir():
                if (member.size or member.mode!=0o755 or member.uid!=0 or member.gid!=0
                        or (len(path.parts)<4 or path.parts[:3] not in (('usr','palm','applications'),('usr','palm','services'),('usr','palm','packages')))):raise ValueError('Unsafe IPK directory')
                directories.add(name);continue
            if not member.isfile():raise ValueError('Unsafe IPK payload')
            total += member.size
            if total > 64*1024*1024 or len(result) >= 4096: raise ValueError('IPK payload too large')
            result[name] = stream.extractfile(member).read(member.size+1)
            if len(result[name]) != member.size: raise ValueError('Truncated payload')
    if directories-{str(p) for name in result for p in PurePosixPath(name).parents}:raise ValueError('Foreign IPK directory')
    return result


def inspect_package(raw, manifest):
    if len(raw) != manifest['size'] or hashlib.sha256(raw).hexdigest() != manifest['sha256']:
        raise ValueError('Package hash mismatch')
    parts = members(raw); files = archive(parts['data.tar.gz']); control = archive(parts['control.tar.gz'])
    lines = control.get('control', b'').decode('utf8').splitlines()
    if lines.count('Package: '+APP) != 1 or lines.count('Version: '+manifest['version']) != 1:
        raise ValueError('Package control identity mismatch')
    if any(not (name.startswith(PREFIX) or name.startswith(SERVICE) or name == INFO) for name in files):
        raise ValueError('Foreign package payload')
    app = json.loads(files.get(PREFIX+'appinfo.json', b'{}')); info = json.loads(files.get(INFO, b'{}'))
    if (app.get('id') != APP or app.get('version') != manifest['version'] or app.get('type') != 'web'
            or app.get('main') != 'index.html' or PREFIX+'index.html' not in files
            or info.get('id') != APP or info.get('app') != APP or info.get('version') != manifest['version']
            or info.get('services') not in ([], [APP+'.service'])):
        raise ValueError('Root application identity mismatch')
    if 'url' in manifest:
        expected='1280x720' if manifest['url'].endswith('_720p_all.ipk') else '1920x1080'
        if app.get('resolution','1920x1080')!=expected:raise ValueError('Root package graphics variant mismatch')
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


def safe_bytes(path, limit=32*1024*1024, uid=None):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)): raise ValueError('Indirect file path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > limit or (uid is not None and (st.st_uid != uid or st.st_mode & 0o022)):
            raise ValueError('Unsafe file')
        raw = f.read(limit+1)
        if len(raw) > limit: raise ValueError('File too large')
        return raw


def verify_payload(root, hashes, uid=0):
    for name, digest in hashes.items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name: raise ValueError('Unsafe payload name')
        from package_data import OWNERS, read_verified
        owner=path.parts[3] if len(path.parts)>=5 and path.parts[:2]==('usr','palm') else None
        if owner in OWNERS or owner in {o+'.service' for o in OWNERS}:
            raw=read_verified(Path(root)/name,sha256=digest,limit=32*1024*1024,uid=uid,installed=root)
        else:raw=safe_bytes(Path(root)/name)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Installed payload mismatch: '+name)

"""Deterministic IPK creation and data-only launcher personalization."""
import gzip
import hashlib
import io
import json
import html
import re
import unicodedata
from pathlib import Path, PurePosixPath
import tarfile

ROOT_APP = 'com.cleanyourtv.root.preview'
# webOS pkgverifier rejects epoch-zero tar dates. Fixed 2024-01-01 keeps builds reproducible.
IPK_MTIME = 1704067200


def safe_name(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or str(path) != name or '..' in path.parts or '\\' in name or '\x00' in name:
        raise ValueError('Unsafe package path')
    return name


def ar(parts):
    result = bytearray(b'!<arch>\n')
    for name, data in parts.items():
        result.extend(f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode())
        result.extend(data)
        if len(data) % 2:
            result.extend(b'\n')
    return bytes(result)


def read_ar(data):
    if data[:8] != b'!<arch>\n':
        raise ValueError('Not an IPK archive')
    result, offset = {}, 8
    while offset < len(data):
        header = data[offset:offset + 60]
        if len(header) != 60 or header[58:] != b'`\n':
            raise ValueError('Invalid IPK member')
        size = int(header[48:58])
        name = header[:16].decode().strip().rstrip('/')
        content = data[offset + 60:offset + 60 + size]
        if size < 0 or len(content) != size or name in result:
            raise ValueError('Invalid IPK member size or duplicate')
        result[name] = content
        offset += 60 + size + size % 2
    return result


def tgz(files, executable=(), helper_state=False, directories=True, shared_directories=False):
    raw = io.BytesIO()
    dirs = set()
    for name in files:
        safe_name(name)
        dirs.update(str(p) for p in PurePosixPath(name).parents if str(p) != '.' and
                    (shared_directories or p.parts[:2] != ('usr','palm') or len(p.parts) >= 4))
    # Root archives retain owned leaves only; No-root opts into SDK parents for opkg.
    if not shared_directories:
        dirs.discard('usr')
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name in sorted(dirs) if directories else ():
            entry = tarfile.TarInfo(name)
            entry.mtime = IPK_MTIME
            entry.type, entry.mode = tarfile.DIRTYPE, 0o755
            if helper_state and name in ('usr/palm/applications/com.local.nativehome/state', 'usr/palm/services/com.local.nativehome.service/state'):
                entry.uid, entry.gid, entry.mode = 5999, 5000, 0o770
                entry.uname, entry.gname = 'prisoner', 'jailer'
            if name in ('usr/palm/services/com.gathin.tvhome.renewal/state',
                        'usr/palm/services/com.gathin.tvhome.renewal/state/home-control'):
                # Native controller and jailed JS service have distinct UIDs.
                # setgid keeps both sides' files in the shared jailer group.
                entry.uid, entry.gid, entry.mode = 5999, 5000, 0o2770
                entry.uname, entry.gname = 'prisoner', 'jailer'
            archive.addfile(entry)
        for name, data in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.mtime = IPK_MTIME
            entry.size, entry.mode = len(data), 0o755 if name in executable else 0o644
            archive.addfile(entry, io.BytesIO(data))
    compressed = io.BytesIO()
    # GzipFile keeps the OS byte canonical across Python/zlib build hosts.
    with gzip.GzipFile(filename='', fileobj=compressed, mode='wb', compresslevel=9, mtime=0) as packed:
        packed.write(raw.getvalue())
    return compressed.getvalue()


def ipk(app, version, files, executable=(), helper_state=False, architecture='all', shared_directories=False):
    control = f'Package: {app}\nVersion: {version}\nArchitecture: {architecture}\nMaintainer: Clean Your TV\nDescription: Clean Your TV\n'
    return ar({'debian-binary': b'2.0\n', 'control.tar.gz': tgz({'control': control.encode()}),
               'data.tar.gz': tgz(files, executable, helper_state, shared_directories=shared_directories)})


def data_files(data):
    with tarfile.open(fileobj=io.BytesIO(read_ar(data)['data.tar.gz']), mode='r:gz') as archive:
        result = {}
        for member in archive:
            if member.isdir():
                continue
            safe_name(member.name)
            if not member.isfile() or member.size > 16 * 1024 * 1024:
                raise ValueError('Unsupported package member')
            result[member.name] = archive.extractfile(member).read()
        return result


def verify_root_rollback_format(data):
    """Accept file-only history and secure own-leaf directory entries."""
    parts=read_ar(data)
    roots=('usr/palm/applications/'+ROOT_APP,'usr/palm/services/'+ROOT_APP+'.service','usr/palm/packages/'+ROOT_APP)
    for name in ('control.tar.gz','data.tar.gz'):
        seen=set();dirs=set();files=set()
        with tarfile.open(fileobj=io.BytesIO(parts[name]),mode='r:gz') as archive:
            for member in archive:
                safe_name(member.name)
                if member.name in seen:raise ValueError('Root rollback package has duplicate archive entries')
                seen.add(member.name)
                if member.isdir():
                    if (member.size or member.mode!=0o755 or member.uid!=0 or member.gid!=0
                            or not any(member.name==root or member.name.startswith(root+'/') for root in roots)):
                        raise ValueError('Root rollback package has unsupported archive entries. Use a corrected installer build.')
                    dirs.add(member.name)
                elif member.isfile():files.add(member.name)
                else:raise ValueError('Root rollback package has unsupported archive entries. Use a corrected installer build.')
        if dirs-{str(parent) for file in files for parent in PurePosixPath(file).parents}:raise ValueError('Root rollback package has foreign directories')


def inventory_script(inventory):
    if not isinstance(inventory, dict) or not isinstance(inventory.get('apps'), list) or not inventory['apps']:
        raise ValueError('No usable apps were read from the TV. Installation stopped.')
    if len(inventory['apps']) > 200 or len(inventory.get('inputs', [])) > 100:
        raise ValueError('TV inventory is too large')
    script = ('window.TV_APPS = ' + json.dumps(inventory, ensure_ascii=True) + ';\n').encode()
    if len(script) > 16 * 1024 * 1024:
        raise ValueError('TV inventory exceeds the 16 MiB package limit')
    return script


def normalize_tv_name(value):
    if not isinstance(value, str):
        raise ValueError('TV name must be text.')
    name = unicodedata.normalize('NFC', value.strip()) or 'Home'
    if len(name) > 48 or any(unicodedata.category(char).startswith('C') or char in '\u2028\u2029' for char in name):
        raise ValueError('TV name must contain at most 48 characters, without control characters.')
    return name


def personalize(data, app, inventory, tv_name=None):
    name = normalize_tv_name(tv_name) if tv_name is not None else None
    parts = read_ar(data)
    files = data_files(data)
    # Preserve execution from the validated regular files; tgz normalizes all
    # permissions to 0755/0644, without retaining setuid or other special bits.
    with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']), mode='r:gz') as archive:
        executable = {member.name for member in archive if member.isfile() and member.mode & 0o111}
    prefix = 'usr/palm/applications/' + app + '/'
    if inventory is not None or name is None:
        files[prefix + 'apps.js'] = inventory_script(inventory)
    if name is not None:
        info = json.loads(files[prefix + 'appinfo.json'])
        if info.get('id') != app:
            raise ValueError('Launcher application identity mismatch')
        info['title'] = name
        files[prefix + 'tv-name-config.js'] = ('window.CYTV_TV_NAME = ' + json.dumps(name, ensure_ascii=True) + ';\n').encode()
        files[prefix + 'appinfo.json'] = (json.dumps(info, ensure_ascii=True, indent=2) + '\n').encode()
        if prefix + 'index.html' in files:
            page = files[prefix + 'index.html'].decode('utf-8')
            page = re.sub(r'<title>.*?</title>', lambda _: '<title>' + html.escape(name) + '</title>',
                          page, count=1, flags=re.IGNORECASE | re.DOTALL)
            files[prefix + 'index.html'] = page.encode('utf-8')
    parts['data.tar.gz'] = tgz(files, executable=executable, directories=True,
                             shared_directories=app == 'com.gathin.tvhome')
    return ar(parts), files


def personalize_root(bundle, inventory, tv_name=None):
    bundle = Path(bundle)
    manifest = json.loads((bundle / 'bundle.json').read_text())
    for name, digest in manifest['files'].items():
        if hashlib.sha256((bundle / safe_name(name)).read_bytes()).hexdigest() != digest:
            raise ValueError('Root bundle integrity mismatch')
    name = manifest['package']
    data, files = personalize((bundle / name).read_bytes(), ROOT_APP, inventory, tv_name=tv_name)
    (bundle / name).write_bytes(data)
    release = json.loads((bundle / 'release.json').read_text())
    release['files'] = {n: hashlib.sha256(b).hexdigest() for n, b in sorted(files.items())}
    (bundle / 'release.json').write_text(json.dumps(release), encoding='utf-8')
    (bundle / 'SHA256SUMS').write_text(hashlib.sha256(data).hexdigest() + '  ' + name + '\n', encoding='utf-8')
    manifest['files'] = {n: hashlib.sha256((bundle / safe_name(n)).read_bytes()).hexdigest() for n in manifest['files']}
    (bundle / 'bundle.json').write_text(json.dumps(manifest), encoding='utf-8')


def verify_payload(root):
    root = Path(root)
    manifest = json.loads((root / 'payload.json').read_text())
    for name, digest in manifest['files'].items():
        path = root / safe_name(name)
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Embedded payload integrity mismatch')
        # Integrity alone cannot detect CRLF introduced before the build hashes.
        files = data_files(path.read_bytes()) if name.endswith('.ipk') else {name: path.read_bytes()}
        for script, data in files.items():
            if script.endswith('.sh') and b'\r' in data:
                raise ValueError('POSIX script must use LF line endings: ' + name + ': ' + script)
    if not manifest['files']:
        raise ValueError('Empty embedded payload')
    return manifest

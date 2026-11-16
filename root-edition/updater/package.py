"""Bounded inspection of our reproducible IPK format, never extract or execute it."""
import gzip
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
SCREENSAVER = 'com.cleanyourtv.screensaver'
SCREENSAVER_PREFIX = 'usr/palm/applications/' + SCREENSAVER + '/'
SCREENSAVER_INFO = 'usr/palm/packages/' + SCREENSAVER + '/packageinfo.json'
SCREENSAVER_RECIPE = PREFIX + 'screensaver-companion/manifest.json'
SCREENSAVER_FILES = frozenset((
    'appinfo.json', 'index.html', 'renderer.js', 'settings.js', 'style.css',
    'icon.png', 'compat-polyfills.js', 'compat-LICENSE.txt',
) + tuple('backgrounds/' + scene + suffix for scene in ('alpine', 'ribbon') for suffix in (
    '-photo.jpg', '-video.mp4', '-video-1080p.mp4', '-CREDITS.txt', '-LICENSE.txt',
)))


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


def _verified_package_files(raw, manifest):
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
    return files


def inspect_package(raw, manifest):
    files = _verified_package_files(raw, manifest)
    companion_files(files)
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


def companion_files(files):
    """Project only the fixed service-free companion from verified Root DATA."""
    recipe = files.get(SCREENSAVER_RECIPE)
    if recipe is None:
        return None
    spec = json.loads(recipe)
    if (not isinstance(spec, dict) or set(spec) != {'schema', 'version', 'files'}
            or type(spec['schema']) is not int or spec['schema'] != 1
            or not isinstance(spec['files'], dict) or set(spec['files']) != SCREENSAVER_FILES):
        raise ValueError('Invalid Root screensaver recipe')
    version = spec['version']
    import re
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}', version):
        raise ValueError('Invalid Root screensaver version')
    result = {}
    for name, source in spec['files'].items():
        if not isinstance(source, str) or not source.startswith(PREFIX) or source not in files:
            raise ValueError('Screensaver resource outside authenticated Root application')
        result[SCREENSAVER_PREFIX + name] = files[source]
    info = json.loads(result[SCREENSAVER_PREFIX + 'appinfo.json'])
    if (not isinstance(info, dict) or info.get('id') != SCREENSAVER
            or info.get('version') != version or info.get('type') != 'web'
            or info.get('main') != 'index.html' or info.get('defaultWindowType') != 'popup'
            or info.get('visible') is not False or info.get('requiredACG') or info.get('privilegedJail')):
        raise ValueError('Unexpected Root screensaver app identity')
    result[SCREENSAVER_INFO] = json.dumps({
        'id': SCREENSAVER, 'version': version, 'app': SCREENSAVER, 'services': [],
    }).encode()
    return version, result


def companion_archive(version, files):
    """Package verified static bytes under the fixed ordinary app identity."""
    def tgz(content):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as stream:
            parents = {str(p) for name in content for p in PurePosixPath(name).parents
                       if len(p.parts) >= 4}
            for name in sorted(parents):
                member = tarfile.TarInfo(name)
                member.type, member.mode, member.mtime = tarfile.DIRTYPE, 0o755, 1704067200
                stream.addfile(member)
            for name, data in sorted(content.items()):
                member = tarfile.TarInfo(name)
                member.mode, member.mtime, member.size = 0o644, 1704067200, len(data)
                stream.addfile(member, io.BytesIO(data))
        packed = io.BytesIO()
        with gzip.GzipFile(filename='', fileobj=packed, mode='wb', compresslevel=1, mtime=0) as output:
            output.write(buffer.getvalue())
        return packed.getvalue()

    control = f'Package: {SCREENSAVER}\nVersion: {version}\nArchitecture: all\nMaintainer: Clean Your TV\nDescription: Clean Your TV Screensaver\n'
    result = bytearray(b'!<arch>\n')
    for name, raw in (('debian-binary', b'2.0\n'), ('control.tar.gz', tgz({'control': control.encode()})),
                      ('data.tar.gz', tgz(files))):
        result.extend(f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(raw):<10}`\n'.encode())
        result.extend(raw)
        if len(raw) % 2:
            result.extend(b'\n')
    return bytes(result)


def root_companion(raw, descriptor):
    return companion_files(_verified_package_files(raw, descriptor))


def installed_companion(installed, selected, uid=0):
    if selected is None:
        paths = (
            SCREENSAVER_PREFIX.rstrip('/'),
            SCREENSAVER_INFO.rsplit('/', 1)[0],
            'usr/palm/services/' + SCREENSAVER + '.service',
        )
        return not any(os.path.lexists(Path(installed) / name) for name in paths)
    try:
        verify_payload(installed, {name: hashlib.sha256(raw).hexdigest()
                                   for name, raw in selected[1].items()}, uid=uid)
    except FileNotFoundError:
        return False
    except ValueError as error:
        if str(error) == 'Package DATA digest mismatch' or str(error).startswith('Installed payload mismatch: '):
            return False
        raise
    return True


def companion_journal_name(tx, rollback):
    return ('screensaver-rollback-' if rollback else 'screensaver-update-') + tx['id']


def companion_outcome_pending(store, tx):
    return any(
        value is not None and (not isinstance(value, dict) or value.get('terminal') is None)
        for value in (store.read(companion_journal_name(tx, rollback)) for rollback in (False, True))
    )


def sync_companion(installed, selected, prior, journal, work, *, uid=0, install=None, remove=None):
    """Advance a fixed companion once under the caller's product/worker lock."""
    if selected is None and prior is None:
        return
    from observed_install import install as observed_install, remove as observed_remove
    from installation import terminal_install, terminal_removal
    from tempfile import TemporaryDirectory

    install = install or observed_install
    remove = remove or observed_remove
    action = 'install' if selected else 'remove'
    version = selected[0] if selected else prior[0]
    content = (selected or prior)[1]
    # Bind receipts to exact payload bytes, not just an app id or version.
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in content.items()}
    identity = {'action': action, 'version': version,
                'sha256': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}

    state = journal()
    if state is not None:
        if not isinstance(state, dict) or set(state) != {'identity', 'terminal'} or state['identity'] != identity:
            raise ValueError('Screensaver package operation changed')
        proof = state['terminal']
        predicate = terminal_install if selected else terminal_removal
        if not predicate(proof, SCREENSAVER):
            raise ValueError('Screensaver package outcome unconfirmed; recovery required')
        if installed_companion(installed, selected, uid):
            return
        if not selected:
            package = Path(installed) / SCREENSAVER_INFO.rsplit('/', 1)[0]
            if package.is_dir() and not any(path.is_symlink() for path in (package, *package.parents)):
                package.rmdir()
            if installed_companion(installed, selected, uid):
                return
        raise ValueError('Screensaver package readback did not match recorded result')

    if installed_companion(installed, selected, uid):
        return
    if not (installed_companion(installed, None, uid)
            or (prior is not None and installed_companion(installed, prior, uid))):
        raise ValueError('Installed screensaver does not match the verified Root baseline')
    if selected:
        with TemporaryDirectory(prefix='screensaver-', dir=work) as directory:
            path = Path(directory) / 'screensaver.ipk'
            with path.open('xb') as output:
                output.write(companion_archive(*selected))
                output.flush()
                os.fsync(output.fileno())
            proof = install(SCREENSAVER, str(path), timeout=150,
                            on_ready=lambda: journal({'identity': identity, 'terminal': None}))
    else:
        journal({'identity': identity, 'terminal': None})
        proof = remove(SCREENSAVER, timeout=150)
    predicate = terminal_install if selected else terminal_removal
    if not predicate(proof, SCREENSAVER):
        raise ValueError('Screensaver package outcome unconfirmed; recovery required')
    journal({'identity': identity, 'terminal': proof})
    # Re-enter solely for terminal readback, never for another package request.
    sync_companion(installed, selected, prior, journal, work, uid=uid, install=install, remove=remove)


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

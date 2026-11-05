"""Acquire one pinned optional Root Python, then bootstrap it over SSH shell.

The cache contains only <archive SHA-256>.tar.gz. No target interpreter is needed
until an authenticated, normalized tree has passed shell inventory verification.
"""
import gzip
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import posixpath
import re
import shlex
import stat
import ssl
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request

from .errors import UserError, TVCommandError, PythonPreflightError, PythonCacheError

SHA256 = '4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea'
SIZE = 26256859
URL = ('https://github.com/astral-sh/python-build-standalone/releases/download/20261021/'
       'cpython-3.13.17%2B20261021-armv7-unknown-linux-gnueabi-install_only_stripped.tar.gz')
RUNTIME_ROOT = '/var/lib/clean-your-tv-python'
MAX_UNPACKED = 160 * 1024 * 1024
MAX_FILES = 12000
_HOST_POSIX = os.name == 'posix'

DOWNLOAD_ERROR = PythonCacheError.DOWNLOAD_ERROR
CACHE_ERROR = PythonCacheError.CACHE_ERROR
ARCHIVE_ERROR = 'The private Python archive is unsafe or incompatible. No runtime was installed.'
TARGET_ERROR = 'This TV cannot safely install private Python. Check its ARM ABI, available space and root-owned runtime directories.'
INSTALL_ERROR = 'Private Python installation could not be verified. Run cytv doctor before retrying.'
MISSING_ERROR = 'This operation requires working Python 3.9 or newer on the TV. Run Root installation to prepare private Python.'

# Exercise the operations used by Root/recovery/updaters, including native modules.
_PROBE_BODY = r'''
import argparse, ast, base64, binascii, codecs, contextlib, copy, errno, fcntl, gzip
import hashlib, importlib, io, json, math, os, pathlib, re, select, shlex, shutil, signal
import stat, struct, subprocess, sys, tarfile, tempfile, threading, time, uuid, zlib
assert sys.version_info >= (3, 9)
assert hashlib.sha256(b'cytv').hexdigest()
assert zlib.decompress(zlib.compress(b'cytv')) == b'cytv'
assert time.monotonic() <= time.monotonic()
with tempfile.TemporaryDirectory(prefix='.cytv-python-smoke-') as directory:
    root = pathlib.Path(directory)
    with (root/'lock').open('wb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lock, fcntl.LOCK_UN)
    with (root/'before').open('wb') as stream:
        stream.write(b'cytv'); stream.flush(); os.fsync(stream.fileno())
    os.replace(root/'before', root/'after')
    assert (root/'after').read_bytes() == b'cytv'
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
assert subprocess.check_output([sys.executable, '-I', '-B', '-c', 'print("cytv-child")'], timeout=15).strip() == b'cytv-child'
'''
SMOKE = _PROBE_BODY + "\nprint('CYTV_RUNTIME_SMOKE')\n"
SYSTEM_PROBE = _PROBE_BODY + "\nprint('CYTV_SYSTEM_PYTHON')\n"


def _asset_url(url):
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme == 'https' and parsed.netloc == 'release-assets.githubusercontent.com'
            and parsed.path.startswith('/') and not parsed.fragment)


class _ReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.count = 0

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > 3 or not _asset_url(newurl):
            raise PythonCacheError('response-policy')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _stream_hash(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(256 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def _host_private(info):
    return not _HOST_POSIX or (info.st_uid == os.getuid() and not info.st_mode & 0o022)


def _verified_bytes(path):
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode): raise UserError(CACHE_ERROR)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or not _host_private(info) or info.st_nlink != 1
                or info.st_size != SIZE or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)):
            raise UserError(CACHE_ERROR)
        data = stream.read(SIZE + 1)
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
        raise UserError(CACHE_ERROR)
    return data


def _android_cache_anchor(cache):
    """Use Chaquopy's app context only for CYTV's fixed private files tree."""
    pattern = r'(/data/(?:data|user/[0-9]+)/com\.cleanyourtv\.android/files)'
    matched = re.fullmatch(pattern + r'/(.+)', str(cache))
    if not _HOST_POSIX or not matched or os.getuid() < 10000: return None
    try:
        from java import jclass
    except ImportError:
        return None
    try:
        application = jclass('com.chaquo.python.Python').getPlatform().getApplication()
        if str(application.getPackageName()) != 'com.cleanyourtv.android': raise UserError(CACHE_ERROR)
        context_anchor = Path(str(application.getFilesDir().getAbsolutePath()))
        if not re.fullmatch(pattern, str(context_anchor)): raise UserError(CACHE_ERROR)
    except Exception:
        raise UserError(CACHE_ERROR) from None

    def platform_anchor(anchor):
        prefix = anchor.parent.parent
        canonical = anchor
        for directory in reversed((prefix, *prefix.parents)):
            info = directory.lstat()
            if stat.S_ISLNK(info.st_mode):
                # The sole allowed platform alias is verified before rewriting.
                if (str(directory) != '/data/user/0' or info.st_uid != 0
                        or str(directory.readlink()) != '/data/data'):
                    raise UserError(CACHE_ERROR)
                canonical = Path('/data/data/com.cleanyourtv.android/files')
                info = Path('/data/data').lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, 1000)
                    or info.st_gid not in (0, 1000) or info.st_mode & 0o002):
                raise UserError(CACHE_ERROR)
        return canonical

    requested_anchor = Path(matched.group(1))
    anchor = platform_anchor(requested_anchor)
    if anchor != platform_anchor(context_anchor): raise UserError(CACHE_ERROR)
    package = anchor.parent.lstat()
    files = anchor.lstat()
    if (not stat.S_ISDIR(package.st_mode) or package.st_uid != os.getuid() or package.st_mode & 0o077
            or not stat.S_ISDIR(files.st_mode) or files.st_uid != os.getuid() or files.st_mode & 0o002
            or (files.st_mode & 0o020 and files.st_gid != os.getgid())):
        raise UserError(CACHE_ERROR)
    relative = cache.relative_to(requested_anchor)
    if '..' in relative.parts: raise UserError(CACHE_ERROR)
    return anchor/relative, anchor


def _cache_directory(cache_dir):
    cache = Path(cache_dir).absolute()
    android_anchor = _android_cache_anchor(cache)
    if android_anchor:
        cache, anchor = android_anchor
        directories, directory = [], cache
        while directory != anchor:
            directories.append(directory)
            directory = directory.parent
    else:
        directories = (cache, *cache.parents)
    for directory in reversed(directories):
        try: info = directory.lstat()
        except FileNotFoundError:
            try: directory.mkdir(mode=0o700)
            except FileExistsError: pass
            info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise UserError(CACHE_ERROR)
        if _HOST_POSIX:
            if info.st_uid not in (0, os.getuid()): raise UserError(CACHE_ERROR)
            # Root-owned sticky temporary parents protect child directory names.
            sticky_temporary_parent = directory != cache and info.st_uid == 0 and info.st_mode & stat.S_ISVTX
            if info.st_mode & 0o022 and not sticky_temporary_parent: raise UserError(CACHE_ERROR)
    if not _host_private(cache.lstat()): raise UserError(CACHE_ERROR)
    return cache


def prime_cache(cache_dir, progress):
    """Prepare/reuse only the pinned verified archive; never contact a TV."""
    temporary = None
    failure = 'cache-access'
    try:
        cache = _cache_directory(cache_dir)
        path = cache/(SHA256 + '.tar.gz')
        if os.path.lexists(path):
            _verified_bytes(path)
            progress('Using the verified private Python cache…')
            return path
        progress('Downloading private Python for this TV (26 MB)…')
        failure = 'network'
        context = ssl.create_default_context()
        if sys.platform == 'darwin':
            # Frozen Python retains its build host's CA paths, absent on a clean Mac.
            context.load_verify_locations(cafile='/etc/ssl/cert.pem')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _ReleaseRedirect(),
                                            urllib.request.HTTPSHandler(context=context))
        failure = 'cache-access'
        fd, temporary = tempfile.mkstemp(prefix='.python-', suffix='.tmp', dir=cache)
        with os.fdopen(fd, 'wb') as output:
            failure = 'network'
            with opener.open(urllib.request.Request(URL, headers={'Accept-Encoding': 'identity'}), timeout=30) as response:
                if response.status != 200:
                    raise PythonCacheError('http')
                if response.geturl() != URL and not _asset_url(response.geturl()):
                    raise PythonCacheError('response-policy')
                length = response.headers.get('Content-Length')
                if length is not None and length != str(SIZE):
                    raise PythonCacheError('size')
                if response.headers.get('Content-Encoding', 'identity') != 'identity':
                    raise PythonCacheError('response-policy')
                digest, total, announced = hashlib.sha256(), 0, 0
                deadline = time.monotonic() + 300
                while True:
                    if time.monotonic() > deadline: raise PythonCacheError('deadline')
                    chunk = response.read(min(256 * 1024, SIZE + 1 - total))
                    if not chunk: break
                    total += len(chunk)
                    if total > SIZE: raise PythonCacheError('size')
                    digest.update(chunk)
                    failure = 'cache-access'
                    output.write(chunk)
                    failure = 'network'
                    percent = total * 100 // SIZE
                    if percent >= announced + 10:
                        progress('Downloading private Python: {percent}%'.format(percent=percent))
                        announced = percent
                if total != SIZE: raise PythonCacheError('size')
                if digest.hexdigest() != SHA256: raise PythonCacheError('sha256')
            failure = 'cache-access'
            output.flush(); os.fsync(output.fileno())
        # Only authenticated bytes replace this one immutable cache pathname.
        # replace is portable to Android filesystems that forbid hardlinks.
        failure = 'cache-replace'
        os.replace(temporary, path); temporary = None
        failure = 'cache-access'
        _verified_bytes(path)
        progress('Private Python download verified…')
        return path
    except PythonCacheError:
        raise
    except UserError:
        raise PythonCacheError('cache-invalid') from None
    except urllib.error.HTTPError:
        raise PythonCacheError('http') from None
    except urllib.error.URLError as error:
        raise PythonCacheError('tls' if isinstance(error.reason, ssl.SSLError) else 'network') from None
    except ssl.SSLError:
        raise PythonCacheError('tls') from None
    except (OSError, ValueError, http.client.HTTPException):
        raise PythonCacheError(failure) from None
    finally:
        if temporary is not None:
            try: os.unlink(temporary)
            except OSError: pass


def _member_name(name):
    if (not isinstance(name, str) or len(name) > 512
            or not re.fullmatch(r'[A-Za-z0-9_+.,@=/-]+', name)
            or name.startswith('/') or any(part in ('', '.', '..') for part in name.rstrip('/').split('/'))):
        raise UserError(ARCHIVE_ERROR)
    name = name.rstrip('/')
    if name != 'python' and not name.startswith('python/'):
        raise UserError(ARCHIVE_ERROR)
    if name == 'python/.cytv-runtime.json': raise UserError(ARCHIVE_ERROR)
    return name


def normalize_to_file(data, output_path):
    """Normalize authenticated bytes into a bounded disk-backed gzip tar.

    Consumers must authenticate input first. All archive metadata and links are
    validated here; output contains only ordinary files and directories.
    """
    try:
        records, total = {}, 0
        with tempfile.TemporaryFile() as unpacked:
            # tarfile otherwise parses GNU/PAX records before application limits.
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
                while True:
                    chunk = compressed.read(256 * 1024)
                    if not chunk: break
                    total += len(chunk)
                    if total > MAX_UNPACKED + 16 * 1024 * 1024: raise UserError(ARCHIVE_ERROR)
                    unpacked.write(chunk)
            unpacked.seek(0)
            with tarfile.open(fileobj=unpacked, mode='r:') as source:
                total = 0
                for member in source:
                    name = _member_name(member.name)
                    if name in records or len(records) >= MAX_FILES or member.size < 0 or member.sparse is not None:
                        raise UserError(ARCHIVE_ERROR)
                    if not (member.isdir() or member.isreg() or member.issym() or member.islnk()):
                        raise UserError(ARCHIVE_ERROR)
                    if not member.isreg() and member.size: raise UserError(ARCHIVE_ERROR)
                    total += member.size
                    if total > MAX_UNPACKED: raise UserError(ARCHIVE_ERROR)
                    records[name] = member
                for name in records:
                    parent = posixpath.dirname(name)
                    while parent:
                        if parent in records and not records[parent].isdir(): raise UserError(ARCHIVE_ERROR)
                        parent = posixpath.dirname(parent)

                def resolve(name, seen=()):
                    if name in seen or len(seen) > 64 or name not in records: raise UserError(ARCHIVE_ERROR)
                    member = records[name]
                    if member.isreg(): return member
                    if not (member.issym() or member.islnk()): raise UserError(ARCHIVE_ERROR)
                    link = member.linkname
                    if (not link or link.startswith('/') or len(link) > 512
                            or not re.fullmatch(r'[A-Za-z0-9_+.,@=/-]+', link)):
                        raise UserError(ARCHIVE_ERROR)
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), link) if member.issym() else link)
                    _member_name(target)
                    return resolve(target, seen + (name,))

                files, hashes, expanded = {}, {}, 0
                for name, member in records.items():
                    if member.isdir(): continue
                    target = resolve(name)
                    expanded += target.size
                    if expanded > MAX_UNPACKED: raise UserError(ARCHIVE_ERROR)
                    relative = name[len('python/'):]
                    files[relative] = target
                    digest = hashlib.sha256()
                    with source.extractfile(target) as stream:
                        for chunk in iter(lambda: stream.read(256 * 1024), b''): digest.update(chunk)
                    hashes[relative] = digest.hexdigest()
                if 'bin/python3.13' not in files or not files['bin/python3.13'].mode & 0o111:
                    raise UserError(ARCHIVE_ERROR)
                inventory = {'schema': 1, 'archive_sha256': SHA256, 'files': dict(sorted(hashes.items()))}
                manifest = json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()
                with open(output_path, 'wb') as output:
                    with gzip.GzipFile(filename='', fileobj=output, mode='wb', compresslevel=1, mtime=0) as packed:
                        with tarfile.open(fileobj=packed, mode='w|', format=tarfile.USTAR_FORMAT) as normalized:
                            directories = set()
                            for name in files:
                                parent = posixpath.dirname(name)
                                while parent: directories.add(parent); parent = posixpath.dirname(parent)
                            for name in sorted(directories):
                                item = tarfile.TarInfo(name); item.type = tarfile.DIRTYPE; item.mode = 0o755
                                normalized.addfile(item)
                            for name, target in sorted(files.items()):
                                item = tarfile.TarInfo(name); item.size = target.size
                                item.mode = 0o755 if target.mode & 0o111 else 0o644
                                with source.extractfile(target) as stream: normalized.addfile(item, stream)
                            item = tarfile.TarInfo('.cytv-runtime.json'); item.size = len(manifest); item.mode = 0o644
                            normalized.addfile(item, io.BytesIO(manifest))
                    output.flush(); os.fsync(output.fileno())
                return inventory
    except UserError:
        raise
    except (OSError, ValueError, EOFError, tarfile.TarError, KeyError, RecursionError):
        raise UserError(ARCHIVE_ERROR) from None


def _normalize(data):
    """Small-fixture wrapper; production streams normalization and SSH transfer."""
    with tempfile.TemporaryDirectory(prefix='cytv-python-') as directory:
        path = Path(directory)/'runtime.tar.gz'
        inventory = normalize_to_file(data, path)
        return path.read_bytes(), inventory

# Shell bootstrap commands use a fixed PATH and check root ownership/modes of
# tools, runtime ancestors and every installed inode before executing Python.
_SHELL = r'''
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
LC_ALL=C
export LC_ALL
umask 077
safe_mode() {
    [ "$(stat -Lc '%u' "$1")" = 0 ] || return 1
    mode=$(stat -Lc '%a' "$1")
    [ "$((0$mode & 022))" = 0 ]
}
safe_dir() { [ -d "$1" ] && [ ! -L "$1" ] && safe_mode "$1"; }
ancestors() {
    ancestor=$1
    while :; do
        safe_dir "$ancestor" || return 1
        [ "$ancestor" != / ] || break
        ancestor=${ancestor%/*}; [ -n "$ancestor" ] || ancestor=/
    done
}
for tool in id stat readlink sha256sum tar gzip find df awk uname od mkdir mktemp chmod rm; do
    tool_path=$(command -v "$tool")
    tool_real=$(readlink -f "$tool_path")
    [ -f "$tool_real" ] && [ -x "$tool_real" ] && safe_mode "$tool_real"
    ancestors "${tool_real%/*}"
done
[ "$(id -u)" = 0 ]
'''


def _run(remote, script, data=None, timeout=90):
    return remote.run('/bin/sh -c ' + shlex.quote(_SHELL + script), data=data, timeout=timeout).strip()


def _target_result(reply):
    if reply == 'CYTV_TARGET_READY': return
    match = re.fullmatch(r'CYTV_TARGET_ERROR space ([0-9]{1,16}) ([0-9]{1,16}) (-1|[0-9]{1,16})', reply)
    if match and all(-1 <= int(value) <= 2**53 - 1 for value in match.groups()):
        raise PythonPreflightError('space', *(int(value) for value in match.groups()))
    reasons = {name: name for name in ('abi', 'ownership', 'space-query')}
    raise PythonPreflightError(reasons.get(reply.removeprefix('CYTV_TARGET_ERROR '), 'unknown'))


def _space_script(required_kib):
    # Only aggregate known WAM storage, never export its contents or app names.
    return r'''
space=$(df -Pk "$base") || { printf 'CYTV_TARGET_ERROR space-query'; exit 0; }
available=$(printf '%s\n' "$space" | awk 'END {print $4}')
case "$available" in ''|*[!0-9]*) printf 'CYTV_TARGET_ERROR space-query'; exit 0;; esac
[ "${#available}" -le 9 ] || { printf 'CYTV_TARGET_ERROR space-query'; exit 0; }
if [ "$available" -lt REQUIRED ] && [ ! -e "$slot" ] && [ ! -L "$slot" ]; then
    wam=-1
    session='/var/lib/wam/Default/Session Storage'
    du_path=$(command -v du || true)
    if ancestors "$session" && [ -n "$du_path" ] && safe_mode "$(readlink -f "$du_path")"; then
        if usage=$(du -skx "$session" 2>/dev/null); then
            size=$(printf '%s\n' "$usage" | awk 'END {print $1}')
            case "$size" in ''|*[!0-9]*) ;; *) [ "${#size}" -gt 9 ] || wam=$size;; esac
        fi
    fi
    printf 'CYTV_TARGET_ERROR space %s REQUIRED %s' "$available" "$wam"
    exit 0
fi
printf CYTV_TARGET_READY
'''.replace('REQUIRED', str(required_kib))


def _check_space(remote, required_kib):
    script = 'base=' + shlex.quote(RUNTIME_ROOT) + '\nslot=\nancestors "$base"\n'
    try: _target_result(_run(remote, script + _space_script(required_kib)))
    except TVCommandError: raise PythonPreflightError('tools') from None


def _preflight(remote):
    script = r'''
ancestors /var/lib || { printf 'CYTV_TARGET_ERROR ownership'; exit 0; }
abi() {
case "$(uname -m)" in armv7l|armv8l|aarch64) ;; *) return 1;; esac
shell=$(readlink -f /bin/sh)
[ "$(od -An -tu1 -j 4 -N 2 "$shell" | awk '{$1=$1;print}')" = '1 1' ] || return 1
[ "$(od -An -tu1 -j 18 -N 2 "$shell" | awk '{$1=$1;print}')" = '40 0' ] || return 1
flags=$(od -An -tu1 -j 37 -N 1 "$shell" | awk '{$1=$1;print}')
[ "$((flags & 4))" = 0 ] || return 1
[ "$(od -An -tu1 -j 39 -N 1 "$shell" | awk '{$1=$1;print}')" = 5 ] || return 1
}
abi || { printf 'CYTV_TARGET_ERROR abi'; exit 0; }
'''
    script += 'base=' + shlex.quote(RUNTIME_ROOT) + '\nslot=' + shlex.quote(RUNTIME_ROOT+'/'+SHA256) + '\n'
    script += r'''
if [ ! -e "$base" ] && [ ! -L "$base" ]; then mkdir -m 755 "$base" || { printf 'CYTV_TARGET_ERROR ownership'; exit 0; }; fi
ancestors "$base" || { printf 'CYTV_TARGET_ERROR ownership'; exit 0; }
'''
    try: _target_result(_run(remote, script + _space_script(327680)))
    except TVCommandError: raise PythonPreflightError('tools') from None


def _verify(remote, tree, inventory):
    manifest = json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()
    checksums = ''.join(digest+'  '+name+'\n' for name, digest in sorted(inventory['files'].items()))
    checksums += hashlib.sha256(manifest).hexdigest()+'  .cytv-runtime.json\n'
    script = 'tree=' + shlex.quote(tree) + '\n'
    script += r'''
ancestors "$tree"
cd "$tree"
unsafe=$(find . ! -type d ! -type f -print)
[ -z "$unsafe" ]
unsafe=$(find . ! -user 0 -print)
[ -z "$unsafe" ]
unsafe=$(find . -perm -002 -print)
[ -z "$unsafe" ]
unsafe=$(find . -perm -020 -print)
[ -z "$unsafe" ]
unsafe=$(find . -type f -links +1 -print)
[ -z "$unsafe" ]
'''
    script += 'files=$(find . -type f)\n[ "$(printf \'%s\\n\' "$files" | awk \'END {print NR}\')" = ' + str(len(inventory['files'])+1) + ' ]\n'
    script += 'sha256sum -c - >/dev/null\nprintf CYTV_RUNTIME_VERIFIED\n'
    if _run(remote, script, data=checksums.encode()) != 'CYTV_RUNTIME_VERIFIED': raise UserError(INSTALL_ERROR)


_PROMOTE = r'''
import fcntl, os, stat, sys
base, tree, slot = sys.argv[1:]
fd = os.open(base+'/.install.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
try:
    info = os.fstat(fd)
    assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1 and not info.st_mode & 0o022
    fcntl.flock(fd, fcntl.LOCK_EX)
    if os.path.lexists(slot):
        print('CYTV_RUNTIME_EXISTS')
    else:
        os.rename(tree, slot)
        directory = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(directory)
        finally: os.close(directory)
        print('CYTV_RUNTIME_PROMOTED')
finally: os.close(fd)
'''


def _smoke(remote, executable):
    result = remote.run(shlex.join([executable, '-I', '-B', '-c', SMOKE]), timeout=60).strip()
    if result != 'CYTV_RUNTIME_SMOKE': raise UserError(INSTALL_ERROR)


def select_python(remote, cache_dir, progress, provision=False):
    """Return system Python, or (only when authorized) a verified private slot."""
    try:
        if remote.run(shlex.join(['/usr/bin/python3', '-I', '-B', '-c', SYSTEM_PROBE]), timeout=60).strip() == 'CYTV_SYSTEM_PYTHON':
            return '/usr/bin/python3'
    except TVCommandError:
        pass
    except UserError:
        raise
    except Exception:
        raise UserError(INSTALL_ERROR) from None
    if not provision: raise UserError(MISSING_ERROR)
    stage = None
    normalized_directory = None
    try:
        progress('Checking TV compatibility for private Python…')
        try: _preflight(remote)
        except PythonPreflightError: raise
        except (UserError, OSError): raise PythonPreflightError() from None
        raw = _verified_bytes(prime_cache(cache_dir, progress))
        progress('Preparing the verified private Python runtime…')
        normalized_directory = tempfile.TemporaryDirectory(prefix='cytv-python-')
        payload = Path(normalized_directory.name)/'runtime.tar.gz'
        inventory = normalize_to_file(raw, payload)
        del raw
        with payload.open('rb') as stream:
            payload_hash = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else _stream_hash(stream)
        slot = RUNTIME_ROOT + '/' + SHA256
        executable = slot + '/bin/python3.13'
        exists = _run(remote, 'slot='+shlex.quote(slot)+'\nif [ -e "$slot" ] || [ -L "$slot" ]; then printf CYTV_SLOT_EXISTS; else printf CYTV_SLOT_MISSING; fi\n')
        if exists == 'CYTV_SLOT_EXISTS':
            _verify(remote, slot, inventory); _smoke(remote, executable)
            progress('Using the verified private Python runtime…')
            return executable
        if exists != 'CYTV_SLOT_MISSING': raise UserError(INSTALL_ERROR)
        _check_space(remote, (MAX_UNPACKED+payload.stat().st_size+32*1024*1024+1023)//1024)
        script = 'base='+shlex.quote(RUNTIME_ROOT)+'\nancestors "$base"\n'
        script += 'stage=$(mktemp -d "$base/.stage-XXXXXXXXXXXX")\nprintf \'%s\\n\' "$stage"\n# CYTV_STAGE_READY\n'
        stage = _run(remote, script)
        if not re.fullmatch(re.escape(RUNTIME_ROOT)+r'/\.stage-[A-Za-z0-9]{6,32}', stage):
            stage = None; raise UserError(INSTALL_ERROR)
        progress('Installing private Python on the TV…')
        if callable(getattr(remote, 'upload_file', None)):
            remote.upload_file(stage+'/runtime.tar.gz', payload, mode=0o600, timeout=600)
        elif payload.stat().st_size <= 1024 * 1024:
            remote.upload(stage+'/runtime.tar.gz', payload.read_bytes(), mode=0o600)
        else:
            raise UserError(INSTALL_ERROR)
        script = 'stage='+shlex.quote(stage)+'\nancestors "$stage"\n'
        script += '[ "$(sha256sum "$stage/runtime.tar.gz" | awk \'{print $1}\')" = '+shlex.quote(payload_hash)+' ]\n'
        script += 'mkdir -m 755 "$stage/tree"\ntar -xzf "$stage/runtime.tar.gz" -C "$stage/tree"\n'
        _run(remote, script, timeout=180)
        tree = stage+'/tree'
        _verify(remote, tree, inventory)
        _smoke(remote, tree+'/bin/python3.13')
        result = remote.run(shlex.join([tree+'/bin/python3.13', '-I', '-B', '-c', _PROMOTE, RUNTIME_ROOT, tree, slot]), timeout=90).strip()
        if result not in ('CYTV_RUNTIME_PROMOTED', 'CYTV_RUNTIME_EXISTS'): raise UserError(INSTALL_ERROR)
        _verify(remote, slot, inventory); _smoke(remote, executable)
        progress('Private Python is ready…')
        return executable
    except UserError as error:
        if isinstance(error, (PythonPreflightError, PythonCacheError)): raise
        if type(error) is UserError and str(error) in (DOWNLOAD_ERROR, CACHE_ERROR, ARCHIVE_ERROR, TARGET_ERROR, INSTALL_ERROR): raise
        raise UserError(INSTALL_ERROR) from None
    except Exception:
        raise UserError(INSTALL_ERROR) from None
    finally:
        if normalized_directory is not None: normalized_directory.cleanup()
        if stage is not None:
            try: _run(remote, 'stage='+shlex.quote(stage)+'\nancestors "$stage"\nrm -rf "$stage"\n')
            except Exception: pass

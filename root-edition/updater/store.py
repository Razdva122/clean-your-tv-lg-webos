"""Small root-owned JSON store. All operations are anchored to a checked dir fd."""
from contextlib import contextmanager
import fcntl
import json
import math
import os
import re
import stat
import uuid

MAX_BYTES = 4 * 1024 * 1024


def encode(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':'), sort_keys=True).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError('invalid JSON value') from error


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('duplicate JSON key')
        result[key] = value
    return result


class Store:
    def __init__(self, root, uid=0):
        self.root = os.path.abspath(root)
        self.uid = uid
        if self.root == '/': raise ValueError('invalid store directory')
        parent = self._walk(os.path.dirname(self.root))
        try:
            try: os.mkdir(os.path.basename(self.root), 0o700, dir_fd=parent)
            except FileExistsError: pass
        finally:
            os.close(parent)
        os.close(self._directory())

    def _walk(self, path):
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in path.strip('/').split('/'):
                if not part: continue
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
                info = os.fstat(fd)
                if (info.st_uid not in (0, self.uid)
                        or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX)):
                    raise ValueError('unsafe store ancestor')
            return fd
        except (OSError, ValueError) as error:
            os.close(fd)
            raise ValueError('unsafe store path') from error

    def _directory(self):
        fd = self._walk(self.root)
        try:
            info = os.fstat(fd)
            if info.st_uid != self.uid or info.st_mode & 0o022:
                raise ValueError('unsafe store ownership or permissions')
            return fd
        except (OSError, ValueError) as error:
            os.close(fd)
            raise ValueError('unsafe store directory') from error

    @staticmethod
    def _name(name):
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}(?:\.json)?', name):
            raise ValueError('unsafe store name')
        return name if name.endswith('.json') else name + '.json'

    def _check(self, info):
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid
                or info.st_mode & 0o022 or info.st_nlink != 1):
            raise ValueError('unsafe store file')
        if info.st_size > MAX_BYTES: raise ValueError('store file too large')

    def read(self, name):
        return self._read(self._name(name))

    def _read(self, name):
        # Internal callers may select this one fixed legacy receipt.
        if name != 'startup-hook.previous.json': name = self._name(name)
        directory = self._directory()
        try:
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError:
                return None
            except OSError as error:
                raise ValueError('unsafe store file') from error
            with os.fdopen(fd, 'rb') as source:
                self._check(os.fstat(source.fileno()))
                raw = source.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES: raise ValueError('store file too large')
            try:
                value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                                   parse_constant=lambda value: (_ for _ in ()).throw(ValueError('invalid number')))
                if value is None: raise ValueError('null is not a stored record')
                return value
            except (ValueError, UnicodeError, RecursionError) as error:
                raise ValueError('corrupt store JSON') from error
        finally:
            os.close(directory)

    def write(self, name, value):
        name = self._name(name)
        if value is None: raise ValueError('null is not a stored record')
        raw = encode(value)
        if len(raw) > MAX_BYTES: raise ValueError('store value too large')
        directory = self._directory()
        temporary = '.write-' + uuid.uuid4().hex
        try:
            try:
                self._check(os.stat(name, dir_fd=directory, follow_symlinks=False))
                if name.startswith('profile-'): raise ValueError('immutable profile exists')
            except FileNotFoundError:
                pass
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
            with os.fdopen(fd, 'wb') as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
            if name.startswith('profile-'):
                os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory,
                        follow_symlinks=False)
                os.unlink(temporary, dir_fd=directory)
            else:
                os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            try: os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError: pass
            os.close(directory)
        return value

    @contextmanager
    def lock(self, blocking=True):
        directory = self._directory()
        fd = None
        try:
            try:
                fd = os.open('worker.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                             0o600, dir_fd=directory)
                self._check(os.fstat(fd))
            except OSError as error:
                raise ValueError('unsafe worker lock') from error
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            self.lock_fd=fd
            yield
        finally:
            self.lock_fd=None
            if fd is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            os.close(directory)


def _cache_descriptor(value):
    if not isinstance(value, dict): raise ValueError('missing cache references')
    items = value.get('components', [value])
    if (not isinstance(items, list) or not items
            or any(not isinstance(item, dict) or not isinstance(item.get('sha256'), str)
                   or not re.fullmatch('[a-f0-9]{64}', item['sha256']) for item in items)):
        raise ValueError('unknown cache references')


def _cache_snapshot(stores, product_complete=False):
    """Only understood, finished journals authorize a cache sweep.

    Callers hold installation.device_operation's product lock. The second read
    below also detects changed references before unlinking; no journal is edited.
    """
    records = []
    fixed = {'baseline', 'current', 'current-root', 'current-no-root', 'transaction',
             'bootstrap', 'bootstrap-bundle', 'infrastructure', 'installed-package',
             'installed-terminal', 'registration', 'legacy-lockdown', 'python-runtime',
             'installer-accepted', 'mutable', 'startup-hook', 'startup-hook.previous'}
    terminal_seen = product_complete is True
    for store in stores:
        directory = store._directory()
        try:
            names = sorted(name for name in os.listdir(directory) if name.endswith('.json'))
            for filename in names:
                name = filename[:-5]
                if name not in fixed and not re.fullmatch(r'(?:profile|healthy|healthy-rollback|helper-resume|renewal-pause|mutable)-[a-f0-9]{32}(?:-rollback)?', name):
                    raise ValueError('unknown retention record')
                value = store._read(filename) if name == 'startup-hook.previous' else store.read(name)
                if not isinstance(value, dict): raise ValueError('unknown retention record')
                if name in {'baseline', 'current', 'current-root', 'current-no-root'}: _cache_descriptor(value)
                if name == 'bootstrap' and value.get('phase') != 'complete':
                    raise ValueError('unfinished bootstrap')
                if name == 'transaction':
                    phase = value.get('phase')
                    if (value.get('schema') != 1 or not re.fullmatch('[a-f0-9]{32}', value.get('id', ''))
                            or phase not in {'complete', 'rolled-back', 'aborted'}
                            or value.get('homeResumePhase') != phase
                            or value.get('profile') != 'profile-'+value['id']
                            or not isinstance(value.get('profileDigest'), str) or not re.fullmatch('[a-f0-9]{64}', value['profileDigest'])
                            or type(value.get('rollbackAttempted')) is not bool
                            or phase in ('aborted','complete') and value['rollbackAttempted']
                            or any(type(value.get(key)) not in (int,float) or not math.isfinite(value[key]) or value[key]<0 for key in ('created','updated'))):
                        raise ValueError('unfinished update')
                    for descriptor in ('candidate', 'prior'): _cache_descriptor(value.get(descriptor))
                    components = value.get('components', [value])
                    if not isinstance(components, list) or not components: raise ValueError('unknown update evidence')
                    for component in components:
                        if not isinstance(component, dict): raise ValueError('unknown component evidence')
                        for leg in ('installEvidence', 'rollbackEvidence'):
                            evidence = component.get(leg)
                            if not isinstance(evidence, dict) or not {'submitted', 'terminal'} <= evidence.keys():
                                raise ValueError('unknown update evidence')
                            submitted, terminal = evidence['submitted'], evidence['terminal']
                            if submitted is not None and (not isinstance(submitted, dict) or not submitted):
                                raise ValueError('unknown submission evidence')
                            if 'intent' in evidence and type(evidence['intent']) is not bool:
                                raise ValueError('unknown installer intent')
                            if (evidence.get('intent', False) or submitted is not None) and terminal is None:
                                raise ValueError('unknown installer outcome')
                            if terminal is not None and (submitted is None or not isinstance(terminal, dict) or type(terminal.get('success')) is not bool):
                                raise ValueError('unknown installer outcome')
                            if phase == 'aborted' and (submitted is not None or terminal is not None or evidence.get('intent', False)):
                                raise ValueError('aborted after installer intent')
                        if phase == 'complete' and (component['installEvidence']['terminal'] or {}).get('success') is not True:
                            raise ValueError('missing installation success')
                        if phase == 'rolled-back' and (component['installEvidence'].get('intent', component['installEvidence']['submitted'] is not None)) and (component['rollbackEvidence']['terminal'] or {}).get('success') is not True:
                            raise ValueError('missing rollback success')
                    if phase == 'rolled-back' and not any((component['rollbackEvidence']['terminal'] or {}).get('success') is True for component in components):
                        raise ValueError('missing rollback terminal proof')
                    terminal_seen = True
                records.append((store.root, filename, value))
        finally:
            os.close(directory)
    if not terminal_seen: raise ValueError('terminal update proof required')
    return records


def _cache_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class _RetentionChanged(ValueError):
    """A previously admitted proof or deletion plan changed."""


def retention_reason(error):
    """Classify failures without forwarding exception text or private values."""
    if isinstance(error, _RetentionChanged): return 'proof-changed'
    while error is not None:
        if isinstance(error, OSError): return 'filesystem-error'
        error = error.__cause__
    return 'admission-refused'


def retention_summary(scope, reason, removed=0):
    """Best-effort fixed summaries; never records paths, IDs or inventories."""
    if (scope not in ('cache', 'cache-peer', 'staging')
            or reason not in ('complete', 'admission-refused', 'missing-inventory',
                              'proof-changed', 'filesystem-error')
            or type(removed) is not int or removed < 0): return
    message = 'cytv-retention scope='+scope+' reason='+reason+' removed='+str(removed)
    # Workers may discard stderr. The platform logger is an independent sink;
    # neither logging availability nor its failures may affect retention.
    try:
        import syslog
        syslog.syslog(syslog.LOG_INFO, message)
    except Exception:
        pass
    try:
        import sys
        sys.stderr.write(message+'\n')
    except Exception:
        pass


def prune_update_caches(stores, *, product_complete=False):
    """Remove only verified unreferenced blobs after terminal update/Home proof.

    No age/size guesses: immutable baseline, latest current/rollback and legacy
    cross-store references remain. Unknown files/records disable the whole sweep.
    Product ownership excludes cooperative writers; root compromise is out of scope.
    """
    import hashlib
    from contextlib import ExitStack
    removed = 0
    reason = 'complete'
    revalidating = False
    try:
        before = _cache_snapshot(stores, product_complete)
        protected = set()
        def references(value):
            if isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value): protected.add(value)
            elif isinstance(value, dict):
                for key, item in value.items(): references(key); references(item)
            elif isinstance(value, list):
                for item in value: references(item)
        for _, _, value in before: references(value)
        with ExitStack() as stack:
            plan = []
            for store in stores:
                root = store._directory();stack.callback(os.close, root)
                try: cache = os.open('cache', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
                except FileNotFoundError: continue
                stack.callback(os.close, cache)
                info = os.fstat(cache)
                if info.st_uid != store.uid or info.st_mode & 0o022: raise ValueError('unsafe cache')
                for name in sorted(os.listdir(cache)):
                    if not re.fullmatch('[a-f0-9]{64}(?:\\.ipk)?', name): raise ValueError('unknown cache entry')
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=cache)
                    with os.fdopen(fd, 'rb') as stream:
                        info = os.fstat(stream.fileno())
                        if (not stat.S_ISREG(info.st_mode) or info.st_uid != store.uid or info.st_nlink != 1
                                or info.st_mode & 0o022 or info.st_size > 64*1024*1024): raise ValueError('unsafe cache entry')
                        digest = hashlib.sha256()
                        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
                        if _cache_identity(os.fstat(stream.fileno())) != _cache_identity(info) or digest.hexdigest() != name[:64]: raise _RetentionChanged('changed cache entry')
                    if name[:64] not in protected: plan.append((cache, name, info))
            revalidating = True
            if _cache_snapshot(stores, product_complete) != before: raise _RetentionChanged('changed cache references')
            # Validate all entries before the first mutation. Each unlink remains
            # anchored to the checked directory and checks the original identity.
            for cache, name, info in plan:
                if _cache_identity(os.stat(name, dir_fd=cache, follow_symlinks=False)) != _cache_identity(info): raise _RetentionChanged('changed cache entry')
            for cache, name, info in plan:
                if _cache_snapshot(stores, product_complete) != before or _cache_identity(os.stat(name, dir_fd=cache, follow_symlinks=False)) != _cache_identity(info):
                    raise _RetentionChanged('changed retention plan')
                os.unlink(name, dir_fd=cache);removed += 1;os.fsync(cache)
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Retention failure must not change an update/recovery outcome.
        reason = retention_reason(error)
        if revalidating and reason == 'admission-refused': reason = 'proof-changed'
    retention_summary('cache', reason, removed)
    return removed


def prune_peer_caches(store, peer):
    """The caller already owns the product operation; absent peers stay absent."""
    try:
        stores = [store]
        if os.path.lexists(peer): stores.append(Store(peer, uid=store.uid))
        return prune_update_caches(stores)
    except (OSError, ValueError) as error:
        retention_summary('cache-peer', retention_reason(error))
        return 0


def retire_verified_files(store, relative, expected, stable):
    """Retire exactly a sealed staging inventory, retaining unknown trees intact.

    The caller holds the product lock and supplies terminal receipt revalidation.
    Missing files support interruption after a previous terminal-only deletion.
    """
    import hashlib
    from contextlib import ExitStack
    removed = 0
    reason = 'complete'
    try:
        if not isinstance(expected, dict) or not expected:
            retention_summary('staging', 'missing-inventory')
            return 0
        for name, digest in expected.items():
            if (not isinstance(name, str) or not re.fullmatch(r'(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+', name)
                    or any(part in ('.', '..') for part in name.split('/'))
                    or not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest)):
                raise ValueError('unsafe retirement inventory')
        if not re.fullmatch(r'(?:request|system-replacement)-[a-f0-9]{32}', relative): raise ValueError('unsafe staging root')
        with ExitStack() as stack:
            root = store._walk(os.path.join(store.root, relative));stack.callback(os.close, root)
            plan = []
            def scan(directory, prefix):
                directory_info = os.fstat(directory)
                if directory_info.st_uid != store.uid or directory_info.st_mode & 0o022: raise ValueError('unsafe staging directory')
                for name in sorted(os.listdir(directory)):
                    path = prefix + name
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if info.st_uid != store.uid or info.st_mode & 0o022: raise ValueError('unsafe staging owner')
                    if stat.S_ISDIR(info.st_mode):
                        if not any(item.startswith(path+'/') for item in expected): raise ValueError('unknown staging directory')
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                        stack.callback(os.close, child);scan(child, path+'/')
                    else:
                        if path not in expected or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 64*1024*1024:
                            raise ValueError('unsafe staging entry')
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                        with os.fdopen(fd, 'rb') as stream:
                            digest = hashlib.sha256()
                            for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
                            if _cache_identity(os.fstat(stream.fileno())) != _cache_identity(info) or digest.hexdigest() != expected[path]:
                                raise _RetentionChanged('staging changed')
                        plan.append((directory, name, info))
            # Logs and journals outside the named payload roots are never swept.
            for name in sorted({name.split('/')[0] for name in expected}):
                if not any(item.startswith(name+'/') for item in expected): raise ValueError('payload directory required')
                try: child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
                except FileNotFoundError: continue
                stack.callback(os.close, child);scan(child, name+'/')
            if not stable(): raise _RetentionChanged('terminal staging proof changed')
            for directory, name, info in plan:
                if _cache_identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) != _cache_identity(info):
                    raise _RetentionChanged('staging changed')
            for directory, name, info in plan:
                if not stable() or _cache_identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) != _cache_identity(info):
                    raise _RetentionChanged('staging retirement changed')
                os.unlink(name, dir_fd=directory);removed += 1;os.fsync(directory)
    except (OSError, ValueError, TypeError, KeyError) as error:
        reason = retention_reason(error)
    retention_summary('staging', reason, removed)
    return removed

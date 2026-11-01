"""Offline trust-boundary checks for optional Root Python acquisition."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import stat
import types
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from cytv.errors import UserError, TVCommandError
from cytv import python_runtime as runtime


def archive(entries):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as output:
        for name, kind, value in entries:
            info = tarfile.TarInfo(name)
            info.mode = 0o755 if name.endswith('python3.13') else 0o644
            if kind == 'file':
                info.size = len(value)
                output.addfile(info, io.BytesIO(value))
            else:
                info.type = {'dir': tarfile.DIRTYPE, 'sym': tarfile.SYMTYPE,
                             'hard': tarfile.LNKTYPE, 'fifo': tarfile.FIFOTYPE}[kind]
                if kind in ('sym', 'hard'): info.linkname = value
                output.addfile(info)
    return data.getvalue()


GOOD = [('python', 'dir', None), ('python/bin', 'dir', None),
        ('python/bin/python3.13', 'file', b'\x7fELFfixture'),
        ('python/bin/python3', 'sym', 'python3.13'),
        ('python/lib', 'dir', None), ('python/lib/data', 'file', b'hello')]


class Response(io.BytesIO):
    status = 200
    headers = {}
    def geturl(self): return runtime.URL


class Remote:
    def __init__(self, system=True, unsupported=False, smoke=True):
        self.system, self.unsupported, self.smoke = system, unsupported, smoke
        self.commands, self.uploads = [], []
    def run(self, command, data=None, timeout=30):
        self.commands.append((command, data))
        if 'CYTV_SYSTEM_PYTHON' in command:
            if not self.system: raise TVCommandError(127)
            return 'CYTV_SYSTEM_PYTHON\n'
        if 'CYTV_TARGET_READY' in command:
            if self.unsupported: raise TVCommandError(1)
            return 'CYTV_TARGET_READY\n'
        if 'CYTV_SLOT_EXISTS' in command: return 'CYTV_SLOT_MISSING\n'
        if 'CYTV_STAGE_READY' in command: return runtime.RUNTIME_ROOT + '/.stage-fixture\n'
        if 'CYTV_RUNTIME_SMOKE' in command:
            if not self.smoke: raise TVCommandError(1)
            return 'CYTV_RUNTIME_SMOKE\n'
        if 'CYTV_RUNTIME_VERIFIED' in command: return 'CYTV_RUNTIME_VERIFIED\n'
        if 'CYTV_RUNTIME_PROMOTED' in command: return 'CYTV_RUNTIME_PROMOTED\n'
        return ''
    def upload(self, path, data, mode=0o600): self.uploads.append((path, data, mode))


class RuntimeTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','Requires the POSIX device shell ABI fixture')
    def test_shell_abi_accepts_arm32_userspace_on_aarch64_without_accepting_elf64(self):
        import shlex
        remote=Remote(system=False)
        runtime._preflight(remote)
        script=shlex.split(remote.commands[-1][0])[-1]
        fragment=script[script.index('abi() {'):script.index('\nabi ||')] + '\nabi\n'
        with tempfile.TemporaryDirectory() as folder:
            elf=Path(folder)/'shell'
            for kernel in ('armv7l','armv8l','aarch64'):
                for elf_class in (1,2):
                    header=bytearray(40);header[:6]=b'\x7fELF\x01\x01';header[4]=elf_class;header[18]=40;header[39]=5;elf.write_bytes(header)
                    prefix='set -e\nuname() { printf "%s\n" "$CYTV_TEST_KERNEL"; }\nreadlink() { printf "%s\n" "$CYTV_TEST_ELF"; }\n'
                    with self.subTest(kernel=kernel,elf_class=elf_class):
                        result=subprocess.run(['/bin/sh','-c',prefix+fragment],env=dict(os.environ,CYTV_TEST_KERNEL=kernel,CYTV_TEST_ELF=str(elf)),capture_output=True,text=True)
                        self.assertEqual(result.returncode==0,elf_class==1,result.stderr)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name).resolve()/'cache'
        self.messages = []

    def pin_fixture(self, data):
        return patch.multiple(runtime, SIZE=len(data), SHA256=hashlib.sha256(data).hexdigest())

    def test_system_python_never_touches_network_cache_or_provisioning(self):
        remote = Remote()
        with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual(runtime.select_python(remote, self.cache, self.messages.append, True), '/usr/bin/python3')
        self.assertFalse(self.cache.exists())
        self.assertFalse(remote.uploads)
        self.assertEqual(len(remote.commands), 1)

    def test_read_only_selection_refuses_missing_python_without_network(self):
        with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            with self.assertRaises(UserError): runtime.select_python(Remote(False), self.cache, self.messages.append)
        self.assertFalse(self.cache.exists())

    def test_unsupported_target_is_rejected_before_download(self):
        with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            with self.assertRaises(UserError): runtime.select_python(Remote(False, True), self.cache, self.messages.append, True)

    @unittest.skipUnless(os.name == 'posix', 'TV probe requires POSIX')
    def test_smoke_runs_real_required_stdlib_operations(self):
        result = subprocess.run([os.sys.executable, '-I', '-c', runtime.SMOKE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'CYTV_RUNTIME_SMOKE')

    @unittest.skipUnless(os.name == 'posix', 'TV probe requires POSIX')
    def test_system_probe_rejects_older_version_and_runs_operations(self):
        result = subprocess.run([os.sys.executable, '-I', '-c', runtime.SYSTEM_PROBE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'CYTV_SYSTEM_PYTHON')
        old = runtime.SYSTEM_PROBE.replace('sys.version_info >= (3, 9)', '(3, 8) >= (3, 9)')
        result = subprocess.run([os.sys.executable, '-I', '-c', old], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_normalization_resolves_internal_links_into_regular_inventory_files(self):
        raw = archive(GOOD + [('python/lib/alias', 'hard', 'python/lib/data')])
        payload, inventory = runtime._normalize(raw)
        self.assertEqual(inventory['schema'], 1)
        self.assertEqual(inventory['archive_sha256'], runtime.SHA256)
        self.assertEqual(inventory['files']['lib/alias'], hashlib.sha256(b'hello').hexdigest())
        with tarfile.open(fileobj=io.BytesIO(payload)) as result:
            self.assertTrue(all(item.isdir() or item.isfile() for item in result))
            self.assertEqual(result.extractfile('bin/python3').read(), b'\x7fELFfixture')
            self.assertEqual(json.load(result.extractfile('.cytv-runtime.json')), inventory)

    def test_archive_rejects_traversal_duplicates_special_files_and_escaping_links(self):
        bad = [('../bad', 'file', b'x'), ('/python/bad', 'file', b'x'),
               ('python/bin/python3.13', 'file', b'duplicate'),
               ('python/fifo', 'fifo', None), ('python/escape', 'sym', '../../outside'),
               ('python/absolute', 'sym', '/etc/passwd'), ('python/dangling', 'sym', 'missing'),
               ('python/lib/up', 'hard', '../outside'), ('python/.cytv-runtime.json', 'file', b'x')]
        for entry in bad:
            with self.subTest(entry=entry):
                with self.assertRaises(UserError): runtime._normalize(archive(GOOD + [entry]))

    def test_archive_rejects_link_cycles_and_directory_link_traversal(self):
        for entries in [
            [('python/a', 'sym', 'b'), ('python/b', 'sym', 'a')],
            [('python/link', 'sym', 'lib'), ('python/link/payload', 'file', b'x')],
            [('python/file', 'file', b'x'), ('python/file/payload', 'file', b'x')],
        ]:
            with self.subTest(entries=entries):
                with self.assertRaises(UserError): runtime._normalize(archive(GOOD + entries))

    def test_archive_rejects_member_and_expansion_limits(self):
        with patch.object(runtime, 'MAX_UNPACKED', 5):
            with self.assertRaises(UserError): runtime._normalize(archive(GOOD))
        with patch.object(runtime, 'MAX_FILES', 2):
            with self.assertRaises(UserError): runtime._normalize(archive(GOOD))

    def test_expansion_is_bounded_before_tar_extension_parser(self):
        bomb = gzip.compress(b'x'*(17*1024*1024))
        with patch.object(runtime, 'MAX_UNPACKED', 1), patch.object(runtime.tarfile, 'open', side_effect=AssertionError('unbounded tar parser')):
            with self.assertRaises(UserError): runtime._normalize(bomb)

    def test_download_failures_never_expose_network_credentials(self):
        with patch.object(runtime.urllib.request, 'build_opener') as builder:
            builder.return_value.open.side_effect = OSError('https://user:secret@example.invalid/?signature=secret')
            with self.assertRaises(UserError) as raised:
                runtime.prime_cache(self.cache, self.messages.append)
        self.assertEqual(str(raised.exception), runtime.DOWNLOAD_ERROR)
        self.assertFalse(list(self.cache.glob('.python-*')))

    def test_download_and_cache_failures_have_distinct_safe_reasons(self):
        import ssl
        import urllib.error
        import http.client
        cases = [('network', OSError('PRIVATE-URL')),
                 ('tls', urllib.error.URLError(ssl.SSLError('PRIVATE-CERT'))),
                 ('http', urllib.error.HTTPError('https://PRIVATE-URL', 403, 'PRIVATE-RESPONSE', {}, None)),
                 ('network', http.client.IncompleteRead(b'PRIVATE-DATA'))]
        for reason, error in cases:
            with self.subTest(reason=reason), patch.object(runtime.urllib.request, 'build_opener') as builder:
                builder.return_value.open.side_effect = error
                with self.assertRaises(UserError) as caught:
                    runtime.prime_cache(self.cache, self.messages.append)
                self.assertEqual(getattr(caught.exception, 'reason', None), reason)
                self.assertNotIn('PRIVATE', str(caught.exception))
                self.assertFalse(list(self.cache.glob('.python-*')))
                if hasattr(error, 'close'): error.close()
        for reason, target in [('cache-access', '_cache_directory'),
                               ('cache-access', 'tempfile.mkstemp'),
                               ('cache-access', 'os.fsync'),
                               ('cache-replace', 'os.replace')]:
            raw = archive(GOOD)
            with self.subTest(target=target), self.pin_fixture(raw), \
                 patch.object(runtime.urllib.request, 'build_opener') as builder, \
                 patch('cytv.python_runtime.' + target, side_effect=PermissionError('PRIVATE-PATH')):
                builder.return_value.open.return_value = Response(raw)
                with self.assertRaises(UserError) as caught:
                    runtime.prime_cache(self.cache, self.messages.append)
                self.assertEqual(getattr(caught.exception, 'reason', None), reason)
                self.assertNotIn('PRIVATE', str(caught.exception))
                self.assertFalse((self.cache / (runtime.SHA256 + '.tar.gz')).exists())
                self.assertFalse(list(self.cache.glob('.python-*')))

    def test_size_hash_policy_and_deadline_failures_are_distinguishable(self):
        raw = archive(GOOD)
        for reason, body, headers, url in [
                ('size', raw[:-1], {}, None), ('size', raw+b'x', {}, None),
                ('sha256', b'x'*len(raw), {}, None),
                ('size', raw, {'Content-Length': '1'}, None),
                ('response-policy', raw, {'Content-Encoding': 'gzip'}, None),
                ('response-policy', raw, {}, 'https://PRIVATE-URL')]:
            with self.subTest(reason=reason, headers=headers), self.pin_fixture(raw), \
                 patch.object(runtime.urllib.request, 'build_opener') as builder:
                response = Response(body); response.headers = headers
                if url: response.geturl = lambda: url
                builder.return_value.open.return_value = response
                with self.assertRaises(UserError) as caught:
                    runtime.prime_cache(self.cache, self.messages.append)
                self.assertEqual(getattr(caught.exception, 'reason', None), reason)
                self.assertFalse((self.cache / (runtime.SHA256 + '.tar.gz')).exists())
                self.assertFalse(list(self.cache.glob('.python-*')))
        with self.pin_fixture(raw), patch.object(runtime.urllib.request, 'build_opener') as builder, \
             patch.object(runtime.time, 'monotonic', side_effect=[0, 301]):
            builder.return_value.open.return_value = Response(raw)
            with self.assertRaises(UserError) as caught:
                runtime.prime_cache(self.cache, self.messages.append)
            self.assertEqual(getattr(caught.exception, 'reason', None), 'deadline')
            self.assertFalse(list(self.cache.glob('.python-*')))

    def test_cache_diagnostic_survives_provisioning_error_boundary(self):
        from cytv import diagnostics, state
        with patch.object(runtime.urllib.request, 'build_opener') as builder:
            builder.return_value.open.side_effect = OSError('PRIVATE-URL')
            with self.assertRaises(UserError) as caught:
                runtime.select_python(Remote(False), self.cache, self.messages.append, True)
        store = state.Store(Path(self.temp.name)/'reports-state')
        report = json.loads(diagnostics.create_report(store, 'install', None, 'preflight', caught.exception).read_text())
        self.assertEqual(report.get('python_cache'), {'reason': 'network'})
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_invalid_existing_cache_keeps_original_bytes_and_safe_reason(self):
        raw = archive(GOOD)
        with self.pin_fixture(raw), patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            self.cache.mkdir(mode=0o700)
            path = self.cache / (runtime.SHA256 + '.tar.gz')
            path.write_bytes(b'original-corrupt-bytes')
            with self.assertRaises(UserError) as caught:
                runtime.prime_cache(self.cache, self.messages.append)
            self.assertEqual(getattr(caught.exception, 'reason', None), 'cache-invalid')
            self.assertEqual(path.read_bytes(), b'original-corrupt-bytes')

    def test_uncertain_system_probe_failure_never_provisions(self):
        remote = Remote(False)
        remote.run = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('private connection details'))
        with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            with self.assertRaises(UserError) as raised:
                runtime.select_python(remote, self.cache, self.messages.append, True)
        self.assertNotIn('private connection details', str(raised.exception))
        self.assertFalse(self.cache.exists())

    def test_download_verified_cache_reused_without_network(self):
        raw = archive(GOOD)
        with self.pin_fixture(raw):
            self.cache.mkdir(mode=0o700)
            path = self.cache/(runtime.SHA256+'.tar.gz')
            path.write_bytes(raw)
            with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
                self.assertEqual(runtime.prime_cache(self.cache, self.messages.append), path)

    def test_corrupt_or_indirect_cache_is_not_used_or_replaced(self):
        raw = archive(GOOD)
        with self.pin_fixture(raw):
            self.cache.mkdir(mode=0o700)
            path = self.cache/(runtime.SHA256+'.tar.gz')
            for indirect in (False, True):
                with self.subTest(indirect=indirect):
                    if indirect:
                        if os.name != 'posix': continue
                        other = self.cache/'other'; other.write_bytes(raw); path.symlink_to(other)
                    else: path.write_bytes(b'corrupt')
                    with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
                        with self.assertRaises(UserError): runtime.prime_cache(self.cache, self.messages.append)
                    path.unlink()

    @unittest.skipUnless(os.name == 'posix', 'POSIX cache ancestry')
    def test_cache_rejects_symlink_parent_and_writable_parent(self):
        raw = archive(GOOD)
        parent = Path(self.temp.name).resolve()/'parent'
        parent.mkdir(mode=0o700)
        link = Path(self.temp.name).resolve()/'alias'
        link.symlink_to(parent, target_is_directory=True)
        with self.pin_fixture(raw), patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            with self.assertRaises(UserError): runtime.prime_cache(link/'cache', self.messages.append)
            parent.chmod(0o777)
            with self.assertRaises(UserError): runtime.prime_cache(parent/'cache', self.messages.append)
        parent.chmod(0o700)

    def android_cache_fixture(self, alias=False):
        anchor = '/data/user/0/com.cleanyourtv.android/files'
        cache = anchor+'/profiles/python-cache'
        def directory(uid, mode=0o755, gid=None):
            return types.SimpleNamespace(st_mode=stat.S_IFDIR | mode, st_uid=uid,
                                         st_gid=uid if gid is None else gid)
        records = {'/': directory(0), '/data': directory(1000, 0o771),
                   '/data/user': directory(1000, 0o711), '/data/user/0': directory(1000, 0o711)}
        for prefix in ('/data/user/0', '/data/data'):
            records[prefix+'/com.cleanyourtv.android'] = directory(10123, 0o700)
            records[prefix+'/com.cleanyourtv.android/files'] = directory(10123, 0o771)
            records[prefix+'/com.cleanyourtv.android/files/profiles'] = directory(10123, 0o700)
            records[prefix+'/com.cleanyourtv.android/files/profiles/python-cache'] = directory(10123, 0o700)
        if alias:
            records['/data/data'] = directory(1000, 0o771)
            records['/data/user/0'] = types.SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_uid=0, st_gid=0)
        application = types.SimpleNamespace(getPackageName=lambda: 'com.cleanyourtv.android',
                                           getFilesDir=lambda: types.SimpleNamespace(getAbsolutePath=lambda: anchor))
        java = types.SimpleNamespace(jclass=lambda name: types.SimpleNamespace(
            getPlatform=lambda: types.SimpleNamespace(getApplication=lambda: application)))
        return cache, records, java

    @unittest.skipUnless(os.name == 'posix', 'Android is POSIX')
    def test_android_cache_uses_private_application_anchor_with_system_ancestors(self):
        for alias in (False, True):
            with self.subTest(alias=alias):
                cache, records, java = self.android_cache_fixture(alias)
                with patch.dict(os.sys.modules, {'java': java}), patch.object(runtime.os, 'getuid', return_value=10123), patch.object(runtime.os, 'getgid', return_value=10123), patch.object(Path, 'lstat', lambda path: records[str(path)]), patch.object(Path, 'readlink', return_value=Path('/data/data')):
                    result = runtime._cache_directory(cache)
                self.assertEqual(str(result), cache.replace('/data/user/0', '/data/data') if alias else cache)

    @unittest.skipUnless(os.name == 'posix', 'Android is POSIX')
    def test_android_anchor_does_not_allow_foreign_writable_or_indirect_app_paths(self):
        for bad in ('foreign-package', 'public-package', 'symlink-files', 'writable-profiles', 'foreign-platform', 'unsafe-alias', 'wrong-application', 'wrong-context-path', 'untrusted-files-group'):
            with self.subTest(bad=bad):
                cache, records, java = self.android_cache_fixture(alias=bad == 'unsafe-alias')
                package = '/data/user/0/com.cleanyourtv.android'
                if bad == 'foreign-package': records[package].st_uid = 10124
                elif bad == 'public-package': records[package].st_mode |= 0o077
                elif bad == 'symlink-files': records[package+'/files'].st_mode = stat.S_IFLNK | 0o777
                elif bad == 'writable-profiles': records[package+'/files/profiles'].st_mode |= 0o022
                elif bad == 'foreign-platform': records['/data'].st_uid = 10124
                elif bad == 'untrusted-files-group': records[package+'/files'].st_gid = 10124
                elif bad == 'wrong-application': java.jclass('').getPlatform().getApplication().getPackageName = lambda: 'other.application'
                elif bad == 'wrong-context-path': java.jclass('').getPlatform().getApplication().getFilesDir = lambda: types.SimpleNamespace(getAbsolutePath=lambda: '/data/user/0/other.application/files')
                with patch.dict(os.sys.modules, {'java': java}), patch.object(runtime.os, 'getuid', return_value=10123), patch.object(runtime.os, 'getgid', return_value=10123), patch.object(Path, 'lstat', lambda path: records[str(path)]), patch.object(Path, 'readlink', return_value=Path('/data/foreign')):
                    with self.assertRaises(UserError): runtime._cache_directory(cache)

    @unittest.skipUnless(os.name == 'posix', 'Android is POSIX')
    def test_android_context_does_not_weaken_external_data_directory(self):
        cache, records, java = self.android_cache_fixture()
        with patch.dict(os.sys.modules, {'java': java}), patch.object(runtime.os, 'getuid', return_value=10123), patch.object(runtime.os, 'getgid', return_value=10123), patch.object(Path, 'lstat', lambda path: records[str(path)]):
            with self.assertRaises(UserError): runtime._cache_directory('/data/external/python-cache')

    def test_download_size_hash_and_final_url_fail_without_publishing_cache(self):
        raw = archive(GOOD)
        for body, url in [(raw+b'x', None), (raw[:-1], None), (b'x'*len(raw), None),
                          (raw, 'https://evil.invalid/archive')]:
            with self.subTest(size=len(body), url=url), self.pin_fixture(raw):
                response = Response(body)
                if url: response.geturl = lambda: url
                with patch.object(runtime.urllib.request, 'build_opener') as builder:
                    builder.return_value.open.return_value = response
                    with self.assertRaises(UserError): runtime.prime_cache(self.cache, self.messages.append)
                self.assertFalse((self.cache/(runtime.SHA256+'.tar.gz')).exists())

    def test_download_disables_proxies_and_validates_release_redirects(self):
        raw = archive(GOOD)
        with self.pin_fixture(raw), patch.object(runtime.urllib.request, 'build_opener') as builder:
            builder.return_value.open.return_value = Response(raw)
            path = runtime.prime_cache(self.cache, self.messages.append)
            self.assertEqual(path.read_bytes(), raw)
            handlers = builder.call_args.args
            self.assertTrue(any(isinstance(item, runtime.urllib.request.ProxyHandler) and item.proxies == {} for item in handlers))
        handler = runtime._ReleaseRedirect()
        request = runtime.urllib.request.Request(runtime.URL)
        for target in ['http://release-assets.githubusercontent.com/x', 'https://evil.invalid/x',
                       'https://github.com/other/release', 'https://u:p@release-assets.githubusercontent.com/x']:
            with self.subTest(target=target):
                with self.assertRaises(UserError): handler.redirect_request(request, None, 302, '', {}, target)
        redirected = runtime._ReleaseRedirect().redirect_request(request, None, 302, '', {}, 'https://release-assets.githubusercontent.com/release-asset/x?sig=private')
        self.assertEqual(redirected.host, 'release-assets.githubusercontent.com')

    def test_cache_works_without_posix_identity_flags_or_hardlinks(self):
        raw = archive(GOOD)
        with self.pin_fixture(raw), patch.object(runtime, '_HOST_POSIX', False), patch.object(runtime.os, 'getuid', side_effect=AssertionError('POSIX uid'), create=True), patch.object(runtime.os, 'link', side_effect=OSError('Android forbids links')), patch.object(runtime.urllib.request, 'build_opener') as builder:
            builder.return_value.open.return_value = Response(raw)
            path = runtime.prime_cache(str(self.cache), self.messages.append)
            self.assertEqual(path.read_bytes(), raw)
            with patch.object(runtime.urllib.request, 'build_opener', side_effect=AssertionError('network')):
                self.assertEqual(runtime.prime_cache(str(self.cache), self.messages.append), path)

    @unittest.skipUnless(os.name == 'posix', 'TV probe requires POSIX')
    def test_managed_smoke_does_not_write_bytecode(self):
        module = Path(self.temp.name)/'bytecode_probe.py'
        module.write_text('value = 1')
        script = 'import sys; sys.path.insert(0, '+repr(self.temp.name)+'); import bytecode_probe; print("CYTV_RUNTIME_SMOKE")'
        class LocalRemote:
            def run(self, command, data=None, timeout=30):
                result = subprocess.run(command, shell=True, input=data, capture_output=True, timeout=timeout)
                if result.returncode: raise TVCommandError(result.returncode)
                return result.stdout.decode()
        with patch.object(runtime, 'SMOKE', script):
            runtime._smoke(LocalRemote(), os.sys.executable)
        self.assertFalse((Path(self.temp.name)/'__pycache__').exists())

    def test_provisioning_uploads_only_normalized_verified_tar_and_returns_pinned_slot(self):
        raw = archive(GOOD)
        remote = Remote(False)
        with self.pin_fixture(raw), patch.object(runtime, 'prime_cache') as prime:
            path = Path(self.temp.name)/'fixture.tar.gz'; path.write_bytes(raw); prime.return_value = path
            executable = runtime.select_python(remote, self.cache, self.messages.append, True)
            self.assertEqual(executable, runtime.RUNTIME_ROOT+'/'+runtime.SHA256+'/bin/python3.13')
        self.assertEqual(len(remote.uploads), 1)
        with tarfile.open(fileobj=io.BytesIO(remote.uploads[0][1])) as payload:
            self.assertTrue(all(member.isfile() or member.isdir() for member in payload))
        self.assertTrue(self.messages)

    def test_production_normalization_uses_disk_and_streaming_transport(self):
        raw = archive(GOOD)
        target = Path(self.temp.name)/'normalized.tar.gz'
        with self.pin_fixture(raw):
            inventory = runtime.normalize_to_file(raw, target)
            with tarfile.open(target) as payload:
                self.assertEqual(json.load(payload.extractfile('.cytv-runtime.json')), inventory)
        class StreamingRemote(Remote):
            def upload(self, path, data, mode=0o600): raise AssertionError('whole-file upload')
            def upload_file(self, path, local_path, mode=0o600, timeout=600):
                with tarfile.open(local_path) as payload:
                    self.installed_data = payload.extractfile('lib/data').read()
        remote = StreamingRemote(False)
        with self.pin_fixture(raw), patch.object(runtime, 'prime_cache') as prime:
            path = Path(self.temp.name)/'fixture.tar.gz'; path.write_bytes(raw); prime.return_value = path
            self.assertTrue(runtime.select_python(remote, self.cache, self.messages.append, True).endswith('/bin/python3.13'))
        self.assertEqual(remote.installed_data, b'hello')

    def test_existing_partial_slot_is_never_overwritten(self):
        raw = archive(GOOD)
        class PartialRemote(Remote):
            def run(self, command, data=None, timeout=30):
                if 'CYTV_SLOT_EXISTS' in command: return 'CYTV_SLOT_EXISTS'
                if 'CYTV_RUNTIME_VERIFIED' in command: raise TVCommandError(1)
                return super().run(command, data, timeout)
        remote = PartialRemote(False)
        with self.pin_fixture(raw), patch.object(runtime, 'prime_cache') as prime:
            path = Path(self.temp.name)/'fixture.tar.gz'; path.write_bytes(raw); prime.return_value = path
            with self.assertRaises(UserError): runtime.select_python(remote, self.cache, self.messages.append, True)
        self.assertFalse(remote.uploads)
        self.assertFalse(any('CYTV_RUNTIME_PROMOTED' in command for command, data in remote.commands))

    @unittest.skipUnless(os.name == 'posix', 'TV bootstrap requires POSIX shell')
    def test_shell_verification_rejects_find_failure(self):
        class LocalRemote:
            def run(self, command, data=None, timeout=30):
                result = subprocess.run(command, shell=True, input=data, capture_output=True)
                if result.returncode: raise TVCommandError(result.returncode)
                return result.stdout.decode()
        shell = 'set -eu; ancestors() { :; }; find() { if [ \"$*\" = \". -type f\" ]; then printf \".cytv-runtime.json\\n\"; else return 1; fi; }; '
        inventory = {'schema': 1, 'archive_sha256': runtime.SHA256, 'files': {}}
        (Path(self.temp.name)/'.cytv-runtime.json').write_text(json.dumps(inventory, sort_keys=True, separators=(',', ':')))
        # Broken find must be a failure even if it emits no unsafe filenames.
        with patch.object(runtime, '_SHELL', shell):
            with self.assertRaises(UserError): runtime._verify(LocalRemote(), self.temp.name, inventory)

    def test_failed_smoke_never_promotes_or_activates_runtime(self):
        raw = archive(GOOD)
        remote = Remote(False, smoke=False)
        with self.pin_fixture(raw), patch.object(runtime, 'prime_cache') as prime:
            path = Path(self.temp.name)/'fixture.tar.gz'; path.write_bytes(raw); prime.return_value = path
            with self.assertRaises(UserError): runtime.select_python(remote, self.cache, self.messages.append, True)
        self.assertFalse(any('CYTV_RUNTIME_PROMOTED' in command for command, data in remote.commands))
        self.assertFalse(any('/usr/bin/python3' in path for path, data, mode in remote.uploads))




@unittest.skipUnless(os.sys.platform.startswith('linux') and hasattr(os, 'geteuid') and os.geteuid() == 0,
                     'Bootstrap execution requires an isolated Linux root test environment')
class ShellBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cytv-python-test-', dir='/var/lib')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.tree = self.base/'tree'
        self.tree.mkdir(mode=0o755)
        data, self.inventory = runtime._normalize(archive(GOOD))
        with tarfile.open(fileobj=io.BytesIO(data)) as payload:
            payload.extractall(self.tree, filter='data')

    class LocalRemote:
        def run(self, command, data=None, timeout=30):
            result = subprocess.run(command, shell=True, input=data, capture_output=True, timeout=timeout)
            if result.returncode: raise TVCommandError(result.returncode)
            return result.stdout.decode()

    def test_shell_verifies_real_tree_and_rejects_unsafe_inodes(self):
        remote = self.LocalRemote()
        runtime._verify(remote, str(self.tree), self.inventory)
        path = self.tree/'lib/data'
        original = path.read_bytes()
        changes = ('content', 'writable', 'symlink', 'hardlink', 'extra', 'foreign')
        for change in changes:
            with self.subTest(change=change):
                if change == 'content': path.write_bytes(b'corrupt')
                elif change == 'writable': path.chmod(0o666)
                elif change == 'symlink': path.unlink(); path.symlink_to(self.tree/'bin/python3.13')
                elif change == 'hardlink': os.link(path, self.base/'outside-link')
                elif change == 'extra': (self.tree/'extra').write_bytes(b'extra')
                elif change == 'foreign': os.chown(path, 1234, 1234)
                with self.assertRaises(UserError): runtime._verify(remote, str(self.tree), self.inventory)
                if change == 'hardlink': (self.base/'outside-link').unlink()
                if change == 'extra': (self.tree/'extra').unlink()
                if change == 'foreign': os.chown(path, 0, 0)
                path.unlink(); path.write_bytes(original); path.chmod(0o644)
        runtime._verify(remote, str(self.tree), self.inventory)

    def test_verified_promotion_is_atomic_and_never_replaces_existing_slot(self):
        slot = self.base/'slot'
        command = [os.sys.executable, '-I', '-B', '-c', runtime._PROMOTE, str(self.base), str(self.tree), str(slot)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'CYTV_RUNTIME_PROMOTED')
        self.assertFalse(self.tree.exists())
        self.assertEqual((slot/'lib/data').read_bytes(), b'hello')
        self.tree.mkdir(); (self.tree/'new').write_bytes(b'other')
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'CYTV_RUNTIME_EXISTS')
        self.assertTrue((self.tree/'new').exists())
        self.assertFalse((slot/'new').exists())


if __name__ == '__main__': unittest.main()

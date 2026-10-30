"""Edition-specific operations; SSH is the only device mutation boundary."""
import json
import hashlib
import re
from pathlib import Path, PurePosixPath
import shlex
import shutil
import tempfile
import time
import uuid

from . import package, i18n, diagnostics
from .errors import UserError, TVRejected, ExistingRoot, TVCommandError, root_recovery_details

HOME = 'com.gathin.tvhome'
HELPER = 'com.local.nativehome'
BASE = '/media/developer/apps/usr/palm'
HELPER_STATE = BASE + '/applications/' + HELPER + '/state'
ROOT_STATE = '/var/lib/clean-your-tv-root'
UPDATER_STATE = '/var/lib/clean-your-tv-root-updater'
UPDATER_APP = 'com.cleanyourtv.root.updater'
SYSTEM_UPDATER_APP = 'com.cleanyourtv.system.updater'
SYSTEM_UPDATER_STATE = '/var/lib/clean-your-tv-system-updater'

# Trusted host code: the target copy cannot bootstrap verification of itself.
# Keep this pre-execution validator aligned with root-edition/python_boot.js.
_RETAINED_PYTHON_CHECK = r'''
function pythonCommand(state){
 var fs=require('fs'),path=require('path'),crypto=require('crypto'),launcher=state+'/python-launcher',receipt=state+'/python-runtime.json';
 function present(name){try{fs.lstatSync(name);return true;}catch(e){if(e.code==='ENOENT')return false;throw e;}}
 function owned(name,file){
  var item=fs.lstatSync(name);
  if(item.uid!==0||(item.mode&18)||item.isSymbolicLink()||(file?(!item.isFile()||item.nlink!==1):!item.isDirectory()))throw Error('unsafe-python-binding');
  for(var parent=path.dirname(name);;parent=path.dirname(parent)){
   item=fs.lstatSync(parent);if(!item.isDirectory()||item.isSymbolicLink()||item.uid!==0||(item.mode&18))throw Error('unsafe-python-binding');
   if(parent===path.dirname(parent))break;
  }
  return fs.lstatSync(name);
 }
 if(!present(launcher)&&!present(receipt))return '/usr/bin/python3';
 var pin='4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea',executable='/var/lib/clean-your-tv-python/'+pin+'/bin/python3.13';
 if((owned(launcher,true).mode&511)!==448||owned(receipt,true).size>65536)throw Error('unsafe-python-binding');
 var binding=JSON.parse(fs.readFileSync(receipt,'utf8'));
 if(Object.keys(binding).sort().join(',')!=='archive_sha256,executable,inventory_sha256,schema'||binding.schema!==1||binding.executable!==executable||binding.archive_sha256!==pin||!/^[a-f0-9]{64}$/.test(binding.inventory_sha256))throw Error('invalid-python-binding');
 if(fs.readFileSync(launcher,'utf8')!=='#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+executable+' "$@"\n')throw Error('invalid-python-launcher');
 var inventoryPath=path.dirname(path.dirname(executable))+'/.cytv-runtime.json';
 if(owned(inventoryPath,true).size>4*1024*1024||owned(executable,true).size>256*1024*1024)throw Error('oversized-python-runtime');
 var raw=fs.readFileSync(inventoryPath),inventory=JSON.parse(raw);
 if(crypto.createHash('sha256').update(raw).digest('hex')!==binding.inventory_sha256||inventory.schema!==1||inventory.archive_sha256!==pin||!inventory.files||crypto.createHash('sha256').update(fs.readFileSync(executable)).digest('hex')!==inventory.files['bin/python3.13'])throw Error('changed-python-runtime');
 return launcher;
}

try { pythonCommand(process.argv[1]); } catch (_) { process.exit(1); }
'''


def root_updater_paths():
    return [UPDATER_STATE, '/var/lib/webosbrew/init.d/51-clean-your-tv-root-updater',
             *[BASE + '/' + kind + '/' + UPDATER_APP + suffix
               for kind, suffix in (('applications', ''), ('packages', ''), ('services', '.service'))],
             *['/var/luna-service2-dev/' + kind + '/' + UPDATER_APP + '.service' + suffix
               for kind, suffix in (('services.d', '.service'), ('roles.d', '.service.json'),
                                ('client-permissions.d', '.service.json'), ('api-permissions.d', '.api.json'))]]


class Installer:
    def __init__(self, remote, store, profile, payload, manifest, progress=print, tv_info=None, checks=None):
        self.remote, self.store, self.profile = remote, store, profile
        self.payload, self.manifest, self.progress = Path(payload), manifest, progress
        self.helper_retry = lambda: False
        self.tv_info = tv_info if tv_info is not None else {}
        from .checks import CheckList
        self.checks = checks if checks is not None else CheckList()

    @staticmethod
    def _python_command(args):
        if args[0].startswith('/var/lib/clean-your-tv-python/'):
            args = ['env', '-u', 'PYTHONHOME', '-u', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE=1', 'PYTHONNOUSERSITE=1', *args]
        return shlex.join(args)

    def _select_python(self, provision=False):
        from .python_runtime import select_python
        from .state import default_dir
        cache = (self.store.root if self.store is not None else default_dir()) / 'python-cache'
        return select_python(self.remote, cache, self.progress, provision=provision)

    def _python(self, state=None):
        if getattr(self, '_selected_python', None):
            return self._selected_python
        managed = '/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'
        states = list(dict.fromkeys([state or ROOT_STATE, ROOT_STATE, UPDATER_STATE, SYSTEM_UPDATER_STATE]))
        if self.store is not None:
            pending = self.store.pending(self.profile) or {}
            for key, base in (('archive', ROOT_STATE), ('updater_archive', UPDATER_STATE), ('system_updater_archive', SYSTEM_UPDATER_STATE)):
                archived = pending.get(key)
                if isinstance(archived, str) and re.fullmatch(re.escape(base)+r'\.archive-[0-9a-f]{32}', archived):
                    states.append(archived)
        for location in states:
            # Check ownership and literal bytes before executing any retained launcher.
            # The selected literal remains usable after its state is archived by removal.
            helper = location + ('/python_binding.py' if location == ROOT_STATE or location.startswith(ROOT_STATE+'.archive-') else '/code/python_binding.py')
            script = r'''cytv_state=STATE
cytv_launcher="$cytv_state/python-launcher"
cytv_receipt="$cytv_state/python-runtime.json"
if [ ! -e "$cytv_launcher" ] && [ ! -L "$cytv_launcher" ] && [ ! -e "$cytv_receipt" ] && [ ! -L "$cytv_receipt" ]; then exit 0; fi
cytv_owned() {
    cytv_path="$1"
    while :; do
        [ ! -L "$cytv_path" ] && [ "$(stat -c %u "$cytv_path")" = 0 ] || return 1
        cytv_mode=$(stat -c %a "$cytv_path") || return 1
        [ "$((0$cytv_mode & 022))" -eq 0 ] || return 1
        [ "$cytv_path" != / ] || break
        cytv_path=$(dirname "$cytv_path")
    done
}
if ! cytv_owned "$cytv_launcher" || ! cytv_owned "$cytv_receipt" || ! cytv_owned MANAGED ||
   [ ! -f "$cytv_launcher" ] || [ ! -f "$cytv_receipt" ] || [ "$(stat -c %a "$cytv_launcher")" != 700 ] ||
   [ "$(stat -c %h "$cytv_launcher")" != 1 ] || [ "$(stat -c %h "$cytv_receipt")" != 1 ] ||
   ! printf '%s\n' '#!/bin/sh' 'unset PYTHONHOME PYTHONPATH' 'export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1' 'exec MANAGED "$@"' | cmp -s - "$cytv_launcher"; then printf CYTV_PYTHON_INVALID; exit 0; fi
if ! cytv_owned HELPER || [ ! -f HELPER ] || [ "$(stat -c %h HELPER)" != 1 ]; then printf CYTV_PYTHON_INVALID; exit 0; fi
unset NODE_OPTIONS NODE_PATH
if ! /usr/bin/node -e NODE_CHECK "$cytv_state" >/dev/null 2>&1; then printf CYTV_PYTHON_INVALID; exit 0; fi
if ! env -u PYTHONHOME -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 MANAGED -c 'import runpy,sys; runpy.run_path(sys.argv[1])["verify_binding"](sys.argv[2]); print("CYTV_PYTHON_BOUND")' HELPER "$cytv_state"; then printf CYTV_PYTHON_INVALID; fi
'''.replace('STATE', shlex.quote(location)).replace('MANAGED', managed).replace('HELPER', shlex.quote(helper)).replace('NODE_CHECK', shlex.quote(_RETAINED_PYTHON_CHECK))
            reply = self.remote.run(script).strip()
            if reply == 'CYTV_PYTHON_BOUND':
                self._selected_python = managed
                return managed
            if reply:
                raise UserError('Retained Python binding could not be verified. Keep recovery state and run cytv status.')
        self._selected_python = '/usr/bin/python3'
        return self._selected_python

    def recover_system_rollback(self, new_attempt=False):
        if self.profile['edition'] != 'root' or not self.remote.root:
            raise UserError('Rollback readiness recovery requires an existing Root connection.')
        if self.store.pending(self.profile):
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        from .system_rollback_recovery import program
        try:
            reply = json.loads(self.remote.run(
                self._python_command([self._python(SYSTEM_UPDATER_STATE), '-I', '-B', '-']),
                data=(program(new_attempt=True) if new_attempt else program()).encode(), timeout=200))
            result = reply.get('result') if isinstance(reply, dict) else None
            if reply.get('returnValue') is not True or not isinstance(result, dict) or result.get('phase') != 'rolled-back' or result.get('homeResumePhase') != 'rolled-back':
                raise ValueError('Rollback readiness is not complete')
            return result
        except Exception:
            raise UserError('Rollback readiness recovery was not confirmed. Keep recovery state and retry the same command.') from None

    def replace_system_updater(self):
        if self.profile['edition']!='root' or not self.remote.root:
            raise UserError('System Updater replacement requires an existing Root connection.')
        pending=self.store.pending(self.profile)
        if pending:
            raise UserError('Previous operation is unresolved. Run cytv status; retain recovery state before retrying.')
        from .system_updater_replace import program
        try:
            source=program(self.payload.resolve()/'system-updater')
            python=self._python(ROOT_STATE)
            reply=json.loads(self.remote.run(self._python_command([python,'-I','-B','-']),data=source.encode(),timeout=600))
            if not isinstance(reply,dict) or reply.get('installed') is not True or reply.get('version')!='1.1.2' or not all(reply.get(k) is True for k in ('root_unchanged','home_unchanged','profile_storage_untouched')):
                raise ValueError('Unconfirmed System replacement')
            return reply
        except Exception:
            raise UserError('System updater setup was not confirmed. Keep recovery state and run cytv status.') from None

    def configure_firmware_access(self, enabled=True, repair=False):
        if self.profile['edition']!='root' or not self.remote.root:
            raise UserError('Homebrew API access requires an existing Root installation.')
        if self.store.pending(self.profile):
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        from .firmware_access import program
        try:
            source=program(self.payload/'root',enabled,repair=True) if repair else program(self.payload/'root',enabled)
            reply=json.loads(self.remote.run(self._python_command([self._python(ROOT_STATE),'-I','-']),data=source.encode(),timeout=60))
            if not isinstance(reply,dict) or reply.get('returnValue') is not True or reply.get('permissions_installed') is not enabled:raise ValueError('Unconfirmed firmware permission action')
            return reply
        except Exception:
            raise UserError('Homebrew API access repair was not confirmed. Keep recovery state and retry the same command.') from None

    def enable_system_updates(self):
        """Provision the independent supervisor without replacing the active edition."""
        if self.store.pending(self.profile):
            raise UserError('Previous operation is unresolved. Run cytv status; retain recovery state before retrying.')
        # Canonicalize the packaged root (macOS /var and PyInstaller app aliases),
        # while keeping links inside the bundle subject to the integrity check.
        bundle = self.payload.resolve() / 'system-updater'
        try:
            metadata = json.loads((bundle / 'bundle.json').read_text())
            files = metadata['files']
            if (metadata.get('schema') != 1 or metadata.get('supervisor') != 1
                    or not isinstance(files, dict)
                    or not {'setup-system-updater.py', 'system-updater.ipk'} <= files.keys()):
                raise ValueError('Invalid bootstrap inventory')
            for name, digest in files.items():
                path = bundle / package.safe_name(name)
                if (any(p.is_symlink() for p in (path, *path.parents))
                        or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
                    raise ValueError('Bootstrap integrity mismatch')
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise UserError('System updater bundle integrity could not be verified. Use a complete installer build.') from error
        probe = ('if test "$(id -u)" = 0 && test -x /usr/bin/luna-send && '
                 '/usr/bin/node -e \'process.exit(Number(process.versions.node.split(".")[0]) >= 8 ? 0 : 1)\'; '
                 'then printf CYTV_SYSTEM_ROOT_READY; fi')
        if self.remote.run(probe).strip() != 'CYTV_SYSTEM_ROOT_READY':
            raise UserError('On-TV system updates require root SSH access and Node.js 8+. Unrooted TVs use the computer installer.')
        python = self._python(SYSTEM_UPDATER_STATE)
        from .python_runtime import SYSTEM_PROBE
        check = self._python_command([python, '-I', '-B', '-c', SYSTEM_PROBE])
        if self.remote.run('if ' + check + ' >/dev/null 2>&1; then printf CYTV_PYTHON_READY; fi').strip() != 'CYTV_PYTHON_READY':
            self._selected_python = self._select_python(provision=True)
        self.store.begin(self.profile, 'enable-system-updates', stage='upload')
        stage = '/tmp/cytv-system-updater-' + uuid.uuid4().hex
        self.remote.run('umask 077; mkdir ' + stage)
        for directory in sorted({str(PurePosixPath(name).parent) for name in files} - {'.'}):
            self.remote.run('mkdir -p ' + shlex.quote(stage + '/' + directory))
        for name in [*files, 'bundle.json']:
            self.remote.upload(stage + '/' + package.safe_name(name), (bundle / name).read_bytes(), mode=0o600)
        self.store.checkpoint(self.profile, stage='setup')
        self.progress('Preparing updates for every TV component…')
        reply = json.loads(self.remote.run(self._python_command([
            self._python(), stage + '/setup-system-updater.py', '--bundle', stage,
            '--edition', self.profile['edition'], '--device', '--apply']), timeout=360))
        if not isinstance(reply, dict) or reply.get('installed') is not True:
            raise UserError('System updater setup was not confirmed. Keep recovery state and run cytv status.')
        self.store.finish(self.profile)
        return reply

    def coordinator_code(self):
        """Stage trusted host code for read-only handoff/status, never retained code."""
        existing=getattr(self,'_coordinator_code',None)
        if existing: return existing
        bundle=self.payload/'root-updater'
        manifest=json.loads((bundle/'bundle.json').read_text())
        files=manifest.get('files')
        if not isinstance(files,dict) or 'install_driver.py' not in files:
            raise UserError('Root Updater bundle is missing or invalid. Use a complete installer build.')
        for name,digest in files.items():
            path=bundle/package.safe_name(name)
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise UserError('Root Updater bundle is missing or invalid. Use a complete installer build.')
        stage='/tmp/cytv-coordinator-'+uuid.uuid4().hex
        self.remote.run('umask 077; mkdir '+stage)
        for name in files:
            if name.endswith('.ipk'): continue
            target=stage+'/'+package.safe_name(name)
            self.remote.run('mkdir -p '+shlex.quote(str(PurePosixPath(target).parent)))
            self.remote.upload(target,(bundle/name).read_bytes(),mode=0o600)
        self._coordinator_code=stage
        return stage

    def product_action(self, action, operation=None, payload=None, migrate=False, verify_current=False):
        if action not in ('inspect','install','status','remove'): raise ValueError('Unsupported product action')
        if action!='inspect' and (not isinstance(operation,str) or not re.fullmatch('[a-f0-9]{32}',operation)):
            raise ValueError('Invalid product operation')
        driver=(payload+'/root-updater' if payload else self.coordinator_code())+'/install_driver.py'
        args=[self._python(),driver,action]
        if operation: args+=['--operation',operation]
        if payload:
            args+=['--payload',payload]
            candidate=getattr(self,'_product_candidates',{}).get(payload)
            if candidate: args+=['--candidate',candidate]
        if migrate: args.append('--migrate-packaged-home')
        if verify_current:args.append('--verify-current')
        reply=json.loads(self.remote.run(self._python_command(args),timeout=90))
        if (not isinstance(reply,dict) or reply.get('operation')!=operation
                or reply.get('state') not in ('pending','complete','recovery_required','unknown','fresh','installed','unsupported','conflict','migration_required')):
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.')
        return reply

    def await_product(self, action, operation, payload, migrate=False):
        reply=self.product_action(action,operation,payload,migrate=migrate)
        deadline=time.monotonic()+1080
        while reply['state']=='pending' and time.monotonic()<deadline:
            time.sleep(1)
            reply=self.product_action('status',operation)
        if reply['state']!='complete':
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        return reply['result']

    def upload_product(self, root_bundle):
        bundles=(('root',root_bundle),('root-updater',self.payload/'root-updater'))
        manifests={};candidate={}
        for component,bundle in bundles:
            raw=(bundle/'bundle.json').read_bytes();manifest=json.loads(raw)
            for name,digest in manifest['files'].items():
                path=bundle/package.safe_name(name)
                if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                    raise UserError('Root Updater bundle is missing or invalid. Use a complete installer build.')
            manifests[component]=manifest
            candidate[component]=hashlib.sha256(raw).hexdigest()
        digest=hashlib.sha256(json.dumps(candidate,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        stage='/tmp/cytv-product-'+uuid.uuid4().hex
        self.remote.run('umask 077; mkdir '+stage)
        for component,bundle in bundles:
            for name in (*manifests[component]['files'],'bundle.json'):
                target=stage+'/'+component+'/'+package.safe_name(name)
                self.remote.run('mkdir -p '+shlex.quote(str(PurePosixPath(target).parent)))
                self.remote.upload(target,(bundle/name).read_bytes(),mode=0o600)
        if not hasattr(self,'_product_candidates'):self._product_candidates={}
        self._product_candidates[stage]=digest
        return stage

    def root_installation(self):
        """Shared descriptor/profile inspection is independent of installer origin."""
        return self.product_action('inspect')['installation']

    def root_action(self, action, bundle=None, migrate=False):
        driver = (bundle or ROOT_STATE) + '/deploy.py'
        args = [self._python(ROOT_STATE), driver, action]
        if bundle:
            args += ['--bundle', bundle]
        if migrate:
            args.append('--migrate-packaged-home')
        attempt = uuid.uuid4().hex if action == 'install' else None
        command = self._python_command(args)
        if attempt: command = 'env CYTV_ROOT_INSTALL_ATTEMPT='+attempt+' '+command
        try:
            raw = self.remote.run(command, timeout=1080 if action == 'uninstall' else 720 if action == 'restore' else 180)
        except TVCommandError as error:
            if action == 'install':
                # Read data only; never rerun the retained driver or installation.
                code = """import os,stat,json
p='/var/lib/clean-your-tv-root/recovery-failure.json'
f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
with os.fdopen(f,'rb') as stream:
 s=os.fstat(stream.fileno())
 if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_nlink!=1 or s.st_mode & 0o077 or s.st_size>4096: raise ValueError('Unsafe recovery diagnostic')
 print(json.dumps(json.loads(stream.read(4097))))
"""
                try:
                    value = json.loads(self.remote.run(self._python_command([args[0], '-c', code]), timeout=15))
                    if isinstance(value, dict) and value.get('attempt') == attempt:
                        error.root_recovery = root_recovery_details(value)
                except Exception:
                    pass  # Preserve the original failure, even when diagnostics are unavailable.
            raise
        reply = json.loads(raw)
        if not isinstance(reply, dict) or reply.get('returnValue') is not True:
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.')
        return reply

    def preflight(self, install=False):
        if self.profile['edition'] == 'root':
            from .python_runtime import SYSTEM_PROBE
            probes = ('test "$(id -u)" = 0', 'test -x /usr/bin/python3',
                      'test -x /usr/bin/luna-send', 'test -d /media/developer/apps',
                      'test -d /var/luna-service2-dev',
                      '/usr/bin/python3 -c "import json"', '/usr/bin/python3 -c "import fcntl"',
                      self._python_command(['/usr/bin/python3', '-I', '-B', '-c', SYSTEM_PROBE]),
                      '/usr/bin/node -e \'process.exit(Number(process.versions.node.split(".")[0]) >= 8 ? 0 : 1)\'')
            checks = dict.fromkeys(diagnostics.ROOT_REQUIREMENTS, 'unknown')
            self.tv_info['root_requirements'] = checks
            python = self._python()
            def check(name, probe):
                # Keep independent import diagnostics when an earlier import failed;
                # otherwise exercise every module/process/filesystem feature used on TV.
                if name == 'python-version' and any(checks[n] != 'pass' for n in ('python-json', 'python-fcntl')):
                    probe = '/usr/bin/python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)"'
                probe = probe.replace('test -x /usr/bin/python3', 'test -x '+shlex.quote(python))
                command = ('if ( ' + probe.replace('/usr/bin/python3', ('env -u PYTHONHOME -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 ' if python.startswith('/var/lib/clean-your-tv-python/') else '') + shlex.quote(python)) + ' ) >/dev/null 2>&1; then printf CYTV_ROOT_READY; '
                           'else printf CYTV_ROOT_MISSING; fi')
                def run():
                    reply = self.remote.run(command).strip()
                    return {'CYTV_ROOT_READY': True, 'CYTV_ROOT_MISSING': False}.get(reply)
                result = self.checks.probe(name, run)
                checks[name] = {True: 'pass', False: 'fail'}.get(result, 'unknown')
            for name, probe in zip(diagnostics.ROOT_REQUIREMENTS, probes):
                check(name, probe)
            python_names = {'python3', 'python-json', 'python-fcntl', 'python-version'}
            if (install and any(checks[name] != 'pass' for name in python_names)
                    and all(result == 'pass' for name, result in checks.items() if name not in python_names)):
                self.checks.update('python3', 'running')
                python = self._selected_python = self._select_python(provision=True)
                for name, probe in zip(diagnostics.ROOT_REQUIREMENTS, probes):
                    if name in python_names:
                        check(name, probe)
            failed = [name for name, result in checks.items() if result != 'pass']
            if failed:
                raise UserError('Root requirements failed or could not be verified: {requirements}. Check the diagnostic report.'.format(
                    requirements=', '.join(failed)))
            if install:
                paths = [ROOT_STATE, BASE + '/applications/' + package.ROOT_APP,
                         BASE + '/services/' + package.ROOT_APP + '.service', BASE + '/packages/' + package.ROOT_APP]
                condition = ' || '.join('[ -e ' + p + ' ] || [ -L ' + p + ' ]' for p in paths)
                existing=self.remote.run('if ' + condition + '; then printf CYTV_EXISTING_ROOT; fi').strip()
                maintain=False
                if existing:
                    try: maintain=self.root_installation().get('can_maintain') is True
                    except (OSError,ValueError,RuntimeError): pass
                if existing and not maintain:
                    raise ExistingRoot('Root is already installed or recovery state remains. Connect interactively to review reinstallation; existing state was left unchanged.')
        else:
            self.checks.update('architecture', 'running')
            arch = self.remote.run('uname -m').strip()
            self.tv_info.update(kernel_arch=arch if arch in diagnostics.KERNEL_ARCHES else 'unknown',
                                userland_abi='unknown', arm32_supported=False)
            # uname describes the kernel, which may be aarch64 while the
            # running TV shell (and supported native apps) still uses ARM32.
            words = self.remote.run('LC_ALL=C od -An -v -t u1 -N 20 /bin/sh').split()
            try:
                header = bytes(int(word) for word in words) if len(words) == 20 else b''
            except ValueError:
                header = b''
            abi = 'unknown'
            if len(header) == 20 and header[:4] == b'\x7fELF' and header[5:7] == b'\x01\x01' and header[4] in (1, 2):
                machine = int.from_bytes(header[18:20], 'little')
                abi = {(1, 40): 'arm32', (2, 183): 'arm64'}.get((header[4], machine), 'other')
            supported = abi == 'arm32' and arch in ('armv7l', 'armv7', 'armv8l', 'aarch64', 'arm64')
            self.tv_info.update(userland_abi=abi, arm32_supported=supported)
            self.checks.update('architecture', 'pass' if supported else 'fail',
                               '' if supported else 'The bundled Home Helper requires ARM32. A compatible TV runtime could not be confirmed.')
            if not supported:
                raise UserError('The bundled Home Helper requires ARM32. A compatible TV runtime could not be confirmed.')
            if install:
                self.checks.update('helper-node', 'running')
                node = self.remote.run('if /usr/bin/node -e \'var v=process.versions.node.split(".").map(Number);process.exit(v[0]>0||v[1]>12||(v[1]===12&&v[2]>=2)?0:1)\'; then printf CYTV_NODE_READY; fi')
                self.checks.update('helper-node', 'pass' if node.strip() == 'CYTV_NODE_READY' else 'fail',
                                   '' if node.strip() == 'CYTV_NODE_READY' else 'Home Helper requires TV Node.js 0.12.2 or newer. Installation has not started.')
                if node.strip() != 'CYTV_NODE_READY':
                    raise UserError('Home Helper requires TV Node.js 0.12.2 or newer. Installation has not started.')
            self.checks.update('root-conflict', 'running')
            root_state = self.remote.run(
                'if [ -e /var/webos-profile/override/clean-your-tv-root.json ] || '
                '[ -L /var/webos-profile/override/clean-your-tv-root.json ]; then printf CYTV_ROOT_STATE; fi')
            self.checks.update('root-conflict', 'fail' if root_state.strip() else 'pass',
                               'Root Home routing is present. Restore it with cytv --edition root restore first.' if root_state.strip() else '')
            if root_state.strip():
                raise UserError('Root Home routing is present. Restore it with cytv --edition root restore first.')
            if not install:
                return
            self.checks.update('helper-idle', 'running')
            helper = self.helper_state()
            self.checks.update('helper-idle', 'unknown' if helper == 'uncertain' else 'fail' if helper == 'running' else 'pass')
            if helper == 'running':
                raise UserError('Home Helper is running. Installation has not started; installed versions are unchanged. Press Home three times within two seconds (older Helper: hold Home for two seconds) to stop it, then rerun installation.')
            if helper == 'uncertain':
                raise UserError('Home Helper state could not be verified. Installation has not started; installed versions are unchanged. Run Check TV status and save a diagnostic report before retrying. Do not delete Helper state files.')
            if helper == 'stale':
                self.progress('A stale Helper PID file was found; no Helper process is running. Continuing installation without deleting state files.')

    def helper_state(self):
        # Read only: a stale PID is harmless once no controller/worker is found.
        # A symlink, unreadable process or failed probe must never permit replacement.
        script = r'''
cytv_state=CYTV_HELPER_IDLE
if [ ! -d /proc/ ] || [ ! -r /proc/ ] || [ ! -x /proc/ ]; then printf CYTV_HELPER_UNCERTAIN; exit 0; fi
for cytv_tool in cat tr grep; do command -v "$cytv_tool" >/dev/null 2>&1 || { printf CYTV_HELPER_UNCERTAIN; exit 0; }; done
if [ -L "HELPER_STATE/controller.pid" ]; then printf CYTV_HELPER_UNCERTAIN; exit 0; fi
if [ -e "HELPER_STATE/controller.pid" ]; then
    cytv_pid=$(cat "HELPER_STATE/controller.pid" 2>/dev/null) || { printf CYTV_HELPER_UNCERTAIN; exit 0; }
    case "$cytv_pid" in ''|0*|*[!0-9]*) printf CYTV_HELPER_UNCERTAIN; exit 0;; esac
    if [ -d "/proc/$cytv_pid" ] && [ ! -r "/proc/$cytv_pid/cmdline" ]; then
        printf CYTV_HELPER_UNCERTAIN; exit 0
    fi
    cytv_state=CYTV_HELPER_STALE
fi
for cytv_file in /proc/[0-9]*/cmdline; do
    [ -e "$cytv_file" ] || continue
    if [ ! -r "$cytv_file" ]; then cytv_state=CYTV_HELPER_UNCERTAIN; continue; fi
    cytv_args=$(tr '\000' '\n' < "$cytv_file" 2>/dev/null) || { cytv_state=CYTV_HELPER_UNCERTAIN; continue; }
    if [ "$cytv_file" = "/proc/${cytv_pid:-}/cmdline" ] && [ -z "$cytv_args" ]; then cytv_state=CYTV_HELPER_UNCERTAIN; fi
    if printf '%s\n' "$cytv_args" | grep -Fx -e 'com.local.nativehome' -e 'HELPER_ROOT/native.js' -e 'HELPER_ROOT/relay' >/dev/null 2>&1; then
        printf CYTV_HELPER_ACTIVE; exit 0
    else
        cytv_match=$?
        if [ "$cytv_match" != 1 ]; then cytv_state=CYTV_HELPER_UNCERTAIN; fi
    fi
done
printf '%s' "$cytv_state"
'''.replace('HELPER_STATE', HELPER_STATE).replace('HELPER_ROOT', BASE + '/applications/' + HELPER)
        result = self.remote.run(script).strip()
        return {'CYTV_HELPER_IDLE': 'stopped', 'CYTV_HELPER_STALE': 'stale',
                'CYTV_HELPER_ACTIVE': 'running'}.get(result, 'uncertain')

    def install(self, inventory, ssap_key=None, migrate=False, reinstall=None):
        # All local validation precedes the durable mutation receipt.
        if self.store.pending(self.profile):
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.')
        if reinstall and migrate:
            raise UserError('Reinstallation does not support --migrate-home. Omit it to read a fresh TV inventory before replacing Root.')
        if not migrate:
            package.inventory_script(inventory)
        if reinstall not in (None, 'installed', 'removed') or (reinstall and self.profile['edition'] != 'root'):
            raise UserError('Invalid reinstallation request.')
        self.preflight(install=not reinstall)
        if self.profile['edition'] == 'root':
            return self.install_root(inventory, migrate, reinstall)
        if not ssap_key:
            raise ValueError('Remote-control pairing is required for No-root.')
        launcher, _ = package.personalize((self.payload / self.manifest['launcher']).read_bytes(), HOME, inventory)
        helper = (self.payload / self.manifest['helper']).read_bytes()
        expected = {}
        for data in (helper, launcher):
            for name, content in package.data_files(data).items():
                if '/state/' not in name:
                    expected['/media/developer/apps/' + name] = hashlib.sha256(content).hexdigest()
        key_data = json.dumps({'key': ssap_key}).encode()
        ids = [app['id'] for app in inventory['apps'] if app['id'] not in (HOME, HELPER, 'com.webos.app.home', package.ROOT_APP)]
        apps_data = json.dumps(ids).encode()
        expected[HELPER_STATE + '/ssap-key.json'] = hashlib.sha256(key_data).hexdigest()
        expected[HELPER_STATE + '/apps.json'] = hashlib.sha256(apps_data).hexdigest()
        self.store.begin(self.profile, 'install', expected=expected,
                         versions={HOME: self.manifest['home_version'], HELPER: self.manifest['helper_version']})
        stage = '/media/developer/temp/cytv-' + uuid.uuid4().hex
        # appinstalld may run as another UID. Allow traversal/read, never foreign writes.
        self.remote.run('umask 022; mkdir -p /media/developer/temp && '
                        'case "$(LC_ALL=C ls -ld /media/developer/temp | cut -c10)" in '
                        'x|t) ;; *) chmod o+x /media/developer/temp || exit 1;; esac && '
                        'mkdir -m 755 ' + stage)
        for app, data, name in ((HELPER, helper, 'helper.ipk'), (HOME, launcher, 'launcher.ipk')):
            self.progress('Installing ' + ('Home Helper' if app == HELPER else 'Home') + '…')
            path = stage + '/' + name
            self.remote.upload(path, data, mode=0o644)
            self.remote.luna('com.webos.appInstallService/dev/install', {'id': app, 'ipkUrl': path, 'subscribe': True}, terminal='installed', timeout=150)
        self.verify_installed()
        self.progress('Configuring Home Helper…')
        self.remote.upload(HELPER_STATE + '/ssap-key.json', key_data, mode=0o640)
        self.remote.upload(HELPER_STATE + '/apps.json', apps_data, mode=0o644)
        self.save_eim('unknown')  # Persist uncertainty before submitting registration.
        try:
            self.remote.luna('com.webos.service.eim/addDevice', {'appId': HOME, 'pigImage': '', 'mvpdIcon': ''})
            self.save_eim(True)
        except TVRejected:
            self.save_eim(self.read_eim())
            self.progress('Warning: early input restoration is unavailable; startup will use the guarded fallback.')
        except RuntimeError:
            self.store.checkpoint(self.profile, eim_registered='unknown')
            self.progress('Warning: early input restoration was not confirmed; startup will use the guarded fallback.')
        self.remote.luna('com.webos.applicationManager/launch', {'id': HELPER, 'params': {'nativeHomeStart': True}})
        from .state import private_write
        private_write(self.store.device_dir(self.profile) / 'installation.json',
                      json.dumps({'eim_registered': self.store.pending(self.profile).get('eim_registered', 'unknown')}).encode())
        self.store.finish(self.profile)
        self.remote.run('rm -f ' + stage + '/helper.ipk ' + stage + '/launcher.ipk; rmdir ' + stage)
        return {'installed': 'no-root', 'launch_requested': True, 'hardware_verified': False}

    def install_root(self, inventory, migrate, reinstall=None):
        updater = self.payload / 'root-updater'
        try:
            updater_manifest = json.loads((updater / 'bundle.json').read_text())
            names = updater_manifest['files']
            if updater_manifest.get('schema') != 1 or not isinstance(names, dict) or not {'setup-updater.py', 'root-updater.ipk'} <= names.keys():
                raise ValueError('Invalid Root Updater bundle')
            for name, digest in names.items():
                path = updater / package.safe_name(name)
                if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError('Root Updater bundle integrity mismatch')
        except (OSError, KeyError, TypeError, ValueError) as error:
            raise UserError('Root Updater bundle is missing or invalid. Use a complete installer build.') from error
        if reinstall:
            condition=' || '.join('[ -e '+p+' ] || [ -L '+p+' ]' for p in root_updater_paths())
            if self.remote.run('if '+condition+'; then printf CYTV_EXISTING_UPDATER; fi').strip():
                raise UserError('Root Updater already exists or setup state remains. Use Software updates on the TV; if unavailable, inspect recovery before reinstalling.')
        with tempfile.TemporaryDirectory(prefix='cytv-root-') as tmp:
            bundle = Path(tmp).resolve() / 'root'
            shutil.copytree(self.payload / 'root', bundle)
            if not migrate:
                package.personalize_root(bundle, inventory)
            manifest = json.loads((bundle / 'bundle.json').read_text())
            for name, digest in manifest['files'].items():
                if hashlib.sha256((bundle / package.safe_name(name)).read_bytes()).hexdigest() != digest:
                    raise ValueError('Prepared Root bundle integrity mismatch')
            package.verify_root_rollback_format((bundle / package.safe_name(manifest['package'])).read_bytes())
            release_sha = hashlib.sha256((bundle / 'release.json').read_bytes()).hexdigest()
            bundle_sha = hashlib.sha256((bundle / 'bundle.json').read_bytes()).hexdigest()
            if reinstall:
                self.prepare_root_reinstall(already_removed=reinstall == 'removed')
                self.preflight(install=True)
            operation=uuid.uuid4().hex
            self.store.begin(self.profile,'install',release_sha=release_sha,bundle_sha=bundle_sha,migrate=migrate,
                             requires_updater=True,product_operation=operation,stage='coordinator-upload')
            self.progress('Uploading Root and recovery runtime…')
            stage=self.upload_product(bundle)
            self.store.checkpoint(self.profile,stage='coordinator-submitted',product_payload=stage)
            result=self.await_product('install',operation,stage,migrate=migrate)
            if result.get('installed')!=package.ROOT_APP or result.get('home_changed') is not False:
                raise UserError('Root installation readback is unexpected. Keep recovery state and run cytv status.')
            if self.root_action('status').get('result',{}).get('recovery',{}).get('integrity_verified') is not True:
                raise UserError('Root is installed, but recovery could not be verified. Run cytv status; activation has not started.')
            baseline_sha=result.get('baseline_sha')
            if not isinstance(baseline_sha,str) or not re.fullmatch('[a-f0-9]{64}',baseline_sha):
                raise UserError('Root updater recovery verification failed. Keep recovery state and run cytv status.')
            self.store.checkpoint(self.profile,stage='verify',baseline_sha=baseline_sha)
            self.verify_root_updater(baseline_sha)
            self.store.checkpoint(self.profile, action='activate-root', stage='stop-helper', updates_ready=True)
            self.activate_root()
            return dict(result, home_changed=True, launch_requested=True, updates_ready=True)

    def verify_root_updater(self, baseline_sha):
        script = """
import hashlib, sys
from pathlib import Path
sys.path.insert(0, '/var/lib/clean-your-tv-root-updater/code')
from updater.device import Device, STATE
from updater.store import Store
from updater.package import safe_bytes, inspect_package
store = Store(STATE)
Device(store).integrity()
if store.read('bootstrap').get('phase') != 'complete': raise ValueError('Incomplete updater setup')
current = store.read('current')
if current.get('sha256') != sys.argv[1]: raise ValueError('Rollback baseline mismatch')
raw = safe_bytes(STATE / 'cache' / (sys.argv[1] + '.ipk'), uid=0)
if hashlib.sha256(raw).hexdigest() != sys.argv[1]: raise ValueError('Rollback cache mismatch')
inspect_package(raw, current)
print('CYTV_UPDATER_VERIFIED')
"""
        if self.remote.run(self._python_command([self._python(), '-c', script, baseline_sha]), timeout=60).strip() != 'CYTV_UPDATER_VERIFIED':
            raise UserError('Root updater recovery verification failed. Keep recovery state and run cytv status.')
        reply = self.remote.luna(UPDATER_APP + '.service/status', {}, app_id=package.ROOT_APP, timeout=110)
        transaction=reply.get('result')
        healthy=(transaction is None or (isinstance(transaction,dict) and transaction.get('schema')==1 and isinstance(transaction.get('id'),str) and re.fullmatch('[a-f0-9]{32}',transaction['id']) and transaction.get('phase') in ('complete','rolled-back','aborted') and transaction.get('homeResumePhase')==transaction.get('phase')))
        if reply.get('returnValue') is not True or 'result' not in reply or not healthy:
            raise UserError('Root updater service is not ready. Keep recovery state and run cytv status.')

    @staticmethod
    def root_active(result):
        return (result.get('recovery', {}).get('integrity_verified') is True
                and (result.get('intent') or {}).get('enabled') is True
                and (result.get('intent') or {}).get('phase') == 'active'
                and result.get('guardian_active') is True
                and result.get('effective', {}).get('sam_home') == package.ROOT_APP
                and result.get('effective', {}).get('profiles', {}).get('idleApp', {}).get('appId') == package.ROOT_APP
                and result.get('effective', {}).get('profiles', {}).get('defaultApps', {}).get('categories', {}).get('home') == package.ROOT_APP)

    def activate_root(self):
        pending=self.store.pending(self.profile) or {}
        if pending.get('product_operation'):
            current=self.product_action('status',pending['product_operation'],verify_current=True)
            if current.get('current') is not True:
                raise UserError('Root setup could not be verified for continuation. Recovery data was kept.')
        self.progress('Checking Root recovery…')
        if self.root_action('status').get('result', {}).get('recovery', {}).get('integrity_verified') is not True:
            raise UserError('Root is installed, but recovery could not be verified. Run cytv status; activation has not started.')
        self.progress('Stopping the old Home Helper…')
        while True:
            try:
                self.stop_helper()
                check = "import sys; sys.path.insert(0, '/var/lib/clean-your-tv-root/runtime'); from helper_bridge import require_idle; require_idle(); print('CYTV_HELPER_IDLE')"
                if self.remote.run(self._python_command([self._python(), '-c', check])).strip() != 'CYTV_HELPER_IDLE':
                    raise RuntimeError('Helper idle state is unconfirmed')
                break
            except RuntimeError:
                if not self.helper_retry():
                    raise UserError('Root is installed, but Home Helper has not stopped. Press Home three times within two seconds (older Helper: hold Home for two seconds), release all buttons, then use Home settings > Turn on Home control. Run cytv status or cytv restore before reinstalling.') from None
        self.store.checkpoint(self.profile, stage='enable')
        self.progress('Turning on Root Home control…')
        try:
            self.root_action('enable')
            self.store.checkpoint(self.profile, stage='launch')
            self.progress('Opening Clean Your TV Home…')
            self.remote.luna('com.webos.applicationManager/launch', {'id': package.ROOT_APP})
            self.store.checkpoint(self.profile, launch_requested=True)
            if not self.root_active(self.root_action('status').get('result', {})):
                raise UserError('Root activation or recovery readback was not confirmed. Run cytv status or cytv restore. Recovery data was kept.')
        except (RuntimeError, ValueError):
            raise UserError('Root is installed, but activation or opening Home could not be confirmed. Run cytv status to inspect it, or cytv restore to return to LG Home. Recovery data was kept; do not reinstall blindly.') from None
        self.store.finish(self.profile)

    def stop_helper(self):
        apps = {app['id'] for app in self.installed_apps()}
        if HELPER in apps:
            self.remote.luna('com.local.nativehome.service/disable', {})
        self.remote.run(
            'if [ -f ' + HELPER_STATE + '/controller.pid ]; then '
            'printf \'{"cmd":"stop"}\' > ' + HELPER_STATE + '/control.json; '
            'n=0; while [ -e ' + HELPER_STATE + '/controller.pid ]; do '
            'n=$((n+1)); [ "$n" -le 15 ] || exit 1; sleep 1; done; fi', timeout=25)

    def installed_apps(self):
        reply = self.remote.luna('com.webos.applicationManager/dev/listApps', {})
        apps = reply.get('apps')
        if not isinstance(apps, list):
            raise UserError('Could not read installed applications.')
        return apps

    def version_summary(self):
        apps = {app['id']: app for app in self.installed_apps()}
        if self.profile['edition'] == 'root':
            root = json.loads((self.payload / 'root/release.json').read_text())['version']
            files = package.data_files((self.payload / 'root-updater/root-updater.ipk').read_bytes())
            updater = json.loads(files['usr/palm/applications/' + UPDATER_APP + '/appinfo.json'])['version']
            targets = [(package.ROOT_APP, 'Root', root), (UPDATER_APP, 'Root Updater', updater)]
        else:
            targets = [(HOME, 'Home', self.manifest['home_version']),
                       (HELPER, 'Home Helper', self.manifest['helper_version'])]
        rows = []
        for app, name, target in targets:
            current = apps.get(app, {}).get('version')
            action = 'Version change'
            if app not in apps:
                action = 'Install'
            elif current == target:
                action = 'Reinstall'
            elif (isinstance(current, str) and re.fullmatch(r'\d+\.\d+\.\d+', current)
                  and re.fullmatch(r'\d+\.\d+\.\d+', target)):
                action = 'Update' if tuple(map(int, current.split('.'))) < tuple(map(int, target.split('.'))) else 'Downgrade'
            current = current or i18n.translate('Unknown version' if app in apps else 'Not installed')
            rows.append(f'{name}: {current} → {target} ({i18n.translate(action)})')
        return rows

    def verify_installed(self):
        apps = {app['id']: app for app in self.installed_apps()}
        for app, key in ((HOME, 'home_version'), (HELPER, 'helper_version')):
            if apps.get(app, {}).get('version') != self.manifest[key]:
                raise UserError('Installed version did not match the package. Run cytv status; do not retry blindly.')

    def status(self):
        pending = self.store.pending(self.profile)
        reconciled = None
        can_resume = False
        if not pending and self.profile['edition']=='root':
            try:
                inspected=self.product_action('inspect')
                active=inspected.get('active_operation')
                if isinstance(active,dict):
                    return {'device':{'product':active},'pending':None,'reconciled':None,'can_resume_root_setup':False,'active_operation':active.get('operation')}
            except (OSError,RuntimeError,ValueError,KeyError):pass
        if pending and pending.get('product_operation') and pending.get('action') in ('install','uninstall'):
            event=self.product_action('status',pending['product_operation'],verify_current=True)
            complete=event['state']=='complete' and event.get('current') is True
            can_resume=False
            if complete and pending['action']=='install':
                try:
                    device=self.root_action('status').get('result',{})
                    if self.root_setup_inactive(device):
                        self.verify_root_updater(event['result']['baseline_sha']);can_resume=True
                except (RuntimeError,ValueError,KeyError,TypeError):pass
            if complete and pending['action']=='uninstall':
                self.store.finish(self.profile)
                reconciled='product-removal-verified'
            return {'device':{'product':event},'pending':self.store.pending(self.profile),'reconciled':reconciled,
                    'can_resume_root_setup':can_resume}
        if pending and pending.get('action') == 'enable-system-updates':
            report = self.system_updater_cleanup('status')
            if report.get('present') is False:
                # The root helper also proves no owned bootstrap process can
                # still create state or submit an installer operation.
                self.store.finish(self.profile)
                reconciled = 'system-updater-not-started'
            elif report.get('present') is True and report.get('bootstrap_complete') is True and report.get('disabled') is False:
                self.store.finish(self.profile)
                reconciled = 'system-updater-bootstrap-verified'
            return {'device': {'system_updater': report}, 'pending': self.store.pending(self.profile),
                    'reconciled': reconciled, 'can_resume_root_setup': False}
        if self.profile['edition'] == 'root':
            raw = self.remote.run('if [ -f ' + ROOT_STATE + '/deploy.json ]; then cat ' + ROOT_STATE + '/deploy.json; '
                                  'elif [ -e ' + ROOT_STATE + ' ] || [ -L ' + ROOT_STATE + ' ]; then printf \'{"stage":"incomplete-state"}\'; '
                                  'else printf \'{"stage":"absent"}\'; fi')
            journal = json.loads(raw)
            stage = journal.get('stage')
            result = {'deployment_stage': stage}
            if pending and pending['action'] == 'archive-root-state':
                readback = self.root_archive('reconcile', pending.get('archive'), pending.get('identity'))
                if readback.get('state') in ('archived', 'not-archived'):
                    self.store.finish(self.profile)
                    pending = None
                    reconciled = 'root-archive-' + readback['state']
            if stage == 'installed-recovery-only':
                result = self.root_action('status')
                if (pending and pending['action'] == 'activate-root'
                        and self.root_active(result.get('result', {}))):
                    self.store.finish(self.profile)
                    reconciled = ('root-activation-verified' if pending.get('launch_requested') is True
                                  else 'root-activation-verified; screen launch unconfirmed, press Home to open it')
                can_resume = self.can_resume_root_setup(pending, result.get('result', {}))
                if self.recover_unstarted_root_updater(pending, result.get('result', {})):
                    pending = None
                    reconciled = 'updater-not-started; recovery verified; reinstallation available'
                if (pending and pending['action'] == 'install' and not pending.get('requires_updater')
                        and result.get('result', {}).get('recovery', {}).get('integrity_verified') is True
                        and self.root_files_match(pending)):
                    self.store.finish(self.profile)
                    reconciled = 'root-installation-verified'
            elif stage == 'uninstalled-state-retained':
                self.verify_absent(package.ROOT_APP)
                if pending and pending['action'] == 'uninstall' and not pending.get('full_project'):
                    self.store.finish(self.profile)
                    reconciled = 'root-removal-verified; TV evidence retained'
            elif stage == 'absent' and pending and pending['action'] == 'install':
                self.verify_absent(package.ROOT_APP)
                self.store.finish(self.profile)
                reconciled = 'no-root-installation-submitted'
        else:
            result = {'apps': [{k: app.get(k) for k in ('id', 'version')} for app in self.installed_apps() if app.get('id') in (HOME, HELPER)],
                      'helper_state': self.helper_state()}
            if pending and pending['action'] == 'install' and pending.get('expected'):
                expected = pending['expected']
                versions = pending.get('versions', {HOME: self.manifest.get('home_version'), HELPER: self.manifest.get('helper_version')})
                actual = {app['id']: app.get('version') for app in result['apps']}
                if actual == versions:
                    try:
                        raw = self.remote.run('sha256sum ' + ' '.join(shlex.quote(n) for n in sorted(expected)))
                        hashes = {line.split(None, 1)[1]: line.split(None, 1)[0] for line in raw.splitlines()}
                        if hashes == expected:
                            self.save_eim(pending.get('eim_registered', 'unknown'))
                            self.store.finish(self.profile)
                            reconciled = 'installed-files-verified; helper launch requires TV check'
                    except (RuntimeError, ValueError, IndexError):
                        pass  # An incomplete readback retains the receipt.
            elif pending and pending['action'] == 'uninstall' and pending.get('stage') == 'removing' and not result['apps']:
                self.verify_absent(HOME)
                self.verify_absent(HELPER)
                self.store.finish(self.profile)
                reconciled = 'removal-verified'
        return {'device': result, 'pending': self.store.pending(self.profile), 'reconciled': reconciled,
                'can_resume_root_setup': can_resume,
                **({'deployment_stage': stage} if self.profile['edition'] == 'root' else {})}

    @staticmethod
    def root_setup_inactive(device):
        try:
            effective = device.get('effective', {})
            profiles = effective.get('profiles', {})
            never_activated = (device.get('journal_exists') is False
                               and 'guardian_active' not in device
                               and 'intent' in device and device['intent'] is None)
            disabled = (device.get('guardian_active') is False
                        and isinstance(device.get('intent'), dict)
                        and device['intent'].get('enabled') is False)
            if (device.get('recovery', {}).get('integrity_verified') is not True
                    or not (never_activated or disabled)
                    or effective.get('sam_home') != 'com.webos.app.home'
                    or profiles.get('defaultApps', {}).get('categories', {}).get('home') != 'com.webos.app.home'
                    or profiles.get('idleApp', {}).get('appId') != 'com.webos.app.home'):
                return False
            return True
        except (AttributeError, TypeError):
            return False

    def can_resume_root_setup(self, pending, device):
        if (self.profile['edition'] != 'root' or not pending
                or pending.get('action') != 'setup-root-updater'
                or pending.get('stage') != 'verify' or pending.get('requires_updater') is not True
                or not isinstance(pending.get('baseline_sha'), str)
                or len(pending['baseline_sha']) != 64
                or any(c not in '0123456789abcdef' for c in pending['baseline_sha'])
                or not self.root_setup_inactive(device)):
            return False
        try:
            if not self.root_files_match(pending):
                return False
            self.verify_root_updater(pending['baseline_sha'])
            return True
        except (RuntimeError, ValueError, TypeError, KeyError):
            return False

    def resume_root_setup(self):
        # Revalidate after the user's confirmation; never resubmit package setup.
        if self.status().get('can_resume_root_setup') is not True:
            raise UserError('Root setup could not be verified for continuation. Recovery data was kept.')
        self.store.checkpoint(self.profile, action='activate-root', stage='stop-helper', updates_ready=True)
        self.activate_root()
        return {'installed': package.ROOT_APP, 'home_changed': True, 'launch_requested': True, 'updates_ready': True}

    def recover_unstarted_root_updater(self, pending, device):
        """Resolve only a proven pre-bootstrap failure; never change TV state."""
        if (self.profile['edition'] != 'root' or not pending
                or pending.get('action') != 'setup-root-updater' or pending.get('stage') != 'setup'
                or pending.get('requires_updater') is not True):
            return False
        try:
            if not self.root_setup_inactive(device):
                return False
            # A disconnected SSH session may leave bootstrap validating its bundle.
            # Check this before paths: bootstrap creates state before any mutation.
            script = """from pathlib import Path
import os
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name) == os.getpid(): continue
    try: args = (proc/'cmdline').read_bytes().split(b'\\0')
    except FileNotFoundError: continue
    if any(arg.rsplit(b'/',1)[-1] == b'setup-updater.py' for arg in args):
        raise RuntimeError('Updater bootstrap is still running')
print('CYTV_BOOTSTRAP_IDLE')
"""
            if self.remote.run(self._python_command([self._python(), '-c', script])).strip() != 'CYTV_BOOTSTRAP_IDLE':
                return False
            condition = ' || '.join('[ -e ' + shlex.quote(p) + ' ] || [ -L ' + shlex.quote(p) + ' ]' for p in root_updater_paths())
            if self.remote.run('if ' + condition + '; then printf CYTV_EXISTING_UPDATER; else printf CYTV_UPDATER_ABSENT; fi').strip() != 'CYTV_UPDATER_ABSENT':
                return False
            idle = self.remote.luna('com.webos.appInstallService/status', {'subscribe': True})
            if idle.get('returnValue') is not True or idle.get('status', {}).get('apps') != []:
                return False
            if not self.root_files_match(pending):
                return False
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError):
            return False
        # Archive the incomplete operation before unlocking an explicit reinstall.
        from .state import private_write
        receipt = self.store.recovery(self.profile, 'updater-not-started')
        private_write(receipt, json.dumps({'action': 'updater-not-started', 'stage': 'verified', 'previous': pending}).encode())
        self.store.finish(self.profile)
        return True

    def prepare_root_reinstall(self, already_removed=False):
        if self.profile['edition'] != 'root' or self.store.pending(self.profile):
            raise UserError('Reinstallation needs a resolved Root deployment. Run cytv status first.')
        if not already_removed:
            self.progress('Restoring LG Home and removing the previous Root…')
            self.uninstall()
        self.verify_absent(package.ROOT_APP)
        inspected = self.root_archive('inspect')
        if inspected.get('busy') is not False:
            raise UserError('Previous Root was removed. Restart the TV with its remote, wait for LG Home, then run cytv again. Old Root processes must stop before reinstallation. Recovery data was kept.')
        archive = ROOT_STATE + '.archive-' + uuid.uuid4().hex
        self.store.begin(self.profile, 'archive-root-state', archive=archive, identity=inspected['identity'])
        self.progress('Keeping the previous recovery state in an archive…')
        reply = self.root_archive('archive', archive, inspected['identity'])
        if reply.get('archived') != archive:
            raise UserError('Recovery archive was not confirmed. Run cytv status; do not retry blindly.')
        self.store.finish(self.profile)
        self.progress('Previous recovery state retained: ' + archive)
        return archive

    def root_archive(self, action, destination=None, identity=None):
        from .root_archive import SCRIPT
        args = [self._python(), '-c', SCRIPT, action]
        if destination is not None:
            args += [destination, json.dumps(identity)]
        reply = json.loads(self.remote.run(self._python_command(args)))
        if not isinstance(reply, dict):
            raise UserError('Recovery archive could not be verified. Keep recovery state and run cytv status.')
        return reply

    def verify_absent(self, app):
        service = HOME + '.renewal' if app == HOME else app + '.service'
        paths = [BASE + '/applications/' + app, BASE + '/services/' + service, BASE + '/packages/' + app]
        condition = ' || '.join('[ -e ' + shlex.quote(p) + ' ] || [ -L ' + shlex.quote(p) + ' ]' for p in paths)
        if self.remote.run('if ' + condition + '; then printf CYTV_REMAINS; fi').strip():
            raise UserError('Application, service or package files remain on the TV. Keep recovery evidence; removal is not complete.')

    def read_eim(self):
        try:
            reply = self.remote.luna('com.webos.service.eim/getAllInputStatus', {})
            devices = reply.get('devices')
            if not isinstance(devices, list) or not all(isinstance(d, dict) and isinstance(d.get('id'), str) for d in devices):
                return 'unknown'
            return any(d.get('appId') == HOME or d.get('id') == HOME for d in devices)
        except RuntimeError:
            return 'unknown'

    def save_eim(self, value):
        from .state import private_write
        if self.store.pending(self.profile):
            self.store.checkpoint(self.profile, eim_registered=value)
        private_write(self.store.device_dir(self.profile) / 'installation.json', json.dumps({'eim_registered': value}).encode())

    def root_files_match(self, pending):
        if not pending.get('release_sha') or not pending.get('bundle_sha'):
            return False
        script = '''import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/var/lib/clean-your-tv-root')
import deploy
state=Path('/var/lib/clean-your-tv-root')
for name,digest in [('release.json',sys.argv[1]),('bundle.json',sys.argv[2])]:
    if hashlib.sha256(deploy.checked_file(state,name)).hexdigest()!=digest: raise ValueError('Different release')
release=json.loads(deploy.checked_file(state,'release.json'))
files=dict(release['files'])
if sys.argv[3]=='migrate':
    private=json.loads(deploy.checked_file(state,'personalization.json'))
    for name,digest in private['files'].items():
        files['usr/palm/applications/com.cleanyourtv.root.preview/'+name]=digest
for name,digest in files.items():
    if hashlib.sha256(deploy.checked_file(deploy.INSTALLED,name)).hexdigest()!=digest: raise ValueError('Changed payload')
print('CYTV_ROOT_FILES_OK')
'''
        try:
            args = [self._python(), '-c', script, pending['release_sha'], pending['bundle_sha'], 'migrate' if pending.get('migrate') else 'fresh']
            return self.remote.run(self._python_command(args)).strip() == 'CYTV_ROOT_FILES_OK'
        except RuntimeError:
            return False

    def restore(self):
        from .state import private_write
        receipt = self.store.recovery(self.profile, 'restore')
        result = self.restore_device()
        private_write(receipt, b'{"action":"restore","stage":"complete"}')
        pending = self.store.pending(self.profile)
        if pending and pending['action'] in ('trial', 'activate-root'):
            self.store.finish(self.profile)
        return result

    def restore_device(self):
        if self.profile['edition'] == 'root':
            return self.root_action('restore')
        self.stop_helper()
        receipt = self.store.device_dir(self.profile) / 'installation.json'
        installation = json.loads(receipt.read_text()) if receipt.exists() else {}
        pending = self.store.pending(self.profile) or {}
        eim = pending.get('eim_registered', installation.get('eim_registered', 'unknown'))
        eim_error = False
        if eim is not False:
            try:
                self.remote.luna('com.webos.service.eim/deleteDevice', {'appId': HOME})
                self.save_eim(False)
            except RuntimeError:
                if self.read_eim() is False:
                    self.save_eim(False)
                else:
                    eim_error = True
        self.remote.luna('com.webos.applicationManager/launch', {'id': 'com.webos.app.home'})
        if eim_error:
            raise UserError('LG Home launch was requested, but input restoration removal is unconfirmed. Keep recovery state and run cytv doctor before uninstalling.')
        return {'restored': True, 'pending': self.store.pending(self.profile)}

    def system_updater_cleanup(self, action, archive=None):
        from .system_updater_remove import COMMAND
        args = [self._python(), '-c', COMMAND, action]
        if archive is not None:
            args.append(archive)
        reply = json.loads(self.remote.run(self._python_command(args), timeout=60))
        if not isinstance(reply, dict):
            raise UserError('Updater permissions removal could not be verified.')
        return reply

    def root_updater_cleanup(self, action, archive):
        from .root_updater_remove import COMMAND
        reply = json.loads(self.remote.run(self._python_command([self._python(), '-c', COMMAND, action, archive]), timeout=60))
        if not isinstance(reply, dict):
            raise UserError('Root Updater cleanup could not be verified.')
        return reply

    def cleanup_legacy_permissions(self):
        from .legacy_permissions_remove import SCRIPT
        if self.remote.run(self._python_command([self._python(), '-c', SCRIPT]), timeout=30).strip() != 'CYTV_LEGACY_PERMISSIONS_REMOVED':
            raise UserError('Updater permissions removal could not be verified.')

    def cleanup_updater_app_permissions(self):
        from .app_permissions_remove import SCRIPT
        if self.remote.run(self._python_command([self._python(), '-c', SCRIPT]), timeout=30).strip() != 'CYTV_APP_PERMISSIONS_REMOVED':
            raise UserError('Root Updater app permissions removal could not be verified. Recovery data was kept.')

    def verify_project_removed(self):
        script = """import os
from pathlib import Path
apps=('com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.updater','com.gathin.tvhome','com.local.nativehome','com.cleanyourtv.system.updater')
paths=['/var/lib/webosbrew/init.d/50-clean-your-tv-root','/var/lib/webosbrew/init.d/51-clean-your-tv-root-updater',
       '/var/lib/webosbrew/init.d/52-clean-your-tv-system-updater',
       '/var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json',
       '/var/webos-profile/override/clean-your-tv-root.json']
if any(os.path.lexists(p) for p in paths): raise ValueError('Project startup or routing remains')
for folder in ('services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d'):
    for p in (Path('/var/luna-service2-dev')/folder).iterdir():
        if any(p.name.startswith(app+'.') for app in apps): raise ValueError('Project bus registration remains')
print('CYTV_PROJECT_REMOVED')
"""
        if self.remote.run(self._python_command([self._python(), '-c', script])).strip() != 'CYTV_PROJECT_REMOVED':
            raise UserError('Project startup or service registrations remain. Removal is not complete.')
        settings = self.remote.luna('com.webos.settingsservice/getSystemSettings', {'category': 'general', 'keys': ['defaultApps']})
        reply = self.remote.luna('com.webos.service.systemprofile/getProfiles', {'names': ['defaultApps', 'idleApp'], 'subscribe': False})
        try:
            profiles = reply['profiles']
            routes = (settings['settings']['defaultApps']['home'], profiles['defaultApps']['categories']['home'], profiles['idleApp']['appId'])
            if settings.get('returnValue') is not True or reply.get('returnValue') is not True or any(route != 'com.webos.app.home' for route in routes):
                raise ValueError('LG Home routing differs')
        except (KeyError, TypeError, ValueError):
            raise UserError('LG Home routing could not be verified. Keep recovery data.') from None

    def recover_root_removal(self, action):
        from .root_remove_recovery import SCRIPT
        reply = json.loads(self.remote.run(self._python_command([self._python(), '-c', SCRIPT, action]), timeout=1080))
        if not isinstance(reply, dict) or reply.get('returnValue') is not True:
            if isinstance(reply, dict) and reply.get('reason') == 'busy':
                raise UserError('The previous removal is still running. Wait a minute, then choose Remove again. The app will check the TV before continuing.')
            raise UserError('The TV has not confirmed the previous package removal. Recovery records were kept. Restart the TV, then choose Remove again to check its state. If this message returns, send the diagnostic report to support.')
        return reply

    def uninstall_project(self):
        pending=self.store.pending(self.profile)
        if pending:
            if pending.get('action')!='uninstall' or pending.get('full_project') is not True or not pending.get('product_operation'):
                raise UserError('An earlier operation needs recovery before full removal. Recovery data was kept.')
            event=self.product_action('status',pending['product_operation'],verify_current=True)
            if event['state']!='complete' or event.get('current') is not True:
                raise UserError('Previous package removal outcome is unknown or the app reappeared; it was not submitted again.')
            result=event['result']
        else:
            # Validate/stage the current trusted code before reserving host intent.
            self.coordinator_code()
            operation=uuid.uuid4().hex
            self.store.begin(self.profile,'uninstall',full_project=True,product_operation=operation,stage='coordinator-upload')
            stage=self.upload_product(self.payload/'root')
            self.store.checkpoint(self.profile,stage='coordinator-submitted',product_payload=stage)
            result=self.await_product('remove',operation,stage)
        proof=self.product_action('status',(self.store.pending(self.profile) or {})['product_operation'],verify_current=True)
        if proof.get('current') is not True:
            raise UserError('Project startup or service registrations remain. Removal is not complete.')
        if result.get('removed') is not True or result.get('applications_services_startup_removed') is not True:
            raise UserError('Project startup or service registrations remain. Removal is not complete.')
        self.store.finish(self.profile)
        return result

    def uninstall(self, full_project=False):
        if full_project and self.profile['edition'] == 'root':
            return self.uninstall_project()
        pending = self.store.pending(self.profile)
        if pending:
            # Repeated remove requests are just as uncertain as repeated installs.
            resuming_remove = pending['action'] == 'uninstall' and self.profile['edition'] == 'no-root'
            if pending['action'] != 'install' and not resuming_remove:
                raise UserError('Previous operation is unresolved. Run cytv status and retain recovery evidence before removal.')
            idle = self.remote.luna('com.webos.appInstallService/status', {'subscribe': True})
            if idle.get('status', {}).get('apps') != []:
                raise UserError('TV installer is not confirmed idle. Keep the receipt and run cytv status before removal.')
            if not resuming_remove:
                self.store.checkpoint(self.profile, previous=pending, action='uninstall', stage='pending')
        else:
            self.store.begin(self.profile, 'uninstall')
        if self.profile['edition'] == 'root':
            result = self.root_action('uninstall')
            if result.get('removed') != package.ROOT_APP or result.get('state_retained') != ROOT_STATE:
                raise UserError('Root removal readback was unexpected. Keep recovery state and run cytv status before reinstalling.')
        else:
            self.restore()
            self.store.checkpoint(self.profile, stage='removing')
            apps = {app['id'] for app in self.installed_apps()}
            removals = dict(self.store.pending(self.profile).get('removals', {}))
            for app in (HELPER, HOME):
                previous = removals.get(app)
                if previous == 'submitted' and app in apps:
                    raise UserError('Previous package removal outcome is unknown. It was not resubmitted; run cytv status and retain evidence.')
                if previous in ('done', 'terminal') and app in apps:
                    raise UserError('A removed package is present again. Keep recovery evidence; it was not removed again.')
                if app in apps:
                    removals[app] = 'submitted'
                    self.store.checkpoint(self.profile, removals=removals)
                    self.remote.luna('com.webos.appInstallService/dev/remove', {'id': app, 'subscribe': True}, terminal='removed', timeout=150)
                    removals[app] = 'terminal'
                    self.store.checkpoint(self.profile, removals=removals)
                if removals.get(app) == 'terminal':
                    # Only a terminal removal receipt permits empty package metadata cleanup.
                    directory = BASE + '/packages/' + app
                    self.remote.run('if [ -d ' + directory + ' ] && [ ! -L ' + directory + ' ]; then rmdir ' + directory + ' 2>/dev/null || true; fi')
                self.verify_absent(app)
                removals[app] = 'done'
                self.store.checkpoint(self.profile, removals=removals)
            if any(app['id'] in (HOME, HELPER) for app in self.installed_apps()):
                raise UserError('Removal could not be verified. Keep the operation journal.')
            self.verify_absent(HOME)
            self.verify_absent(HELPER)
            result = {'removed': True}
        self.store.finish(self.profile)
        return result

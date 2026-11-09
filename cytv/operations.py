"""Edition-specific operations; SSH is the only device mutation boundary."""
import json
import hashlib
import re
from pathlib import Path, PurePosixPath
import shlex
import shutil
import tempfile
import time
from time import sleep
import uuid

from . import package, i18n, diagnostics, graphics, storage
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


def require_removal_idle(remote, profile, pending):
    if pending and pending.get('recovery_protocol') == 'no-root-original-stream-v1':
        raise UserError('The original No-root operation cannot safely continue. Recovery data was kept.', reason_code='pending-operation')
    # A fresh uninstall reserves its journal before restore(), and only changes
    # to "removing" before any package request. Resume that pre-submission state
    # like a fresh uninstall: dev/remove has its own terminal reply stream.
    # Never apply this to an inherited install or an uncertain package outcome.
    from .recovery_state import unsubmitted_removal
    if unsubmitted_removal(profile, pending):
        return
    try:
        idle = remote.luna('com.webos.appInstallService/status', {'subscribe': True}, timeout=10)
    except TVRejected as error:
        if profile.get('edition') == 'no-root' and error.luna.get('operation') == 'package-status':
            from .failure_help import GUIDES
            # Keep the typed/numeric evidence, but do not suggest repeating
            # Doctor as a way around an unavailable recovery capability.
            error.args = ('\n'.join(GUIDES['recovery-status-rejected'][:3]),)
        raise
    if (not isinstance(idle, dict) or idle.get('returnValue') is not True or
            not isinstance(idle.get('status'), dict) or idle['status'].get('apps') != []):
        raise UserError('TV installer is not confirmed idle. Keep the receipt and run cytv status before removal.', reason_code='pending-operation')


class Installer:
    def __init__(self, remote, store, profile, payload, manifest, progress=print, tv_info=None, checks=None):
        self.remote, self.store, self.profile = remote, store, profile
        self.payload, self.manifest, self.progress = Path(payload), manifest, progress
        self.helper_retry = lambda: False
        self.reconnect = None
        self.tv_info = tv_info if tv_info is not None else {}
        from .checks import CheckList
        self.checks = checks if checks is not None else CheckList()
        from .outcomes import SetupOutcome
        self.outcome = SetupOutcome(self.checks, self.tv_info)
        self.use_runtime_variant()

    def use_runtime_variant(self):
        if self.profile.get('root_variant') == 'node012-beta':
            from .root_runtime import select_payload
            if not getattr(self, '_runtime_variant_selected', False):
                self.payload, self.manifest = select_payload(self.payload, self.manifest)
                self._runtime_variant_selected = True
            self.tv_info['root_variant'] = 'node012-beta'
            self.checks.root_variant = 'node012-beta'

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
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
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
            if not isinstance(reply,dict) or reply.get('installed') is not True or reply.get('version')!='1.2.8' or not all(reply.get(k) is True for k in ('root_unchanged','home_unchanged','profile_storage_untouched')):
                raise ValueError('Unconfirmed System replacement')
            return reply
        except Exception:
            raise UserError('System updater setup was not confirmed. Keep recovery state and run cytv status.') from None

    def configure_firmware_access(self, enabled=True, repair=False):
        if self.profile['edition']!='root' or not self.remote.root:
            raise UserError('Homebrew API access requires an existing Root installation.')
        if self.store.pending(self.profile):
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        from .firmware_access import program
        try:
            source=program(self.payload/'root',enabled,repair=True) if repair else program(self.payload/'root',enabled)
            reply=json.loads(self.remote.run(self._python_command([self._python(ROOT_STATE),'-I','-']),data=source.encode(),timeout=60))
            if not isinstance(reply,dict) or reply.get('returnValue') is not True or reply.get('permissions_installed') is not enabled:raise ValueError('Unconfirmed firmware permission action')
            return reply
        except Exception:
            raise UserError('Homebrew API access repair was not confirmed. Keep recovery state and retry the same command.') from None

    def enable_system_updates(self):
        if self.profile.get('root_variant') == 'node012-beta':
            raise UserError('Root Beta automatic updates are unavailable; use the computer installer.')
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
            self._python(), '-B', stage + '/setup-system-updater.py', '--bundle', stage,
            '--edition', self.profile['edition'], '--device', '--apply']), timeout=360))
        if not isinstance(reply, dict) or reply.get('installed') is not True:
            raise UserError('System updater setup was not confirmed. Keep recovery state and run cytv status.')
        self.store.finish(self.profile)
        return reply

    def coordinator_code(self, recovery=False):
        """Stage trusted host code for read-only handoff/status, never retained code."""
        cache='_recovery_code' if recovery else '_coordinator_code'
        existing=getattr(self,cache,None)
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
        for name in (*files,'bundle.json'):
            if name.endswith('.ipk') and not recovery: continue
            target=stage+'/'+package.safe_name(name)
            self.remote.run('mkdir -p '+shlex.quote(str(PurePosixPath(target).parent)))
            self.remote.upload(target,(bundle/name).read_bytes(),mode=0o600)
        setattr(self,cache,stage)
        return stage

    def product_action(self, action, operation=None, payload=None, migrate=False, verify_current=False, resume=False, trusted_recovery=False, retire_stages=(), helper_fence=None, removal_intent=None, removal_lease=None):
        if action not in ('inspect','install','native-install','status','remove','clean-remove','clean-status','clean-target'): raise ValueError('Unsupported product action')
        if action!='inspect' and (not isinstance(operation,str) or not re.fullmatch('[a-f0-9]{32}',operation)):
            raise ValueError('Invalid product operation')
        # Keep execution-boundary evidence without exporting commands, paths or
        # stderr. A status failure is not the retained deployment failure.
        boundary='coordinator-stage'
        try:
            driver=(payload+'/root-updater' if payload else self.coordinator_code())+'/install_driver.py'
            boundary='python-select'
            if action in ('clean-remove','clean-target','native-install'):
                # Fresh support imports and a host-verified interpreter; no
                # retained launcher/binding module executes during full cleanup.
                python=self._select_python(provision=True)
                self._selected_python=python
                entry='import runpy,sys;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name="__main__")'
                args=[python,'-I','-B','-c',entry,driver.rsplit('/',1)[0],driver,action]
            else:args=[action] if trusted_recovery or resume else [self._python(),'-B',driver,action]
            if operation: args+=['--operation',operation]
            if payload:
                args+=['--payload',payload]
                candidate=getattr(self,'_product_candidates',{}).get(payload)
                if candidate: args+=['--candidate',candidate]
            if migrate: args.append('--migrate-packaged-home')
            if verify_current:args.append('--verify-current')
            if removal_intent is not None:
                if action!='clean-remove' or not re.fullmatch('[a-f0-9]{32}',removal_intent):raise ValueError('Invalid removal intent')
                args+=['--removal-intent',removal_intent]
            if helper_fence is not None:
                if action!='clean-remove':raise ValueError('Helper fence requires clean removal')
                args+=['--helper-fence',json.dumps(helper_fence,sort_keys=True,separators=(',',':'))]
            if removal_lease is not None:
                if action!='clean-remove' or (removal_lease!='-' and not re.fullmatch('[a-f0-9]{32}',removal_lease)):
                    raise ValueError('Invalid current removal lease')
                args+=['--removal-lease',removal_lease]
            for retired in retire_stages:
                if action!='clean-remove' or not isinstance(retired,str) or not re.fullmatch(r'/tmp/cytv-product-[a-f0-9]{32}',retired):
                    raise ValueError('Invalid cleanup support stage')
                args+=['--retire-stage',retired]
            if resume:
                if action != 'install' or payload is not None:
                    raise ValueError('Original installation continuation required')
                args += ['--resume', '--final-readback-only']
            boundary='driver'
            if trusted_recovery or resume:
                from .root_install_recovery import run
                raw=run(self,driver.rsplit('/',1)[0],'install_driver.py',args,timeout=90)
            else:raw=self.remote.run(self._python_command(args),timeout=1080 if action in ('clean-remove','native-install') else 90)
            reply=json.loads(raw)
        except TVCommandError as error:
            error.root_action=action
            error.root_boundary=boundary
            raise
        if (not isinstance(reply,dict) or reply.get('operation')!=operation
                or reply.get('state') not in ('pending','complete','recovery_required','unknown','fresh','installed','unsupported','conflict','migration_required')):
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.', reason_code='root-operation-unconfirmed')
        status = self.tv_info.setdefault('status', {})
        status.setdefault('device', {})['product'] = diagnostics.context.product_summary(reply)
        return reply

    def await_product(self, action, operation, payload, migrate=False):
        reply=self.product_action(action,operation,payload,migrate=migrate)
        deadline=time.monotonic()+1080
        while reply['state']=='pending' and time.monotonic()<deadline:
            time.sleep(1)
            reply=self.product_action('status',operation)
        if reply['state']!='complete':
            if reply.get('code') == 'installer-runtime-mismatch':
                from .root_runtime_contract import MISMATCH
                raise UserError(MISMATCH, reason_code='installer-runtime-mismatch')
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        return reply['result']

    def upload_product(self, root_bundle, clean_removal=False):
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
        if clean_removal:
            pending=self.store.pending(self.profile)
            if not pending or pending.get('recovery_protocol')!='clean-removal-v1':raise ValueError('Clean removal intent required')
            stages=list(pending.get('cleanup_stages',[]))
            if any(not isinstance(path,str) or not re.fullmatch(r'/tmp/cytv-product-[a-f0-9]{32}',path) for path in stages):
                raise ValueError('Invalid cleanup support stage')
            self.store.checkpoint(self.profile,cleanup_stages=stages+[stage])
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
        reply=self.product_action('inspect')
        if reply.get('reason')=='restart-required':
            raise UserError('Previous Root was removed. Restart the TV with its remote, wait for LG Home, then run cytv again. Old Root processes must stop before reinstallation. Recovery data was kept.',reason_code='restart-required')
        if reply.get('reason')=='project-apps-remain':
            raise UserError('Clean Your TV apps are present after the previous full removal. To switch to Root, first run Uninstall Clean Your TV with the saved Root connection. This removes No-root Home and Helper too; back up preferences, wait for verified removal, then install Root.',reason_code='project-apps-remain')
        result=reply.get('installation')
        if not isinstance(result,dict):
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.', reason_code='root-operation-unconfirmed')
        return result

    def native_root_present(self):
        script = "if " + ' || '.join('[ -e '+ROOT_STATE+'/'+name+' ] || [ -L '+ROOT_STATE+'/'+name+' ]'
            for name in ('home-backend.json','c1-gate','c1-keyfilter','runtime/c1-home-gate','runtime/c1-keyfilter-guard','runtime/c1_gate.py','runtime/c1_keyfilter.py'))
        return self.remote.run(script+'; then printf CYTV_C1_GATE; fi').strip() == 'CYTV_C1_GATE'

    def collect_root_diagnostics(self, cursor=None):
        try:
            from .root_activation_diagnostics import collect
            value=collect(self.remote,self._python(ROOT_STATE),cursor)
            self.tv_info['root_diagnostics']=diagnostics.context.root_diagnostics_summary(value)
            return value.get('cursor')
        except Exception:
            # Optional evidence must not change recovery or hide the primary error.
            self.tv_info['root_diagnostics']={'health_log':{'status':'unavailable'}}
            return None

    def root_action(self, action, bundle=None, migrate=False, experimental=False):
        driver = (bundle or ROOT_STATE) + '/deploy.py'
        args = [self._python(ROOT_STATE), driver, action]
        if bundle:
            args += ['--bundle', bundle]
        if migrate:
            args.append('--migrate-packaged-home')
        if experimental:
            if action != 'install': raise ValueError('Experimental admission applies only to a fresh install')
            args.append('--experimental-c1-gate')
        attempt = uuid.uuid4().hex if action == 'install' else None
        command = self._python_command(args)
        if attempt: command = 'env CYTV_ROOT_INSTALL_ATTEMPT='+attempt+' '+command
        if action == 'enable' and isinstance(self.tv_info.get('status'), dict):
            self.tv_info['status']['observation_phase']='before-enable'
        cursor = self.collect_root_diagnostics() if action == 'enable' else None
        try:
            raw = self.remote.run(command, timeout=1080 if action == 'uninstall' else 720 if action == 'restore' or experimental else 180)
        except TVCommandError as error:
            if action == 'enable':
                self.collect_root_diagnostics(cursor)
                from .root_action_failure import apply_activation_reason
                apply_activation_reason(error, self.tv_info)
            error.root_action = action
            error.root_boundary = 'driver'
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
        if action == 'enable': self.collect_root_diagnostics(cursor)
        reply = json.loads(raw)
        if not isinstance(reply, dict) or reply.get('returnValue') is not True:
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.', reason_code='root-operation-unconfirmed')
        return reply

    def preflight(self, install=False, home_interfaces=False):
        diagnostics.context.collect_node_version(self.remote, self.tv_info)
        if self.profile['edition'] == 'root':
            from .python_runtime import SYSTEM_PROBE
            probes = ('test "$(id -u)" = 0', 'test -x /usr/bin/python3',
                      'test -x /usr/bin/luna-send', 'test -d /media/developer/apps',
                      'test -d /var/luna-service2-dev',
                      '/usr/bin/python3 -c "import json"', '/usr/bin/python3 -c "import fcntl"',
                      self._python_command(['/usr/bin/python3', '-I', '-B', '-c', SYSTEM_PROBE]),
                      '/usr/bin/node -e \'process.exit(Number(process.versions.node.split(".")[0]) >= 8 ? 0 : 1)\'')
            if self.profile.get('root_variant') == 'node012-beta':
                from .root_runtime import NODE_BETA_PROBE, VENDOR_PROBE
                probes = (*probes[:-1], NODE_BETA_PROBE)
                if self.remote.run(VENDOR_PROBE, timeout=10).strip() != 'CYTV_VENDOR_READY':
                    raise UserError('Root Beta vendor modules could not be loaded. Installation has not started. Save the diagnostic report.', reason_code='root-requirements')
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
            if home_interfaces:
                from .root_capabilities import verify, CALLS
                if all(checks[name]=='pass' for name in checks if name not in python_names):
                    if not install and self.native_root_present():
                        device = self.root_action('status').get('result', {})
                        if device.get('backend') != 'c1-native-gate' or not (self.root_active(device) or self.root_setup_inactive(device)):
                            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.', reason_code='root-operation-unconfirmed')
                        self.tv_info['home_backend'] = 'c1-native-gate'
                        for name in CALLS:
                            checks.pop(name, None)
                            self.checks.update(name, 'unknown')
                    elif 'c1-native-gate' in self.manifest.get('root_backends', {}):
                        verify(self.remote, self.checks, self.tv_info, allow_c1=True,
                               allow_compositor=self.manifest['root_backends']['c1-native-gate'].get('admission_schema') == 3)
                    else:
                        verify(self.remote, self.checks, self.tv_info)
                else:
                    checks.update(dict.fromkeys(CALLS, 'unknown'))
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
                    requirements=', '.join(failed)), reason_code='root-requirements')
            if install:
                paths = [ROOT_STATE, BASE + '/applications/' + package.ROOT_APP,
                         BASE + '/services/' + package.ROOT_APP + '.service', BASE + '/packages/' + package.ROOT_APP,
                         '/var/lib/clean-your-tv-installation/operation.json']
                condition = ' || '.join('[ -e ' + p + ' ] || [ -L ' + p + ' ]' for p in paths)
                existing=self.remote.run('if ' + condition + '; then printf CYTV_EXISTING_ROOT; fi').strip()
                maintain=False
                self._native_clean_install=False
                if existing:
                    try:
                        installation=self.root_installation()
                        maintain=(installation.get('clean_removal_verified') is True and
                                  installation.get('can_install') is True)
                        self._native_clean_install=(installation.get('clean_removal_verified') is True
                            and installation.get('can_install') is True and self.tv_info.get('home_backend')=='c1-native-gate')
                    except UserError as error:
                        if error.reason_code in ('restart-required','project-apps-remain'):raise
                    except (OSError,ValueError,RuntimeError): pass
                if existing and not maintain:
                    raise ExistingRoot('Root is already installed or recovery state remains. Connect interactively to review reinstallation; existing state was left unchanged.')
        else:
            if install and self.profile.get('connection') == 'root-ssh':
                from .root_runtime import FRESH_PROBE
                if self.remote.run(FRESH_PROBE, timeout=10).strip() != 'CYTV_FRESH_ROOT':
                    from .root_no_root_handoff import probe
                    try:self._root_handoff=probe(self)
                    except (OSError,ValueError,RuntimeError):
                        raise UserError('Previous Root installation needs recovery. Run cytv status or cytv restore. Reinstallation has not started; recovery data was left unchanged.') from None
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
                node = self.remote.run('if /usr/bin/node -e \'var v=process.versions.node.split(".").map(Number);process.exit(v[0]>0||v[1]>10||(v[1]===10&&v[2]>=15)?0:1)\'; then printf CYTV_NODE_READY; fi')
                self.checks.update('helper-node', 'pass' if node.strip() == 'CYTV_NODE_READY' else 'fail',
                                   '' if node.strip() == 'CYTV_NODE_READY' else 'Home Helper requires TV Node.js 0.10.15 or newer. Installation has not started.')
                if node.strip() != 'CYTV_NODE_READY':
                    raise UserError('Home Helper requires TV Node.js 0.10.15 or newer. Installation has not started.')
            self.checks.update('root-conflict', 'running')
            root_state = self.remote.run(
                'if [ -e /var/webos-profile/override/clean-your-tv-root.json ] || '
                '[ -L /var/webos-profile/override/clean-your-tv-root.json ] || '
                '[ -e /var/lib/clean-your-tv-root/home-backend.json ] || '
                '[ -L /var/lib/clean-your-tv-root/home-backend.json ] || '
                '[ -e /var/lib/clean-your-tv-root/c1-gate ] || '
                '[ -L /var/lib/clean-your-tv-root/c1-gate ] || '
                '[ -e /var/lib/clean-your-tv-root/runtime/c1-home-gate ] || '
                '[ -L /var/lib/clean-your-tv-root/runtime/c1-home-gate ]; then printf CYTV_ROOT_STATE; fi')
            self.checks.update('root-conflict', 'fail' if root_state.strip() else 'pass',
                               'Root Home routing is present. Restore it with cytv --edition root restore first.' if root_state.strip() else '')
            if root_state.strip():
                raise UserError('Root Home routing is present. Restore it with cytv --edition root restore first.')
            if not install:
                return
            self.checks.update('helper-idle', 'running')
            helper = self.helper_state()
            self.tv_info['helper_state'] = helper
            self.checks.update('helper-idle', 'unknown' if helper == 'uncertain' else 'fail' if helper == 'running' else 'pass')
            if helper == 'running':
                raise UserError('Home Helper is running. Installation has not started; installed versions are unchanged. Press Home three times within two seconds (older Helper: hold Home for two seconds) to stop it, then rerun installation.', reason_code='helper-running')
            if helper == 'uncertain':
                raise UserError('Home Helper state could not be verified. Installation has not started; installed versions are unchanged. Run Check TV status and save a diagnostic report before retrying. Do not delete Helper state files.', reason_code='helper-state-unverified')
            if helper == 'stale':
                self.progress('A stale Helper PID file was found; no Helper process is running. Continuing installation without deleting state files.')

    def helper_state(self, timeout=None):
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
    # Older BusyBox grep ignores -x with -F, matching this SSH script itself.
    # Use anchored basic expressions and escape the literal path dots instead.
    if printf '%s\n' "$cytv_args" | grep -e '^com[.]local[.]nativehome$' -e '^HELPER_ROOT/native[.]js$' -e '^HELPER_ROOT/relay$' >/dev/null 2>&1; then
        printf CYTV_HELPER_ACTIVE; exit 0
    else
        cytv_match=$?
        if [ "$cytv_match" != 1 ]; then cytv_state=CYTV_HELPER_UNCERTAIN; fi
    fi
done
printf '%s' "$cytv_state"
'''.replace('HELPER_STATE', HELPER_STATE).replace('HELPER_ROOT', (BASE + '/applications/' + HELPER).replace('.', '[.]'))
        result = self.remote.run(script, **({'timeout': timeout} if timeout is not None else {})).strip()
        return {'CYTV_HELPER_IDLE': 'stopped', 'CYTV_HELPER_STALE': 'stale',
                'CYTV_HELPER_ACTIVE': 'running'}.get(result, 'uncertain')

    def select_graphics(self):
        """Resolve only new installs; retained recovery keeps its original bytes."""
        if hasattr(self, '_graphics_paths'):
            return
        try:
            selected = graphics.resolution(self.remote.luna(graphics.URI, {'keys': ['UHD']}))
        except (OSError, RuntimeError, ValueError, TypeError):
            raise UserError('TV graphics capability could not be verified. Installation has not started.', reason_code='graphics-unverified') from None
        variants = {'1920x1080': {'launcher': 'launcher.ipk', 'root': 'root'},
                    '1280x720': {'launcher': 'launcher-720p.ipk', 'root': 'root-720p'}}
        try:
            if self.manifest.get('graphics') != variants:
                raise ValueError('Missing graphics variants')
            paths = variants[selected]
            def verified(name):
                path = self.payload / package.safe_name(name)
                # PyInstaller may alias the payload root in macOS bundles;
                # only links within that root are untrusted package members.
                if path.is_symlink() or any((self.payload / parent).is_symlink() for parent in PurePosixPath(name).parents if str(parent) != '.'):
                    raise ValueError('Indirect graphics payload')
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != self.manifest['files'][name]:
                    raise ValueError('Graphics payload mismatch')
                return raw
            if self.profile['edition'] == 'root':
                directory = paths['root']
                bundle = json.loads(verified(directory + '/bundle.json'))
                for name, digest in bundle['files'].items():
                    if hashlib.sha256(verified(directory + '/' + package.safe_name(name))).hexdigest() != digest:
                        raise ValueError('Graphics bundle mismatch')
                raw = verified(directory + '/' + package.safe_name(bundle['package']))
                release = json.loads(verified(directory + '/release.json'))
                app, version = package.ROOT_APP, release['version']
            else:
                raw = verified(paths['launcher'])
                app, version = HOME, self.manifest['home_version']
            info = json.loads(package.data_files(raw)['usr/palm/applications/' + app + '/appinfo.json'])
            if info.get('id') != app or info.get('version') != version or info.get('resolution') != selected:
                raise ValueError('Graphics application mismatch')
        except (OSError, ValueError, KeyError, TypeError):
            raise UserError('Embedded graphics packages are missing or invalid. Use a complete installer build. Installation has not started.') from None
        self._graphics_paths = paths
        self.tv_info['graphics_resolution'] = selected

    def install(self, inventory, ssap_key=None, migrate=False, reinstall=None):
        # All local validation precedes the durable mutation receipt.
        if getattr(self, 'tv_name', None) is not None:
            self.tv_name = package.normalize_tv_name(self.tv_name)
        pending = self.store.pending(self.profile)
        replace_activation = (reinstall == 'installed' and self.profile['edition'] == 'root'
                              and pending and pending.get('action') == 'activate-root'
                              and pending.get('home_backend') != 'c1-native-gate')
        if pending and not replace_activation:
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation')
        if reinstall and migrate:
            raise UserError('Reinstallation does not support --migrate-home. Omit it to read a fresh TV inventory before replacing Root.')
        if not migrate:
            package.inventory_script(inventory)
        if reinstall not in (None, 'installed', 'removed') or (reinstall and self.profile['edition'] != 'root'):
            raise UserError('Invalid reinstallation request.')
        self.outcome.begin()
        self.select_graphics()
        if self.profile['edition']=='root':
            self.preflight(install=not reinstall, home_interfaces=True)
        else:
            self.preflight(install=not reinstall)
        if self.profile['edition'] == 'root':
            return self.install_root(inventory, migrate, reinstall)
        if not ssap_key:
            raise ValueError('Remote-control pairing is required for No-root.')
        launcher, _ = package.personalize((self.payload / self._graphics_paths['launcher']).read_bytes(), HOME, inventory,
                                         tv_name=getattr(self, 'tv_name', None))
        helper = (self.payload / self.manifest['helper']).read_bytes()
        expected = {}
        for data in (helper, launcher):
            for name, content in package.data_files(data).items():
                if '/state/' not in name:
                    expected[BASE.removesuffix('/usr/palm') + '/' + name] = hashlib.sha256(content).hexdigest()
        key_data = json.dumps({'key': ssap_key}).encode()
        ids = [app['id'] for app in inventory['apps'] if app['id'] not in (HOME, HELPER, 'com.webos.app.home', package.ROOT_APP)]
        apps_data = json.dumps(ids).encode()
        expected[HELPER_STATE + '/ssap-key.json'] = hashlib.sha256(key_data).hexdigest()
        expected[HELPER_STATE + '/apps.json'] = hashlib.sha256(apps_data).hexdigest()
        storage.install(self.remote, {'helper.ipk': helper, 'launcher.ipk': launcher}, self.progress,
                        root=self.profile.get('connection') == 'root-ssh')
        from . import no_root_observer
        pending = no_root_observer.begin(self, 'install', {'helper.ipk': helper, 'launcher.ipk': launcher},
            {HOME: self.manifest['home_version'], HELPER: self.manifest['helper_version']}, expected,
            {'ssap-key.json': key_data, 'apps.json': apps_data})
        return self.continue_no_root(pending)

    def continue_no_root(self, expected_pending):
        from .no_root_observer import continue_operation
        return continue_operation(self, expected_pending)

    def has_root_updater(self):
        condition=' || '.join('[ -e '+p+' ] || [ -L '+p+' ]' for p in root_updater_paths())
        return bool(self.remote.run('if '+condition+'; then printf CYTV_EXISTING_UPDATER; fi').strip())

    def install_root(self, inventory, migrate, reinstall=None):
        if self.tv_info.get('home_backend') == 'c1-native-gate':
            from .root_gate import install
            return install(self, inventory, migrate, reinstall)
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
        with tempfile.TemporaryDirectory(prefix='cytv-root-') as tmp:
            bundle = Path(tmp).resolve() / 'root'
            shutil.copytree(self.payload / self._graphics_paths['root'], bundle)
            if not migrate or getattr(self, 'tv_name', None) is not None:
                package.personalize_root(bundle, inventory if not migrate else None, tv_name=getattr(self, 'tv_name', None))
            manifest = json.loads((bundle / 'bundle.json').read_text())
            for name, digest in manifest['files'].items():
                if hashlib.sha256((bundle / package.safe_name(name)).read_bytes()).hexdigest() != digest:
                    raise ValueError('Prepared Root bundle integrity mismatch')
            package.verify_root_rollback_format((bundle / package.safe_name(manifest['package'])).read_bytes())
            release_sha = hashlib.sha256((bundle / 'release.json').read_bytes()).hexdigest()
            bundle_sha = hashlib.sha256((bundle / 'bundle.json').read_bytes()).hexdigest()
            storage.install(self.remote, {str(path.relative_to(bundle)): path.read_bytes()
                            for path in bundle.rglob('*') if path.is_file()} |
                            {'updater/' + str(path.relative_to(updater)): path.read_bytes()
                             for path in updater.rglob('*') if path.is_file()}, self.progress, root=True)
            if reinstall:
                self.prepare_root_reinstall()
                self.preflight(install=True, home_interfaces=True)
            operation=uuid.uuid4().hex
            self.store.begin(self.profile,'install',release_sha=release_sha,bundle_sha=bundle_sha,migrate=migrate,
                             requires_updater=True,product_operation=operation,stage='coordinator-upload',
                             recovery_protocol='root-final-readback-v1')
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
            self.outcome.packages_verified()
            updates_ready = self.profile.get('root_variant') != 'node012-beta'
            # This receipt proves recovery infrastructure readiness, not OTA eligibility.
            self.store.checkpoint(self.profile, action='activate-root', stage='stop-helper', updates_ready=True)
            self.activate_root()
            return dict(result, home_changed=True, launch_requested=True, updates_ready=updates_ready,
                        beta=not updates_ready)

    def _root_setup_check(self, name, state):
        detail = self.tv_info.get('root_setup_recovery')
        if detail is not None:
            detail['checks'][name] = state
            if state == 'pending': detail['reason'] = 'pending'
            elif state == 'unverified': detail['reason'] = name+'-unverified'

    def verify_root_updater(self, baseline_sha):
        script = """
import errno, hashlib, sys
from pathlib import Path
step = 'updater'
try:
    sys.path.insert(0, '/var/lib/clean-your-tv-root-updater/code')
    from updater.device import Device, STATE
    from updater.store import Store
    from updater.package import safe_bytes, inspect_package
    store = Store(STATE)
    Device(store).integrity()
    if store.read('bootstrap').get('phase') != 'complete': raise ValueError('Incomplete updater setup')
    step = 'rollback-baseline'
    current = store.read('current')
    if current.get('sha256') != sys.argv[1]: raise ValueError('Rollback baseline mismatch')
    raw = safe_bytes(STATE / 'cache' / (sys.argv[1] + '.ipk'), uid=0)
    if hashlib.sha256(raw).hexdigest() != sys.argv[1]: raise ValueError('Rollback cache mismatch')
    inspect_package(raw, current)
except Exception as error:
    # Preserve transport storage-full detection for real filesystem exhaustion.
    if isinstance(error, OSError) and error.errno in (errno.ENOSPC, errno.EDQUOT): raise
    # A fixed failed-boundary marker is evidence only; success still needs every check.
    print('CYTV_UPDATER_UNVERIFIED '+step)
else:
    print('CYTV_UPDATER_VERIFIED')
"""
        command = self._python_command([self._python(), '-c', script, baseline_sha])
        self._root_setup_check('updater', 'pending')
        self._root_setup_check('rollback-baseline', 'pending')
        raw = self.remote.run(command, timeout=60).strip()
        if raw != 'CYTV_UPDATER_VERIFIED':
            if raw == 'CYTV_UPDATER_UNVERIFIED updater':
                self._root_setup_check('rollback-baseline', 'not-run')
                self._root_setup_check('updater', 'unverified')
            elif raw == 'CYTV_UPDATER_UNVERIFIED rollback-baseline':
                self._root_setup_check('updater', 'verified')
                self._root_setup_check('rollback-baseline', 'unverified')
            else:
                self._root_setup_check('updater', 'unverified')
            raise UserError('Root updater recovery verification failed. Keep recovery state and run cytv status.')
        self._root_setup_check('updater', 'verified')
        self._root_setup_check('rollback-baseline', 'verified')
        self._root_setup_check('updater-transaction', 'pending')
        reply = self.remote.luna(UPDATER_APP + '.service/status', {}, app_id=package.ROOT_APP, timeout=110)
        transaction=reply.get('result')
        healthy=(transaction is None or (isinstance(transaction,dict) and transaction.get('schema')==1 and isinstance(transaction.get('id'),str) and re.fullmatch('[a-f0-9]{32}',transaction['id']) and transaction.get('phase') in ('complete','rolled-back','aborted') and transaction.get('homeResumePhase')==transaction.get('phase')))
        if reply.get('returnValue') is not True or 'result' not in reply or not healthy:
            self._root_setup_check('updater-transaction', 'unverified')
            raise UserError('Root updater service is not ready. Keep recovery state and run cytv status.')
        self._root_setup_check('updater-transaction', 'verified')

    @staticmethod
    def root_active(result):
        if result.get('backend') == 'c1-native-gate':
            from .root_gate import native_proof
            effective = result.get('effective', {})
            intent = result.get('intent') or {}
            return (result.get('recovery', {}).get('integrity_verified') is True
                    and intent.get('enabled') is True and intent.get('phase') == 'active'
                    and effective.get('backend') == 'c1-native-gate' and effective.get('profiles') is None
                    and native_proof(result) is not None
                    and effective.get('state') == 'armed'
                    and (effective.get('mounted') is True or effective.get('routing') == 'compositor-keyfilter-v1')
                    and effective.get('healthy') is True and effective.get('stock_verified') is False
                    and effective.get('stopped') is False
                    and isinstance(effective.get('token'), str) and effective['token'] == intent.get('token')
                    and re.fullmatch('[a-f0-9]{32}', effective['token']) is not None
                    and type(effective.get('guardian_pid')) is int and effective['guardian_pid'] > 1)
        return (result.get('recovery', {}).get('integrity_verified') is True
                and (result.get('intent') or {}).get('enabled') is True
                and (result.get('intent') or {}).get('phase') == 'active'
                and result.get('guardian_active') is True
                and result.get('effective', {}).get('sam_home') == package.ROOT_APP
                and (result.get('effective', {}).get('profiles') or {}).get('idleApp', {}).get('appId') == package.ROOT_APP
                and (result.get('effective', {}).get('profiles') or {}).get('defaultApps', {}).get('categories', {}).get('home') == package.ROOT_APP)

    def stop_root_helper_for_activation(self):
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

    def recover_failed_activation(self):
        """Compensate our activation through the ownership-checked restore path.

        Keep the original stage/error, including when the compensation fails.
        Never repeat enable/launch or acknowledge the installation as complete.
        """
        pending = self.store.pending(self.profile)
        if (self.profile['edition'] != 'root' or not pending or 'previous' in pending
                or pending.get('action') not in ('install', 'activate-root')
                or pending.get('stage') not in ('enable', 'launch', 'launch-submitting')):
            return False
        self.store.checkpoint(self.profile, activation_restore_pending=True, activation_restore='unverified')
        self.progress('Restoring LG Home…')
        for attempt in range(2):
            try:
                current = self.root_action('status').get('result', {})
                if current.get('recovery', {}).get('integrity_verified') is not True:
                    return False
                if not self.root_setup_inactive(current):
                    self.root_action('restore')
                    if not self.root_setup_inactive(self.root_action('status').get('result', {})):
                        return False
                self.store.checkpoint(self.profile, activation_restore_pending=False, activation_restore='verified')
                self.progress('LG Home is restored.')
                return True
            except Exception as error:
                from .errors import connection_interrupted
                reconnect = getattr(self, 'reconnect', None)
                if attempt or not reconnect or not connection_interrupted(error):
                    return False
                try:
                    self.remote = reconnect()
                except Exception:
                    return False
        return False

    def activate_root(self):
        pending=self.store.pending(self.profile) or {}
        if pending.get('home_backend') == 'c1-native-gate':
            from .root_activation import activate
            return activate(self)
        if pending.get('product_operation'):
            current=self.product_action('status',pending['product_operation'],verify_current=True)
            if current.get('current') is not True:
                raise UserError('Root setup could not be verified for continuation. Recovery data was kept.')
        from .root_runtime_contract import verify
        verify(self)
        self.progress('Checking Root recovery…')
        if self.root_action('status').get('result', {}).get('recovery', {}).get('integrity_verified') is not True:
            raise UserError('Root is installed, but recovery could not be verified. Run cytv status; activation has not started.')
        self.stop_root_helper_for_activation()
        self.store.checkpoint(self.profile, stage='enable')
        self.progress('Turning on Root Home control…')
        try:
            self.root_action('enable')
            self.store.checkpoint(self.profile, stage='launch')
            self.progress('Opening Clean Your TV Home…')
            self.outcome.launch_submitted()
            self.remote.luna('com.webos.applicationManager/launch', {'id': package.ROOT_APP})
            self.outcome.launch_accepted()
            self.store.checkpoint(self.profile, launch_requested=True)
            if not self.root_active(self.root_action('status').get('result', {})):
                raise UserError('Root activation or recovery readback was not confirmed. Run cytv status or cytv restore. Recovery data was kept.')
            self.outcome.startup_observed('root-state-verified')
        except (OSError, RuntimeError, ValueError) as error:
            self.outcome.startup_observed('unverified')
            try:
                self.recover_failed_activation()
            except Exception:
                pass  # A failed recovery checkpoint must not replace the first error.
            if isinstance(error, UserError):
                raise  # Preserve sanitized SSH/Luna evidence and the pending stage.
            raise UserError('Root is installed, but activation or opening Home could not be confirmed. Run cytv status to inspect it, or cytv restore to return to LG Home. Recovery data was kept; do not reinstall blindly.') from None
        self.store.finish(self.profile)

    def stop_helper(self):
        apps = {app['id'] for app in self.installed_apps()}
        if HELPER in apps:
            try:
                self.remote.luna('com.local.nativehome.service/disable', {})
            except TVRejected as error:
                if (self.profile['edition'] != 'no-root' or error.luna['operation'] != 'helper-disable'
                        or error.luna['error_code'] != -1):
                    raise
                from .helper_stop import PROGRAM
                if self.remote.run('/usr/bin/node', data=PROGRAM.encode(), timeout=15).strip() != 'CYTV_HELPER_STOP_REQUESTED':
                    raise UserError('Home Helper stop could not be verified. Keep recovery state and run cytv status.')
                for attempt in range(16):
                    if self.helper_state() in ('stopped', 'stale'):
                        return
                    if attempt < 15:
                        time.sleep(1)
                raise UserError('Home Helper stop could not be verified. Keep recovery state and run cytv status.')
        self.remote.run(
            'if [ -f ' + HELPER_STATE + '/controller.pid ]; then '
            'printf \'{"cmd":"stop"}\' > ' + HELPER_STATE + '/control.json; '
            'n=0; while [ -e ' + HELPER_STATE + '/controller.pid ]; do '
            'n=$((n+1)); [ "$n" -le 15 ] || exit 1; sleep 1; done; fi', timeout=25)

    def root_inventory(self, fallback):
        """Use the existing fixed Root catalog reader; Root needs no SSAP key."""
        import base64
        if self.profile['edition']!='root':raise ValueError('Root inventory requires Root')
        observed=self.tv_info['root_inventory']={'applications':'unknown','inputs':'unknown'}
        self.tv_info.pop('root_inventory_failures',None)
        try:
            from .root_catalog import capture
            replies,failures=capture(self.remote)
            if failures:self.tv_info['root_inventory_failures']=failures
            module=self.coordinator_code()+'/app-inventory.js'
            # Reuse the shipped validation/icon reader with captured SSH replies.
            # Supplying its I/O provider avoids even loading Node child_process.
            captured=json.dumps({'replies':replies,'failures':failures},separators=(',',':'))
            program=('var reader=require('+json.dumps(module)+');'
                     'var captured=JSON.parse('+json.dumps(captured)+'),failures=captured.failures;'
                     'function reply(file,args,options,done){'
                     'var index=args[2]==="luna://com.webos.applicationManager/listApps"?0:'
                     'args[2]==="luna://com.webos.service.eim/getAllInputStatus"?1:-1;'
                     'if(file!=="/usr/bin/luna-send"||index<0)throw Error("Invalid catalog read");'
                     'done(null,JSON.stringify(captured.replies[index]));}'
                     'function unavailable(kind){return function(error){'
                     'failures[kind]=error&&error.inventory||{reason:"unknown"};return null;};}'
                     'Promise.all([captured.replies[0]===null?Promise.resolve(null):reader(reply).catch(unavailable("applications")),'
                     'captured.replies[1]===null?Promise.resolve(null):reader.inputs(reply).catch(unavailable("inputs"))])'
                     '.then(function(value){value.push(failures);process.stdout.write(JSON.stringify(value));},function(){process.exit(1);});').encode()
            value=json.loads(self.remote.run('/usr/bin/node',data=program,timeout=30))
            if not isinstance(value,list) or len(value)!=3 or not isinstance(value[2],dict):raise ValueError('Invalid Root inventory')
            failures=diagnostics.context.inventory_failures(value[2])
            if failures:self.tv_info['root_inventory_failures']=failures
            observed['applications']='unavailable' if value[0] is None else 'unknown'
            observed['inputs']=('unavailable' if value[1] is None else 'read'
                if isinstance(value[1],dict) and value[1].get('returnValue') is True
                and isinstance(value[1].get('devices'),list) and len(value[1]['devices'])<=100 else 'invalid')
            if not isinstance(value[0],list) or len(value[0])>200:
                if value[0] is not None:observed['applications']='invalid'
                raise ValueError('Invalid Root inventory')
            if observed['inputs']=='invalid':raise ValueError('Invalid Root inputs')
            observed['applications']='invalid'
            def text(value):
                return isinstance(value,str) and bool(value) and '\0' not in value and len(value.encode('utf-8'))<=256
            apps=[];seen=set()
            for app in value[0]:
                if not isinstance(app,dict):raise ValueError('Invalid Root application')
                if app.get('hidden'):continue
                if not text(app.get('id')) or not text(app.get('title')):raise ValueError('Invalid Root application')
                if app['id'] in seen:continue
                seen.add(app['id'])
                icon=app.get('icon') or 'data:image/png;base64,'+base64.b64encode(fallback).decode('ascii')
                if not isinstance(icon,str) or len(icon)>45000 or not icon.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):raise ValueError('Invalid Root icon')
                item={key:app[key] for key in ('id','title')};item['icon']=icon
                if isinstance(app.get('iconColor'),str) and re.fullmatch('#[a-fA-F0-9]{6}',app['iconColor']):item['iconColor']=app['iconColor']
                apps.append(item)
            inputs=[];seen=set()
            for device in value[1]['devices'] if value[1] is not None else []:
                if not isinstance(device,dict) or not text(device.get('appId')) or device['appId'] in seen:continue
                label=next((device[k] for k in ('label','deviceName','spdProductDescription','id','appId') if text(device.get(k))),device['appId'])
                seen.add(device['appId']);inputs.append({'appId':device['appId'],'label':label})
            result={'apps':apps,'inputs':inputs};package.inventory_script(result)
            observed['applications']='read'
            if observed['inputs']=='unavailable':
                self.progress('Warning: TV inputs could not be read. Continuing with applications only.')
            return result
        except (ConnectionError,TimeoutError,EOFError) as error:
            raise UserError('Connection to the TV was interrupted. Check the connection and try again.',reason_code='connection-interrupted') from error
        except (OSError,ValueError,TypeError,KeyError,TVCommandError) as error:
            raise UserError('Could not read installed applications.',reason_code='inventory-unavailable') from error

    def installed_apps(self, timeout=30):
        reply = self.remote.luna('com.webos.applicationManager/dev/listApps', {}, timeout=timeout)
        apps = reply.get('apps')
        if not isinstance(apps, list):
            raise UserError('Could not read installed applications.', reason_code='inventory-unavailable')
        return apps

    def version_summary(self):
        observed = self.installed_apps()
        self.tv_info['components'] = diagnostics.context.status_summary({'device': {'apps': observed}}).get('components', {})
        apps = {app['id']: app for app in observed}
        if self.profile['edition'] == 'root':
            if self.tv_info.get('home_backend') == 'c1-native-gate':
                variant = self.manifest['root_backends']['c1-native-gate']['graphics'][self.tv_info['graphics_resolution']]
                root = json.loads((self.payload / package.safe_name(variant) / 'release.json').read_text())['version']
                targets = [(package.ROOT_APP, 'Root (experimental)' if self.tv_info.get('home_backend_schema') == 3 else 'Root (C1 Beta)', root)]
            else:
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
            rows.append(f'{i18n.translate(name)}: {current} → {target} ({i18n.translate(action)})')
        return rows

    def verify_installed(self):
        # Called only after both live install streams confirmed completion.
        # SAM's catalog can lag that reply; retry reads, never package requests.
        deadline = time.monotonic() + 10
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            observed = self.installed_apps(timeout=remaining)
            self.tv_info['components'] = diagnostics.context.status_summary({'device': {'apps': observed}}).get('components', {})
            apps = {app['id']: app for app in observed}
            if time.monotonic() >= deadline:
                break
            if all(apps.get(app, {}).get('version') == self.manifest[key]
                   for app, key in ((HOME, 'home_version'), (HELPER, 'helper_version'))):
                return
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(1, remaining))
        raise UserError('Installed version did not match the package. Run cytv status; do not retry blindly.', reason_code='version-mismatch')

    def status(self):
        diagnostics.context.collect_node_version(self.remote, self.tv_info)
        pending=self.store.pending(self.profile)
        if pending and pending.get('recovery_protocol')=='clean-removal-v1':
            return self.observe_recovery()
        result=self._status()
        self.tv_info['status']=result
        if (self.profile['edition']=='root'
                and result.get('deployment_stage')=='installed-recovery-only'):
            self.collect_root_diagnostics()
        return result

    def observe_recovery(self):
        """Read current proofs without clearing or archiving the host receipt.

        Root checks can stage verified support code, as explained by the UI;
        they never submit packages or activate Home here.
        """
        from .recovery_state import assess
        self.tv_info.pop('root_setup_recovery', None)
        pending = self.store.pending(self.profile)
        if pending and pending.get('recovery_protocol')=='clean-removal-v1':
            from .recovery_state import removal_summary
            result={'device':{},'pending':pending,'assessment':assess(self.profile,pending),
                    'removal':removal_summary(pending),'can_resume_root_setup':False}
            self.tv_info['status']=result
            return result
        initial = assess(self.profile, pending)
        result = ({'device': {}, 'pending': pending, 'can_resume_root_setup': False}
                  if initial['reason'] in ('unsupported-receipt', 'inherited-operation')
                  else self._status(reconcile=False, trusted_recovery=pending is not None and
                                    pending.get('recovery_protocol') == 'root-final-readback-v1'))
        result['assessment'] = assess(self.profile, self.store.pending(self.profile), result)
        self.tv_info['status'] = result
        return result

    def inspect_root_product(self, expected_pending):
        """Explicit trusted support-code inspection of one original installation."""
        pending=self.store.pending(self.profile)
        if (pending != expected_pending or not pending or 'previous' in pending
                or self.profile['edition']!='root' or pending.get('action')!='install'
                or not re.fullmatch('[a-f0-9]{32}',pending.get('product_operation',''))):
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        result=self._status(reconcile=False, trusted_recovery=True)
        if self.store.pending(self.profile)!=pending:
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        from .recovery_state import assess
        result['assessment']=assess(self.profile,pending,result)
        self.tv_info['status']=result
        return result

    def _save_product_baseline(self, pending, observation):
        event=observation.get('device',{}).get('product',{})
        proof=event.get('result',{})
        if (self.store.pending(self.profile)!=pending or event.get('operation')!=pending.get('product_operation')
                or event.get('state')!='complete' or event.get('current') is not True
                or observation.get('can_resume_root_setup') is not True
                or not re.fullmatch('[a-f0-9]{64}',proof.get('baseline_sha',''))):
            raise UserError('Root setup could not be verified for continuation. Recovery data was kept.')
        from .state import private_write
        history=self.store.recovery(self.profile,'continue-root-product')
        private_write(history,json.dumps({'action':'continue-root-product','previous':pending}).encode())
        self.store.checkpoint(self.profile,stage='verify',baseline_sha=proof['baseline_sha'],requires_updater=True)

    def continue_root_product(self, expected_pending):
        result=self.inspect_root_product(expected_pending)
        event=result['device']['product']
        if event.get('can_resume') is not True or event.get('resume_reason')!='original_final_readback_verified':
            raise UserError('Root continuation could not be verified. Recovery data was kept.', reason_code='pending-operation')
        operation=expected_pending['product_operation']
        reply=self.product_action('install',operation,resume=True)
        deadline=time.monotonic()+120
        while reply['state']=='pending' and time.monotonic()<deadline:
            time.sleep(1)
            reply=self.product_action('status',operation,verify_current=True,trusted_recovery=True)
        result=self.inspect_root_product(expected_pending)
        self._save_product_baseline(expected_pending,result)
        return result

    def inspect_root_cancellation(self, expected_pending):
        from .root_install_recovery import invoke
        if (self.profile['edition']!='root' or not isinstance(expected_pending,dict)
                or expected_pending.get('action')!='install'
                or self.store.pending(self.profile)!=expected_pending or 'previous' in expected_pending):
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        proof=invoke(self,'inspect',expected_pending)
        if self.store.pending(self.profile)!=expected_pending:
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        from .recovery_state import assess
        status=self.tv_info.setdefault('status',{})
        status['cancellation']=proof
        status['assessment']=assess(self.profile,expected_pending,status)
        return proof

    def cancel_root_product(self, expected_pending, expected_proof):
        from .root_install_recovery import invoke
        proof=self.inspect_root_cancellation(expected_pending)
        if (proof!=expected_proof or proof.get('state') not in
                ('admissible','admitted','remove-observed','cancellation-terminal-pending','cancelled-and-removed')):
            raise UserError('Root cancellation could not be verified. Recovery data was kept.', reason_code='pending-operation')
        if proof['state']!='cancelled-and-removed':
            invoke(self,'remove',expected_pending,proof)
        disposition=self.inspect_root_cancellation(expected_pending)
        if (disposition.get('state')!='cancelled-and-removed' or disposition.get('lease_terminal') is not True
                or disposition.get('proof_sha256')!=proof.get('proof_sha256')
                or disposition.get('candidate_sha256')!=proof.get('candidate_sha256')
                or disposition.get('home_changed') is not False):
            raise UserError('Root cancellation could not be verified. Recovery data was kept.', reason_code='pending-operation')
        from .state import private_write
        history=self.store.recovery(self.profile,'cancelled-root-install')
        private_write(history,json.dumps({'action':'cancelled-root-install','stage':'verified',
                                        'previous':expected_pending,'disposition':disposition}).encode())
        self.store.finish(self.profile)
        return disposition

    def reconcile_recovery(self, expected_pending):
        """Explicit local completion; fresh backend evidence remains authority."""
        previous = self.store.pending(self.profile)
        if not previous or previous != expected_pending:
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        result = self.observe_recovery()
        reason = result.get('reconciliation')
        if (reason not in ('product-removal-verified', 'root-activation-verified')
                or self.store.pending(self.profile) != previous):
            raise UserError('Recovery could not be verified. Recovery data was kept.', reason_code='pending-operation')
        from .state import private_write
        receipt = self.store.recovery(self.profile, 'reconcile-recovery')
        private_write(receipt, json.dumps({'action': 'reconcile-recovery', 'stage': 'verified',
            'reason': reason, 'previous': previous}).encode())
        self.store.finish(self.profile)
        return {'reconciled': reason}

    def _status(self, reconcile=True, trusted_recovery=False):
        self.tv_info.pop('root_setup_recovery', None)
        pending = self.store.pending(self.profile)
        restoring = bool(pending and pending.get('activation_restore_pending') is True)
        reconcile = reconcile and not restoring
        if pending and pending.get('recovery_protocol') == 'no-root-original-stream-v1':
            from .no_root_observer import observe
            return observe(self, pending)
        reconciled = None
        reconciliation = None
        can_resume = False
        if (self.profile['edition']=='root' and pending and pending.get('action')=='install'
                and pending.get('stage')=='coordinator-submitted' and not trusted_recovery):
            # A failed submission/status (including SSH 127) does not authorize
            # staging a replacement driver or executing retained binding code.
            from .root_passive import collect
            passive=collect(self.remote,pending.get('product_operation'),pending)
            event=dict(operation=pending['product_operation'],action='install',state='recovery_required',
                       stage='blocked',code='operation_requires_recovery',can_resume=False,
                       resume_reason='recovery_evidence_required',passive=passive)
            return dict(device={'product':event},pending=pending,reconciled=None,can_resume_root_setup=False)
        if not pending and self.profile['edition']=='root' and not self.native_root_present():
            try:
                inspected=self.product_action('inspect')
                active=inspected.get('active_operation')
                if isinstance(active,dict):
                    return {'device':{'product':active},'pending':None,'reconciled':None,'can_resume_root_setup':False,'active_operation':active.get('operation')}
            except (OSError,RuntimeError,ValueError,KeyError):pass
        if pending and pending.get('product_operation') and pending.get('action') in ('install','uninstall'):
            event=self.product_action('status',pending['product_operation'],verify_current=True,
                                      **({'trusted_recovery':True} if trusted_recovery else {}))
            complete=event['state']=='complete' and event.get('current') is True
            can_resume=False
            if complete and pending['action']=='install':
                event=dict(event)
                reason='current-package-files-unverified'
                try:
                    proof=event['result']
                    if (proof.get('installed')!=package.ROOT_APP or proof.get('home_changed') is not False
                            or proof.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}',proof.get('baseline_sha',''))):
                        raise ValueError('current_product_proof_required')
                    device=self.root_action('status').get('result',{})
                    reason='stock-routing-unverified'
                    if self.root_setup_inactive(device):
                        reason='updater-baseline-unverified'
                        self.verify_root_updater(event['result']['baseline_sha']);can_resume=True
                    elif (device.get('effective',{}).get('sam_home')=='com.webos.app.home'
                          and device.get('effective',{}).get('profiles',{}).get('defaultApps',{}).get('categories',{}).get('home')=='com.webos.app.home'
                          and device.get('effective',{}).get('profiles',{}).get('idleApp',{}).get('appId')=='com.webos.app.home'):
                        reason='intent-guardian-unverified'
                except (RuntimeError,ValueError,KeyError,TypeError):pass
                if not can_resume:event['setup_reason']=reason
            if complete and pending['action']=='uninstall':
                reconciliation='product-removal-verified'
                if reconcile:
                    self.store.finish(self.profile)
                    reconciled=reconciliation
            return {'device':{'product':event},'pending':self.store.pending(self.profile),'reconciled':reconciled,
                    'reconciliation':reconciliation, 'can_resume_root_setup':can_resume and not restoring}
        if pending and pending.get('action') == 'enable-system-updates':
            report = self.system_updater_cleanup('status')
            if reconcile and report.get('present') is False:
                # The root helper also proves no owned bootstrap process can
                # still create state or submit an installer operation.
                self.store.finish(self.profile)
                reconciled = 'system-updater-not-started'
            elif reconcile and report.get('present') is True and report.get('bootstrap_complete') is True and report.get('disabled') is False:
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
            if stage=='cancellation-admitted':
                installation=self.root_installation()
                if installation.get('clean_removal_verified') is True and installation.get('can_install') is True:
                    return {'device':{'installation':installation},'deployment_stage':'verified-clean',
                            'pending':self.store.pending(self.profile),'reconciled':None,
                            'can_resume_root_setup':False,'reconciliation':None}
            result = {'deployment_stage': stage}
            if reconcile and pending and pending['action'] == 'archive-root-state':
                readback = self.root_archive('reconcile', pending.get('archive'), pending.get('identity'))
                if readback.get('state') in ('archived', 'not-archived'):
                    self.store.finish(self.profile)
                    pending = None
                    reconciled = 'root-archive-' + readback['state']
            if stage == 'installed-recovery-only':
                result = self.root_action('status')
                if (pending and not restoring and pending['action'] == 'activate-root'
                        and self.root_active(result.get('result', {}))
                        and (reconcile or self.root_files_match(pending))
                        and (pending.get('home_backend') != 'c1-native-gate' or
                             result.get('result', {}).get('backend') == 'c1-native-gate'
                             and result.get('result', {}).get('effective', {}).get('token') == pending.get('home_token'))):
                    reconciliation = 'root-activation-verified'
                    if reconcile:
                        self.store.finish(self.profile)
                        reconciled = ('root-activation-verified' if pending.get('launch_requested') is True
                                      else 'root-activation-verified; screen launch unconfirmed, press Home to open it')
                can_resume = self.can_resume_root_setup(pending, result.get('result', {}))
                if reconcile and self.recover_unstarted_root_updater(pending, result.get('result', {})):
                    pending = None
                    reconciled = 'updater-not-started; recovery verified; reinstallation available'
                if (reconcile and pending and pending['action'] == 'install' and not pending.get('requires_updater')
                        and pending.get('home_backend') != 'c1-native-gate'
                        and result.get('result', {}).get('recovery', {}).get('integrity_verified') is True
                        and self.root_files_match(pending)):
                    self.store.finish(self.profile)
                    reconciled = 'root-installation-verified'
            elif stage == 'uninstalled-state-retained':
                self.verify_absent(package.ROOT_APP)
                if reconcile and pending and pending['action'] == 'uninstall' and not pending.get('full_project'):
                    self.store.finish(self.profile)
                    reconciled = 'root-removal-verified; TV evidence retained'
            elif (reconcile and stage == 'absent' and pending and pending['action'] == 'install'
                  and (pending.get('home_backend') != 'c1-native-gate' or pending.get('stage') == 'upload')):
                self.verify_absent(package.ROOT_APP)
                self.store.finish(self.profile)
                reconciled = 'no-root-installation-submitted'
        else:
            result = {'apps': [{k: app.get(k) for k in ('id', 'version')} for app in self.installed_apps() if app.get('id') in (HOME, HELPER)],
                      'helper_state': self.helper_state()}
            # App inventory and files describe a snapshot, not the outcome of an
            # interrupted installer transaction. No supported terminal readback
            # is established for these legacy receipts; retain them unchanged.
        return {'device': result, 'pending': self.store.pending(self.profile), 'reconciled': reconciled,
                'can_resume_root_setup': can_resume, 'reconciliation': reconciliation,
                **({'deployment_stage': stage} if self.profile['edition'] == 'root' else {})}

    @staticmethod
    def root_setup_inactive(device):
        try:
            effective = device.get('effective', {})
            if device.get('backend') == 'c1-native-gate':
                from .root_gate import stock_proof
                return (device.get('recovery', {}).get('integrity_verified') is True
                        and stock_proof(device)
                        and effective.get('backend') == 'c1-native-gate' and effective.get('profiles') is None
                        and effective.get('stock_verified') is True and effective.get('mounted') is False
                        and effective.get('healthy') is False and effective.get('guardian_pid') == 0
                        and (device.get('intent') or {}).get('enabled') is False)
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
        if pending and pending.get('activation_restore_pending') is True:
            if self.profile['edition'] == 'root' and pending.get('action') == 'activate-root':
                self.tv_info['root_setup_recovery'] = {'reason': 'restoration-pending',
                    'checks': dict.fromkeys(diagnostics.context.ROOT_SETUP_CHECKS, 'not-run')}
            return False
        if (self.profile['edition'] == 'root' and pending
                and pending.get('action') == 'activate-root'
                and pending.get('home_backend') != 'c1-native-gate'):
            return self.can_resume_root_activation(pending, device)
        if (self.profile['edition'] == 'root' and pending
                and pending.get('home_backend') == 'c1-native-gate'):
            return (pending.get('action') == 'install' and pending.get('stage') in ('setup', 'verify')
                    and device.get('backend') == 'c1-native-gate'
                    and self.root_setup_inactive(device) and self.root_files_match(pending))
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

    def can_resume_root_activation(self, pending, device):
        # Advice only: retain original short-circuit order and all admission predicates.
        detail = {'reason': 'not-run',
                  'checks': dict.fromkeys(diagnostics.context.ROOT_SETUP_CHECKS, 'not-run')}
        self.tv_info['root_setup_recovery'] = detail
        def check(name, verified):
            self._root_setup_check(name, 'verified' if verified else 'unverified')
            return verified
        if not check('receipt', not (pending.get('stage') not in ('stop-helper', 'enable', 'launch')
                or pending.get('requires_updater') is not True or pending.get('updates_ready') is not True
                or not isinstance(pending.get('baseline_sha'), str)
                or re.fullmatch('[a-f0-9]{64}', pending['baseline_sha']) is None)):
            return False
        if not check('stock-home', self.root_setup_inactive(device)):
            return False
        if not check('restored-journal', not (not isinstance(device.get('journal'), dict)
                or device['journal'].get('state') != 'restored'
                or (device.get('intent') or {}).get('phase') != 'disabled')):
            return False
        current = 'files'
        try:
            self._root_setup_check(current, 'pending')
            if not check(current, self.root_files_match(pending)): return False
            current = 'product'
            if pending.get('product_operation'):
                self._root_setup_check(current, 'pending')
                event = self.product_action('status', pending['product_operation'], verify_current=True)
                proof = event.get('result', {})
                if not check(current, not (event.get('state') != 'complete' or event.get('current') is not True
                        or proof.get('verified') is not True or proof.get('home_changed') is not False
                        or proof.get('baseline_sha') != pending['baseline_sha'])):
                    return False
            else:
                self._root_setup_check(current, 'not-required')
            current = 'updater'
            self._root_setup_check(current, 'pending')
            self.verify_root_updater(pending['baseline_sha'])
            # Successful return covers every verifier substep.
            for name in ('updater', 'rollback-baseline', 'updater-transaction'):
                self._root_setup_check(name, 'verified')
            current = 'binding'
            self._root_setup_check(current, 'pending')
            from .root_activation_recovery import SCRIPT
            if not check(current, self.remote.run(self._python_command([self._python(), '-c', SCRIPT])).strip() == 'CYTV_ACTIVATION_RECOVERABLE'):
                return False
            detail['reason'] = 'verified'
            return True
        except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError):
            if detail['reason'] == 'pending':
                # No classified reply: later remote substeps remain pending, not assumed absent.
                pending_checks = [name for name, state in detail['checks'].items() if state == 'pending']
                self._root_setup_check(pending_checks[0] if pending_checks else current, 'unverified')
            return False

    def finish_root_setup_disabled(self, expected_pending=None):
        """Explicitly cancel only verified restored activation, preserving its receipt."""
        previous=self.store.pending(self.profile)
        if expected_pending is not None and previous != expected_pending:
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        product=bool(previous and previous.get('action')=='install' and previous.get('product_operation'))
        result=self.inspect_root_product(previous) if product else self.observe_recovery()
        if (self.profile['edition']!='root' or not previous
                or self.store.pending(self.profile) != previous
                or (previous.get('action')!='activate-root' and not product)
                or previous.get('home_backend')=='c1-native-gate'
                or result.get('can_resume_root_setup') is not True):
            raise UserError('Root setup could not be verified for continuation. Recovery data was kept.')
        from .state import private_write
        receipt=self.store.recovery(self.profile,'finish-root-setup-disabled')
        private_write(receipt,json.dumps({'action':'finish-root-setup-disabled','stage':'verified',
            'home_changed':False,'previous':previous,
            'baseline_sha':result['device']['product']['result']['baseline_sha'] if product else previous['baseline_sha']}).encode())
        self.store.finish(self.profile)
        self.outcome.packages_verified()
        return {'home_changed':False,'updates_ready':self.profile.get('root_variant') != 'node012-beta','home_control':'disabled'}

    def resume_root_setup(self, expected_pending=None):
        # Revalidate after the user's confirmation; never resubmit package setup.
        previous = self.store.pending(self.profile)
        if expected_pending is not None and previous != expected_pending:
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
        self.outcome.begin()
        observation=(self.inspect_root_product(previous) if previous and previous.get('action')=='install'
                     and previous.get('product_operation') else self.observe_recovery())
        if (observation.get('can_resume_root_setup') is not True
                or self.store.pending(self.profile) != previous):
            raise UserError('Root setup could not be verified for continuation. Recovery data was kept.')
        if previous.get('action')=='install' and previous.get('product_operation'):
            self._save_product_baseline(previous,observation)
        previous = self.store.pending(self.profile)
        if previous and previous.get('action') == 'activate-root':
            from .state import private_write
            receipt = self.store.recovery(self.profile, 'resume-root-activation')
            private_write(receipt, json.dumps({'action': 'resume-root-activation', 'previous': previous}).encode())
        self.outcome.packages_verified()
        if (self.store.pending(self.profile) or {}).get('home_backend') == 'c1-native-gate':
            self.store.checkpoint(self.profile, action='activate-root', stage='stop-helper', updates_ready=False)
            launched = self.activate_root()
            return {'installed':package.ROOT_APP,'home_changed':True,'launch_requested':launched,
                    'updates_ready':False,'backend':'c1-native-gate','beta':True}
        self.store.checkpoint(self.profile, action='activate-root', stage='stop-helper', updates_ready=True)
        self.activate_root()
        return {'installed': package.ROOT_APP, 'home_changed': True, 'launch_requested': True,
                'updates_ready': self.profile.get('root_variant') != 'node012-beta'}

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

    def prepare_root_reinstall(self):
        if self.profile['edition'] != 'root':
            raise UserError('Reinstallation requires Root access.')
        self.progress('Restoring LG Home and removing the previous Clean Your TV installation…')
        result = self.uninstall_project()
        if (result.get('removed') is not True or result.get('verified_clean') is not True
                or result.get('restart_required') is True or self.store.pending(self.profile)):
            raise UserError('Removal is not finished. Continue removal in this installer before installing again.',
                            reason_code='pending-operation')
        # Full cleanup retires staged support and may remove private Python.
        # Fresh preflight must select/stage them again, never execute cached paths.
        for name in ('_coordinator_code', '_recovery_code', '_selected_python'):
            self.__dict__.pop(name, None)
        self.progress('Previous installation removed. Installing the packages and runtime in this installer…')

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
            try:
                installation=self.root_installation()
                if installation.get('clean_removal_verified') is True and installation.get('can_install') is True:
                    return {'restored':True,'already_removed':True}
            except UserError as error:
                if error.reason_code in ('restart-required','project-apps-remain'):raise
            except (OSError,ValueError,RuntimeError):
                pass
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

    def cleanup_legacy_permissions(self):
        from .legacy_permissions_remove import SCRIPT
        if self.remote.run(self._python_command([self._python(), '-c', SCRIPT]), timeout=30).strip() != 'CYTV_LEGACY_PERMISSIONS_REMOVED':
            raise UserError('Updater permissions removal could not be verified.')

    def verify_project_startup_removed(self):
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

    def verify_project_removed(self):
        self.verify_project_startup_removed()
        settings = self.remote.luna('com.webos.settingsservice/getSystemSettings', {'category': 'general', 'keys': ['defaultApps']})
        reply = self.remote.luna('com.webos.service.systemprofile/getProfiles', {'names': ['defaultApps', 'idleApp'], 'subscribe': False})
        try:
            profiles = reply['profiles']
            routes = (settings['settings']['defaultApps']['home'], profiles['defaultApps']['categories']['home'], profiles['idleApp']['appId'])
            if settings.get('returnValue') is not True or reply.get('returnValue') is not True or any(route != 'com.webos.app.home' for route in routes):
                raise ValueError('LG Home routing differs')
        except (KeyError, TypeError, ValueError):
            raise UserError('LG Home routing could not be verified. Keep recovery data.') from None

    def uninstall_project(self):
        pending=self.store.request_clean_removal(self.profile)
        return self.continue_clean_removal(pending)

    def continue_clean_removal(self, expected_pending):
        from .errors import connection_interrupted
        from .recovery_state import REMOVAL_REASONS
        # Root's verified full-project absence also completes blocked No-root
        # goals for this host. Never use an old receipt or cross-host proof.
        related = []
        if self.profile['edition'] == 'root':
            for profile in self.store.profiles():
                pending = self.store.pending(profile)
                if (profile['host'] == self.profile['host'] and profile['edition'] == 'no-root' and pending
                        and pending.get('recovery_protocol') == 'clean-removal-v1'
                        and pending.get('removal_reason') == 'root-access-required'):
                    related.append((profile, pending))
        reconnect = getattr(self, 'reconnect', None)
        lost = False
        for attempt in range(3):
            try:
                if lost:
                    self.remote = reconnect()
                result = self._continue_clean_removal(expected_pending)
                if result.get('removed') is True and result.get('verified_clean') is True and result.get('restart_required') is not True:
                    for profile, pending in related:
                        if self.store.pending(profile) == pending:
                            self.store.checkpoint(profile, stage='verified-clean', removal_reason='removal-verified',
                                result={'removed':True, 'verified_clean':True},
                                root_removal_operation=expected_pending['removal_operation'])
                            self.store.finish_clean_removal(profile)
                return result
            except Exception as error:
                lost = connection_interrupted(error)
                reason = 'connection-interrupted' if lost else getattr(error, 'reason_code', None)
                if (reason in REMOVAL_REASONS and self.store.pending(self.profile)
                        and (self.profile['edition'] == 'no-root' or reason in
                             ('connection-interrupted', 'root-access-required', 'root-worker-busy', 'removal-failed'))):
                    self.store.checkpoint(self.profile, removal_reason=reason)
                if not reconnect or attempt == 2 or not (lost or reason == 'root-worker-busy'):
                    raise
                try:
                    diagnostics.create_report(self.store, 'uninstall', self.profile, 'uninstall', error,
                                              getattr(self, 'tv_info', {}))
                except (OSError, ValueError, TypeError):
                    pass
                expected_pending = self.store.pending(self.profile)
                self.progress('Connecting to the TV…' if lost else 'Another Clean Your TV operation is still running. Wait for it to finish, then choose Try again.')
                sleep(attempt + 1)

    def _continue_clean_removal(self, expected_pending):
        """Explicit adapter dispatch; advisory summaries are never credentials."""
        pending=self.store.pending(self.profile)
        if pending!=expected_pending or not pending or pending.get('recovery_protocol')!='clean-removal-v1':
            raise UserError('Removal evidence changed. Recovery data was kept.',reason_code='pending-operation')
        if self.profile['edition']=='no-root':
            from .root_no_root_handoff import cleanup_target, cleanup_stamp
            if 'root_cleanup_lease' not in pending:
                from .no_root_cleanup import continue_removal
                try:return continue_removal(self,pending)
                except UserError as error:
                    if error.reason_code!='root-access-required' or self.profile.get('connection')!='root-ssh':raise
                    try:stamp=cleanup_target(self)
                    except (OSError,ValueError,RuntimeError):raise error from None
                    self.store.checkpoint(self.profile,root_cleanup_lease=stamp['lease'],
                        root_cleanup_operation=stamp['operation'],root_cleanup_node=stamp['node'])
                    pending=self.store.pending(self.profile)
            cleanup_stamp(dict(lease=pending['root_cleanup_lease'],operation=pending.get('root_cleanup_operation'),
                               node=pending.get('root_cleanup_node')))
        return self._continue_root_clean_removal(pending)

    def _continue_root_clean_removal(self, pending):
        if (self.profile['edition']=='no-root' and pending.get('root_cleanup_node')=='0.12.2'
                and self.manifest.get('runtime_variant')!='node012-beta'):
            from .root_runtime import select_payload
            original=self.payload,self.manifest
            self.payload,self.manifest=select_payload(*original)
            try:return self._continue_root_clean_removal(pending)
            finally:self.payload,self.manifest=original
        operation=pending['product_operation']
        self.progress('Removing Clean Your TV; earlier installation results will be kept.')
        from .root_clean_tail import resume as resume_tail
        reply=resume_tail(self,pending)
        if reply is None:
            root_bundle=self.payload/'root'
            previous=pending
            native_pending=False
            while isinstance(previous,dict):
                native_pending=native_pending or previous.get('home_backend')=='c1-native-gate'
                previous=previous.get('previous')
            # A host hint selects current support only. The TV still fences and
            # proves cleanup; absent device journals never clear this pending.
            if self.native_root_present() or native_pending:
                root_bundle=self.payload/'root-c1'
                if not root_bundle.is_dir():
                    raise UserError('Native C1 recovery could not be verified. Removal has not started.')
            stage=self.upload_product(root_bundle,clean_removal=True)
            retire_stages=list(pending.get('cleanup_stages',[]))
            old=pending
            while isinstance(old,dict):
                retained=old.get('product_payload')
                if isinstance(retained,str) and re.fullmatch(r'/tmp/cytv-product-[a-f0-9]{32}',retained):retire_stages.append(retained)
                old=old.get('previous')
            self.store.checkpoint(self.profile,product_payload=stage)
            target=self.product_action('clean-target',operation,stage)
            selected=target.get('target_operation');lease=target.get('target_lease')
            goal=target.get('target_removal') or pending['removal_operation']
            if pending.get('root_cleanup_lease') and (
                    lease!=pending['root_cleanup_lease']
                    or selected!=pending.get('removal_target_operation',pending['product_operation'])
                    or goal!=pending.get('removal_target_intent',pending['removal_operation'])):
                raise UserError('Removal evidence changed. Recovery data was kept.',reason_code='pending-operation')
            if (not isinstance(selected,str) or not re.fullmatch('[a-f0-9]{32}',selected)
                    or not isinstance(goal,str) or not re.fullmatch('[a-f0-9]{32}',goal)
                    or lease is not None and (not isinstance(lease,str) or not re.fullmatch('[a-f0-9]{32}',lease))):
                raise UserError('Removal evidence changed. Recovery data was kept.')
            self.store.checkpoint(self.profile,removal_target_operation=selected,removal_target_lease=lease,removal_target_intent=goal)
            reply=self.product_action('clean-remove',selected,stage,retire_stages=tuple(dict.fromkeys(retire_stages)),
                                      removal_intent=goal,removal_lease=lease or '-')
        from .recovery_state import REMOVAL_STAGES, REMOVAL_REASONS
        phase=reply.get('stage')
        if phase in REMOVAL_STAGES:
            self.store.checkpoint(self.profile,stage=phase,removal_reason=reply.get('reason') if reply.get('reason') in REMOVAL_REASONS else 'ownership-conflict')
        result=reply.get('result',{})
        if result.get('restart_required') is True:
            self.store.checkpoint(self.profile,stage='restart-required',removal_reason='restart-required',cleanup_boot_id=reply.get('cleanup_boot_id'))
            return dict(result,removed=False,verified_clean=False,restart_required=True)
        failure=reply.get('cleanup_error')
        messages={
            'root-worker-busy':'Another Clean Your TV operation is still running. Wait for it to finish, then choose Try again.',
            'root-access-required':'Root access is required to remove the remaining files. Restore Root SSH access, then choose Try again.',
            'removal-failed':'The TV could not finish removing a package. Choose Try again.',
            'cleanup-check-failed':'Some Clean Your TV files or settings remain. Choose Try again.'}
        if failure in messages:
            self.store.checkpoint(self.profile,removal_reason=failure)
            raise UserError(messages[failure],reason_code=failure)
        if (reply.get('state')!='complete' or phase!='verified-clean'
                or result.get('removed') is not True or result.get('private_cleanup_verified') is not True
                or reply.get('current') is not True):
            raise UserError(messages['cleanup-check-failed'],reason_code='cleanup-check-failed')
        result=dict(result,verified_clean=True)
        self.store.checkpoint(self.profile,stage='verified-clean',removal_reason='removal-verified',result=result)
        self.store.finish_clean_removal(self.profile)
        self._coordinator_code=self._recovery_code=self._selected_python=None
        return dict(result,verified_clean=True)

    def uninstall(self, full_project=False):
        if full_project:
            pending=self.store.request_clean_removal(self.profile)
            return self.continue_clean_removal(pending)
        pending = self.store.pending(self.profile)
        if self.profile['edition']=='no-root' and (not pending or pending.get('recovery_protocol')=='no-root-original-stream-v1'):
            from . import no_root_observer
            if pending and pending.get('action')!='uninstall':
                no_root_observer.refuse()
            if not pending:
                pending=no_root_observer.begin(self,'remove',{}, {}, {}, {})
            return self.continue_no_root(pending)
        if pending:
            # Repeated remove requests are just as uncertain as repeated installs.
            resuming_remove = pending['action'] == 'uninstall' and self.profile['edition'] == 'no-root'
            if pending['action'] != 'install' and not resuming_remove:
                raise UserError('Previous operation is unresolved. Run cytv status and retain recovery evidence before removal.')
            require_removal_idle(self.remote, self.profile, pending)
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

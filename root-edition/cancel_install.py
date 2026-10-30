#!/usr/bin/env python3
"""Internal trusted-source cancellation of one never-activated failed install.

Not an install continuation. Original submission, snapshot, request and SDK
terminal stay unchanged. This module is deliberately outside normal worker
inventories: run it only from separately pinned, reviewed recovery source.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

from install_driver import operation_id, candidate_digest
from install_device import ROOT, UPDATER, SUPERVISOR, APP, LocalDevice, checked_store
from installation import Ownership, _optional_record, terminal_install, terminal_removal
from updater.package import safe_bytes, inspect_package
from updater.store import encode

RECOVERY_FILES=('cancel_install.py','cancel_provision.py')


def digest(value):return hashlib.sha256(encode(value)).hexdigest()


class Recovery:
    def __init__(self, device, ownership, *, root=ROOT, system=Path('/'), proc=Path('/proc'), code_sha256):
        if not re.fullmatch('[a-f0-9]{64}',code_sha256):raise ValueError('pinned_recovery_code_required')
        self.device,self.owner,self.store=device,ownership,ownership.store
        self.root,self.system,self.proc=Path(root),Path(system),Path(proc)
        self.code_sha256=code_sha256

    def original_inventories(self, snapshot, submission):
        """Read known historical layouts as data; never use them for install."""
        import deploy
        from updater.bootstrap import verify_bundle
        root=snapshot/'root'
        def read(path,**kwargs):
            os.close(self.store._walk(str(path.parent)))
            return safe_bytes(path,uid=self.store.uid,**kwargs)
        manifest=json.loads(read(root/'bundle.json'));release=json.loads(read(root/'release.json'))
        version=release.get('version')
        if not isinstance(version,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',version):raise ValueError('invalid_original_root_version')
        package=APP+'_'+version+'_all.ipk'
        required=set(deploy.SUPPORT_FILES)|{'runtime/'+n for n in deploy.RUNTIME_FILES}|{package,'release.json','SHA256SUMS'}
        if (manifest.get('package')!=package or release.get('application_id')!=APP
                or not isinstance(manifest.get('files'),dict)
                or set(manifest['files']) not in (required,required|{'runtime/audio_recovery.py'})):
            raise ValueError('unknown_original_root_inventory')
        for name,sha in manifest['files'].items():
            if hashlib.sha256(read(root/name)).hexdigest()!=sha:raise ValueError('original_root_bundle_changed')
        inventories={'root':manifest,'root-updater':verify_bundle(snapshot/'root-updater',reader=read)}
        options=submission.get('options',{})
        if options.get('prepare_supervisor') is True:
            from system_setup import verify_bundle as verify_system
            inventories['supervisor']=verify_system(snapshot/'supervisor')
        return inventories

    def idle(self, snapshot):
        # An existing worker is rejected even when waiting on the ownership lock.
        # A later old worker must acquire that lock and see our deploy tombstone
        # (or terminal lease) before it can perform any product effects.
        prefixes=tuple(str(p).encode()+b'/' for p in (self.root,snapshot,UPDATER,SUPERVISOR))
        for process in self.proc.iterdir():
            if not process.name.isdigit():continue
            try:args=(process/'cmdline').read_bytes().split(b'\0')
            except FileNotFoundError:continue
            if any(arg.startswith(prefixes) for arg in args):raise ValueError('live_original_worker')
        if self.device.rpc('com.webos.appInstallService/status',{'subscribe':True}).get('status',{}).get('apps')!=[]:
            raise ValueError('installer_not_idle')

    def baseline(self, provision=None):
        if provision is None:
            settings=self.device.rpc('com.webos.settingsservice/getSystemSettings',{'category':'general','keys':['defaultApps']})
            profiles=self.device.rpc('com.webos.service.systemprofile/getProfiles',{'names':['defaultApps','idleApp'],'subscribe':False})['profiles']
            if (settings['settings']['defaultApps']['home'],profiles['defaultApps']['categories']['home'],profiles['idleApp']['appId'])!=('com.webos.app.home',)*3:
                raise ValueError('lg_home_routing_unconfirmed')
        # Original SDK registrations are expected; project overrides are not.
        paths=['var/webos-profile/override/clean-your-tv-root.json',
               'var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json']
        paths+=['var/lib/webosbrew/init.d/'+n for n in ('50-clean-your-tv-root','51-clean-your-tv-root-updater','52-clean-your-tv-system-updater')]
        if any(os.path.lexists(self.system/p) for p in paths):raise ValueError('project_routing_present')
        for state in (UPDATER,SUPERVISOR):
            if os.path.lexists(state):raise ValueError('other_component_state_present')
        apps=(APP,'com.cleanyourtv.root.updater','com.cleanyourtv.system.updater','com.cleanyourtv.updater','com.gathin.tvhome','com.local.nativehome')
        if self.device.apps()-{APP} & set(apps):raise ValueError('other_product_package_present')
        for app in apps[1:]:self.device.absent(app)
        bus=self.system/'var/luna-service2-dev'
        for folder in ('services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d'):
            directory=bus/folder
            if not os.path.lexists(directory):continue
            os.close(self.store._walk(str(directory)))
            for path in directory.iterdir():
                if path.name.startswith(tuple(a+'.' for a in apps[1:])):raise ValueError('other_product_registration_present')
                allowed=provision is not None and str(path) in provision['snapshot']['files']
                if not allowed and path.name.startswith(APP+'.') and str(self.root).encode() in safe_bytes(path,uid=self.store.uid):
                    raise ValueError('private_root_registration_present')

    def original(self, identifier, candidate, recovery):
        identifier=operation_id(identifier)
        if not isinstance(candidate,str) or not re.fullmatch('[a-f0-9]{64}',candidate):raise ValueError('original_candidate_required')
        request=_optional_record(self.store,'request-'+identifier)
        submission=_optional_record(self.store,'submission-'+identifier)
        if (not isinstance(request,dict) or request.get('operation')!=identifier or request.get('action')!='install'
                or request.get('state')!='recovery_required' or request.get('stage')!='root-deploy'
                or request.get('home_changed') is not False or request.get('candidate_sha256')!=candidate
                or not isinstance(submission,dict) or submission.get('operation')!=identifier
                or submission.get('action')!='install' or submission.get('stage')!='submitted'
                or submission.get('candidate_sha256')!=candidate):raise ValueError('original_failed_install_required')
        snapshot=Path(self.store.root)/('request-'+identifier)
        os.close(self.store._walk(str(snapshot)))
        inventories=self.original_inventories(snapshot,submission)
        options=self.device.verify_snapshot(snapshot,submission,inventories=inventories)
        if options['migrate']:raise ValueError('migration_cancellation_unsupported')
        if candidate_digest(snapshot,inventories)!=candidate:raise ValueError('original_candidate_changed')
        lease=self.owner.status()
        if (lease is None or lease['id']!=request.get('lease') or lease['owner']!='product'
                or lease['journal']!='product-'+identifier+'.json'):raise ValueError('original_lease_required')
        if lease['terminal'] and (recovery is None or recovery.get('stage')!='cancelled-and-removed'
                                  or lease['stage']!='cancelled-and-removed'):raise ValueError('unexpected_terminal_lease')
        if recovery is None and lease['stage']!='root-deploy':raise ValueError('original_lease_stage_required')
        self.idle(snapshot)
        root_store=checked_store(self.root,self.store.uid)
        os.close(root_store._directory())
        journal=root_store.read('deploy')
        original_journal=recovery['original']['deploy'] if recovery else journal
        if original_journal not in [dict(version=1,app=APP,stage=stage) for stage in ('install-observed','provision-finalize-starting')]:
            raise ValueError('never_activated_failed_install_required')
        pending_provision=original_journal['stage']=='provision-finalize-starting'
        provision=None
        # Reject every unexpected private entry, including dangling symlinks.
        import deploy
        allowed={Path(n).parts[0] for n in deploy.SUPPORT_FILES}|{'runtime','bundle.json','release.json','deploy.json','install-terminal.json','python-launcher','python-runtime.json','provision.lock'}
        if pending_provision:
            from cancel_provision import EXTRA
            allowed|=EXTRA
        if {p.name for p in self.root.iterdir()}-allowed:raise ValueError('provisioning_or_unknown_private_state')
        files=(*sorted(set(inventories['root']['files'])-{inventories['root']['package'],'SHA256SUMS'}),'bundle.json')
        retained={}
        for name in files:
            os.close(self.store._walk(str((self.root/name).parent)))
            raw=safe_bytes(self.root/name,uid=self.store.uid)
            if raw!=safe_bytes(snapshot/'root'/name,uid=self.store.uid):raise ValueError('original_private_bytes_changed')
            retained[name]=hashlib.sha256(raw).hexdigest()
        from python_binding import verify_binding
        verify_binding(self.root)
        terminal=root_store.read('install-terminal')
        if not terminal_install(terminal,APP):raise ValueError('actual_install_terminal_required')
        if pending_provision:
            from cancel_provision import PendingProvision
            removed=recovery is not None and recovery['stage'] in ('remove-observed','cancelled-and-removed')
            provision=PendingProvision(self).inspect(admitted=recovery is not None,removed=removed,
                                                     restored=recovery is not None and recovery['stage']!='admitted')
        self.baseline(provision)
        if recovery:
            admitted={k:v for k,v in recovery.items() if k not in ('removal_terminal','provision_restored')}
            admitted['stage']='admitted'
            allowed_journals=[dict(version=1,app=APP,stage='cancellation-admitted',cancellation=admitted)]
            if recovery['stage'] in ('remove-observed','cancelled-and-removed') and terminal_removal(recovery.get('removal_terminal'),APP):
                allowed_journals.append(dict(version=1,app=APP,stage='uninstalled-state-retained',
                                             evidence=recovery['removal_terminal'],**({'provisioning_rolled_back':True} if pending_provision else {'provisioning_not_started':True})))
            if journal not in allowed_journals:raise ValueError('cancellation_deploy_changed')
        release=json.loads(safe_bytes(snapshot/'root/release.json',uid=self.store.uid))
        manifest=inventories['root'];raw=safe_bytes(snapshot/'root'/manifest['package'],uid=self.store.uid)
        hashes=inspect_package(raw,{'version':release['version'],'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'local':True})
        if hashes!=release['files']:raise ValueError('original_package_inventory_changed')
        original=dict(request=request,submission=submission,deploy=original_journal,install_terminal=terminal,private=retained)
        if provision is not None:original['provision']=provision
        if recovery and original!=recovery['original']:raise ValueError('original_cancellation_proof_changed')
        return original,hashes,lease,root_store

    def receipt(self, identifier):
        value=_optional_record(self.store,'cancellation-'+operation_id(identifier))
        if value is None:
            journal=checked_store(self.root,self.store.uid).read('deploy')
            if isinstance(journal,dict) and journal.get('stage')=='cancellation-admitted':
                value=journal.get('cancellation')
                if not isinstance(value,dict):raise ValueError('missing_atomic_cancellation_proof')
        return value

    def saved_candidate(self, identifier):
        """Read one explicit operation's selector; full admission still follows."""
        request=_optional_record(self.store,'request-'+operation_id(identifier))
        candidate=request.get('candidate_sha256') if isinstance(request,dict) else None
        if not isinstance(candidate,str) or not re.fullmatch('[a-f0-9]{64}',candidate):
            raise ValueError('original_candidate_required')
        return candidate

    def inspect(self, identifier, candidate):
        recovery=self.receipt(identifier)
        if recovery is not None:
            if (not isinstance(recovery,dict) or recovery.get('schema')!=1 or recovery.get('operation')!=identifier
                    or recovery.get('candidate_sha256')!=candidate or recovery.get('code_sha256')!=self.code_sha256
                    or recovery.get('stage') not in ('admitted','remove-submitting','remove-observed','cancelled-and-removed')):
                raise ValueError('unknown_cancellation_receipt')
        original,hashes,lease,root_store=self.original(identifier,candidate,recovery)
        if recovery is None or recovery['stage']=='admitted':
            from package_data import read_verified
            from install_device import INSTALLED
            if APP not in self.device.apps():raise ValueError('original_package_missing')
            for name,sha in hashes.items():read_verified(INSTALLED/name,sha256=sha,limit=32*1024*1024,installed=INSTALLED,uid=self.store.uid)
        elif recovery['stage']=='remove-submitting':raise ValueError('removal_terminal_unknown_no_replay')
        else:
            if not terminal_removal(recovery.get('removal_terminal'),APP):raise ValueError('actual_remove_terminal_required')
            if recovery['stage']=='cancelled-and-removed':self.verify_absent(recovery['removal_terminal'],provision=original.get('provision'))
        proof=digest(dict(original=original,candidate_sha256=candidate,code_sha256=self.code_sha256))
        if recovery and recovery.get('proof_sha256')!=proof:raise ValueError('cancellation_proof_changed')
        state=recovery['stage'] if recovery else 'admissible'
        if state=='cancelled-and-removed' and not lease['terminal']:state='cancellation-terminal-pending'
        return dict(operation=identifier,candidate_sha256=candidate,code_sha256=self.code_sha256,
                    state=state,lease_terminal=lease['terminal'],proof_sha256=proof,payload_files=len(hashes),home_changed=False)

    def verify_absent(self, terminal, *, cleanup=False, provision=None):
        if not terminal_removal(terminal,APP):raise ValueError('actual_remove_terminal_required')
        import deploy
        if cleanup:deploy.verify_removed(terminal)
        else:self.device.absent(APP)
        if APP in self.device.apps():raise ValueError('root_registration_remains')
        self.baseline(provision)
        bus=self.system/'var/luna-service2-dev'
        for folder in ('services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d'):
            directory=bus/folder
            if os.path.lexists(directory) and any(p.name.startswith(APP+'.') for p in directory.iterdir()):
                raise ValueError('root_bus_registration_remains')

    @contextmanager
    def locked(self, identifier):
        request=self.store.read('request-'+operation_id(identifier))
        with self.owner.operation('product','product-'+identifier+'.json',resume=request['lease']) as lease:
            directory=checked_store(self.root,self.store.uid)._directory()
            try:
                fd=os.open('provision.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=directory)
                try:
                    self.store._check(os.fstat(fd));fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    yield lease
                finally:os.close(fd)
            finally:os.close(directory)

    def remove(self, identifier, candidate, proof_sha256):
        # Admission is repeated inside both locks before any cancellation effect.
        with self.locked(identifier) as lease:
            status=self.inspect(identifier,candidate)
            if status['proof_sha256']!=proof_sha256:raise ValueError('reviewed_admission_changed')
            name='cancellation-'+identifier;record=self.receipt(identifier)
            root_store=checked_store(self.root,self.store.uid)
            if record is None:
                original,_,_,_=self.original(identifier,candidate,None)
                record=dict(schema=1,operation=identifier,candidate_sha256=candidate,code_sha256=self.code_sha256,
                            proof_sha256=proof_sha256,stage='admitted',original=original)
                # One atomic write both preserves original proof and blocks old
                # resume. A crash before the separate receipt can recover from
                # this tombstone, without any unblocked durable admission.
                root_store.write('deploy',dict(version=1,app=APP,stage='cancellation-admitted',cancellation=record))
                self.store.write(name,record)
            if record['stage']=='admitted':
                self.store.write(name,record)
                if record['original'].get('provision') is not None:
                    from cancel_provision import PendingProvision
                    PendingProvision(self).restore(record['original']['provision'])
                    record['provision_restored']=True;self.store.write(name,record)
                record['stage']='remove-submitting';self.store.write(name,record)
                from observed_install import remove
                terminal=remove(APP,timeout=120)
                record.update(stage='remove-observed',removal_terminal=terminal);self.store.write(name,record)
            terminal=record['removal_terminal']
            provision=record['original'].get('provision')
            self.verify_absent(terminal,cleanup=True,provision=provision)
            root_store.write('deploy',dict(version=1,app=APP,stage='uninstalled-state-retained',evidence=terminal,
                                         **({'provisioning_rolled_back':True} if provision is not None else {'provisioning_not_started':True})))
            record['stage']='cancelled-and-removed';self.store.write(name,record)
            # This must precede archival. Old workers now take only their
            # terminal readback branch, even when the live Root tree is absent.
            if not lease['terminal']:self.owner.stage(lease,'cancelled-and-removed',terminal=True)
            return dict(operation=identifier,state='cancelled-and-removed',lease_terminal=True,proof_sha256=proof_sha256,home_changed=False)


def trusted_code_digest(code):
    """Pin the separately reviewed module and complete maintained worker bundle."""
    from updater.bootstrap import verify_bundle
    code=Path(code)
    manifest=verify_bundle(code)
    return digest(dict(bundle=manifest,recovery={name:hashlib.sha256(safe_bytes(code/name,uid=0)).hexdigest() for name in RECOVERY_FILES}))


def main():
    import argparse
    import sys
    from deploy import require_device
    from installation import STATE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','remove'))
    parser.add_argument('--operation',required=True)
    parser.add_argument('--candidate')
    parser.add_argument('--code-sha256',required=True)
    parser.add_argument('--proof-sha256')
    args=parser.parse_args()
    require_device()
    code=Path(__file__).absolute().parent
    store=checked_store(STATE)
    os.close(store._walk(str(code)))
    if trusted_code_digest(code)!=args.code_sha256:raise ValueError('reviewed_recovery_code_changed')
    owner=Ownership.__new__(Ownership);owner.store=store
    recovery=Recovery(LocalDevice(),owner,code_sha256=args.code_sha256)
    if args.action=='inspect':result=recovery.inspect(args.operation,args.candidate if args.candidate is not None else recovery.saved_candidate(args.operation))
    else:
        if args.candidate is None or args.proof_sha256 is None:parser.error('remove requires the original candidate and a reviewed admission proof')
        result=recovery.remove(args.operation,args.candidate,args.proof_sha256)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()

"""Exercise the compatibility shim against the immutable public 1.3 supervisor."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class SystemRollbackAnchorTests(unittest.TestCase):
    def scenario(self,body):
        project=Path(__file__).resolve().parents[2]
        setup='''
from legacy_ota_fixture import LegacyOTA
from pathlib import Path
from unittest.mock import patch
import importlib.util,json,os,shutil,subprocess,sys

def guard_for(f):
 spec=importlib.util.spec_from_file_location('tested_anchor_guard',f.root/'runtime/update_guard.py')
 guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.INSTALLED=f.installed
 return guard

def prepare(f):
 f.complete_update()
 with f.product_operation():f.manager.rollback()
 tx=f.store.read('transaction')
 f.device._guard().reserve(tx['id'],f.root,uid=os.getuid())
 return guard_for(f),tx['id']

def stage(f,g,transaction):
 run=subprocess.run
 def local_run(args,*a,**kw):
  if isinstance(args,(list,tuple)) and args[0]=='/usr/bin/node':args=[shutil.which('node'),*args[1:]]
  return run(args,*a,**kw)
 with f.product_operation(),f.store.lock(),g.locked(f.root,os.getuid()),patch.object(subprocess,'run',side_effect=local_run):
  g.stage_system_rollback_anchor(transaction,f.root,uid=os.getuid())
'''
        result=subprocess.run([sys.executable,'-c',setup+'\n'+body],cwd=project,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(project/'tests/system_updates')},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
        self.assertEqual(result.returncode,0,result.stdout)

    def test_original_supervisor_reproduces_failure_without_shim(self):
        self.scenario('''
with LegacyOTA() as f:
 f.complete_update()
 runtime=f.device.runtime
 f.device.runtime=lambda mode,transaction=None:'restored' if mode=='suspend-update' else runtime(mode,transaction)
 try:f.rollback()
 except (AssertionError,ValueError) as error:assert 'Conflicting Root publication' in str(error),str(error)
 else:raise AssertionError('Unmodified supervisor unexpectedly completed retained rollback')
''')

    def test_original_supervisor_retained_rollback_captures_active_intent_before_authority_changes(self):
        self.scenario('''
with LegacyOTA() as f:
 f.complete_update()
 # Device-only routing/input activation IO is adapted; the immutable manager,
 # package byte authority, guard journal, staging and installer terminals run.
 sys.path.insert(0,str(f.root/'runtime'))
 spec=importlib.util.spec_from_file_location('candidate_live_identity',Path.cwd()/'root-edition/package_identity.py')
 presence=importlib.util.module_from_spec(spec);spec.loader.exec_module(presence)
 presence.STATES={presence.ROOT:f.root,presence.UPDATER:f.updater,presence.SYSTEM:f.state}
 active=dict(version=1,generation=18,phase='active',enabled=True,boot='boot:fixture',token='owner-enable')
 f.root_store.write('persistent-intent',active)
 enabled=[];captured=[];runtime=f.device.runtime
 def restored():
  value=f.root_store.read('persistent-intent');value.update(phase='disabled',enabled=False)
  f.root_store.write('persistent-intent',value);return 'restored'
 def enable():
  value=f.root_store.read('persistent-intent');value.update(phase='active',enabled=True,generation=value['generation']+1,token='resumed')
  f.root_store.write('persistent-intent',value);enabled.append(True)
  return dict(intent=value,persistent=True)
 def observed_runtime(mode,transaction=None):
  if mode not in ('suspend-update','finish-update','abort-update'):return runtime(mode,transaction)
  g=guard_for(f)
  g._intent=lambda:f.root_store.read('persistent-intent')
  g._boot=lambda:'boot:fixture';g._failsafe=lambda:False;g._restore=restored;g._enable=enable
  if mode=='suspend-update':
   # Exact production selector, no home_present=True substitution.
   if not captured:
    assert presence.identity(presence.ROOT,purpose='live',installed=f.installed,uid=os.getuid())['version']=='1.1.0'
   run=subprocess.run
   def local_run(args,*a,**kw):
    if isinstance(args,(list,tuple)) and args[0]=='/usr/bin/node':args=[shutil.which('node'),*args[1:]]
    return run(args,*a,**kw)
   with patch.object(subprocess,'run',side_effect=local_run):result=g.suspend(transaction,f.root,os.getuid())
   captured.append(g.ticket(f.root,os.getuid()))
   return result
  return g.finish(transaction,f.root,os.getuid(),resume=mode=='finish-update')
 f.device.runtime=observed_runtime
 with f.product_operation():f.manager.rollback()
 tx=f.run_until('verifying-rollback')
 assert not enabled, 'Delayed launcher health cannot enable Home'
 assert captured[0]['before']==active and captured[0]['desired'] is True
 f.manager.healthy('root',tx['id'],'1.0.0');tx=f.run_until('rolled-back')
 tx=f.finish_like_worker(tx)
 assert tx['homeResume']=={'status':'restored'},tx
 assert len(enabled)==1 and f.root_store.read('persistent-intent')['enabled'] is True
 f.finish_like_worker(tx);assert len(enabled)==1,'restart must not replay activation'
''')

    def test_staging_is_idempotent_preserves_journal_and_keeps_candidate_selected(self):
        self.scenario('''
with LegacyOTA() as f:
 g,transaction=prepare(f)
 before=(f.state/'transaction.json').read_bytes()
 stage(f,g,transaction)
 receipt=(f.root/('system-rollback-anchor-'+transaction+'.json')).read_bytes()
 stage(f,g,transaction)
 assert (f.state/'transaction.json').read_bytes()==before
 assert (f.root/('system-rollback-anchor-'+transaction+'.json')).read_bytes()==receipt
 current=f.up_store.read('current');assert current['sha256']==f.prior['components'][0]['sha256']
 assert f.device.owner_identity('com.cleanyourtv.root.preview')['version']=='1.1.0'
 assert f.off.read_bytes()==f.off_bytes
 f.rollback()
''')

    def test_crash_windows_reconcile_without_changing_installer_evidence(self):
        self.scenario('''
for point in ('receipt-before','receipt-after','current-before','current-after'):
 with LegacyOTA() as f:
  g,transaction=prepare(f);before=(f.state/'transaction.json').read_bytes()
  atomic=g.atomic;replace=os.replace;injected=[False]
  def fail_receipt(path,value):
   if point=='receipt-before':raise OSError('injected before receipt')
   atomic(path,value)
   if point=='receipt-after':raise OSError('injected after receipt')
  def fail_current(source,destination):
   target=Path(destination)==f.updater/'current.json'
   if target and point=='current-before':raise OSError('injected before anchor')
   replace(source,destination)
   if target and point=='current-after':raise OSError('injected after anchor')
  try:
   with patch.object(g,'atomic',side_effect=fail_receipt),patch.object(os,'replace',side_effect=fail_current):stage(f,g,transaction)
  except OSError:pass
  else:raise AssertionError('Failure injection missed '+point)
  assert (f.state/'transaction.json').read_bytes()==before
  stage(f,g,transaction)
  assert f.up_store.read('current')['sha256']==f.prior['components'][0]['sha256']
  assert f.device.owner_identity('com.cleanyourtv.root.preview')['version']=='1.1.0'
  f.rollback()
''')

    def test_invalid_provenance_unknown_outcomes_and_conflicts_do_not_stage(self):
        self.scenario('''
for damage in ('signature','sdk','prior-cache','writer','reservation','lease','unknown-terminal','rollback-intent','receipt','code'):
 with LegacyOTA() as f:
  g,transaction=prepare(f)
  original=(f.updater/'current.json').read_bytes()
  tx=f.store.read('transaction')
  if damage=='signature':
   tx['candidate']['proof']['signature']='AAAA';f.store.write('transaction',tx)
  elif damage=='sdk':
   path=f.installed/'usr/palm/applications/com.cleanyourtv.root.preview/index.html';path.write_bytes(b'untrusted')
  elif damage=='prior-cache':
   path=f.state/'cache'/f.prior['components'][0]['sha256'];path.write_bytes(b'untrusted')
  elif damage=='writer':
   current=f.up_store.read('current');current['writer']['id']='a'*32;f.up_store.write('current',current);original=(f.updater/'current.json').read_bytes()
  elif damage=='reservation':g.atomic(f.root/'update-block.json',{'transaction':'a'*32})
  elif damage=='lease':
   record=f.owner.status();record['owner']='deploy';f.owner.store.write('operation',record)
  elif damage=='unknown-terminal':
   tx['components'][0]['installEvidence']['terminal']=None;f.store.write('transaction',tx)
  elif damage=='rollback-intent':
   tx['components'][0]['rollbackEvidence']['intent']=True;f.store.write('transaction',tx)
  elif damage=='receipt':g.atomic(f.root/('system-rollback-anchor-'+transaction+'.json'),{'schema':1,'transaction':'a'*32})
  else:
   path=f.code/'system_updater/device.py';path.write_bytes(path.read_bytes()+b'# untrusted')
  try:stage(f,g,transaction)
  except (ValueError,OSError,RuntimeError,subprocess.CalledProcessError):pass
  else:raise AssertionError('Accepted '+damage)
  assert (f.updater/'current.json').read_bytes()==original,damage
  assert f.off.read_bytes()==f.off_bytes
''')

    def test_verified_sources_ignore_matching_unverified_bytecode_and_ambient_modules(self):
        self.scenario('''
with LegacyOTA() as f:
 g,transaction=prepare(f)
 import importlib.util,py_compile,sys,types
 for relative in ('system_updater/device.py','package_identity.py'):
  path=f.code/relative;original=path.read_bytes();info=path.stat()
  poison=b"raise RuntimeError('unverified bytecode executed')"
  path.write_bytes(poison+b' '*(len(original)-len(poison)));os.utime(path,ns=(info.st_atime_ns,info.st_mtime_ns))
  py_compile.compile(str(path),doraise=True)
  path.write_bytes(original);os.utime(path,ns=(info.st_atime_ns,info.st_mtime_ns))
 sentinel=types.ModuleType('package_identity')
 with patch.dict(sys.modules,{'package_identity':sentinel}):
  stage(f,g,transaction)
  assert sys.modules['package_identity'] is sentinel
 assert f.up_store.read('current')['sha256']==f.prior['components'][0]['sha256']
 f.rollback()
''')

    def test_free_parent_locks_cannot_authorize_staging(self):
        self.scenario('''
with LegacyOTA() as f:
 g,transaction=prepare(f);before=(f.updater/'current.json').read_bytes()
 try:g.stage_system_rollback_anchor(transaction,f.root,uid=os.getuid())
 except ValueError as error:assert 'lock' in str(error),str(error)
 else:raise AssertionError('Staged outside owning worker locks')
 assert (f.updater/'current.json').read_bytes()==before
''')


if __name__=='__main__':unittest.main()

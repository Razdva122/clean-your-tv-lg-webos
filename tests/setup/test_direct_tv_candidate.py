"""Direct TV QA is bounded, source-bound data; never release acceptance."""
import hashlib, importlib.util, json, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('feeds_direct',ROOT/'scripts/root-candidate-feeds.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DirectAdmission(unittest.TestCase):
 def setUp(self):
  self.versions=json.loads((ROOT/'release-versions.json').read_text())
  self.run={'id':12,'run_attempt':2,'head_sha':'a'*40,'head_branch':'codex/qa','head_repository':{'full_name':m.REPO},'event':'workflow_dispatch','path':'.github/workflows/tv-candidate.yml','status':'completed','conclusion':'success'}
  self.job={'id':56,'name':'build-root-tv','run_id':12,'run_attempt':2,'head_sha':'a'*40,'status':'completed','conclusion':'success'}
 def validate(self,run=None,jobs=None):
  return m.validate_run(run or self.run,jobs or [self.job],'v'+self.versions['release'],self.versions,[],preliminary=True,direct_tv=True,source_sha='a'*40,branch='codex/qa')
 def test_direct_job_is_bound_to_origin_source_workflow_and_attempt(self):
  value=self.validate();self.assertIs(value['direct_tv'],True);self.assertEqual(value['workflow'],self.run['path'])
  for field,val in [('path','.github/workflows/cytv.yml'),('head_repository',{'full_name':'other/repo'}),('head_sha','b'*40),('run_attempt',3),('status','in_progress')]:
   with self.subTest(field=field),self.assertRaises(ValueError):self.validate(run=dict(self.run,**{field:val}))
  for field,val in [('run_id',13),('run_attempt',1),('name','other'),('head_sha','b'*40)]:
   with self.subTest(field=field),self.assertRaises(ValueError):self.validate(jobs=[dict(self.job,**{field:val})])
 def test_direct_mode_requires_preliminary_and_explicit_source(self):
  with self.assertRaises(ValueError):m.validate_run(self.run,[self.job],'v'+self.versions['release'],self.versions,[],direct_tv=True)
 def test_exact_direct_artifact_and_digest_required(self):
  a={'id':8,'name':'root-tv-candidate','expired':False,'size_in_bytes':30,'digest':'sha256:'+'b'*64,'workflow_run':{'id':12,'head_sha':'a'*40}}
  self.assertEqual(m.artifact_info([a],self.run,direct_tv=True)['id'],8)
  for changed in [dict(a,name='cytv-macos-arm64'),dict(a,digest='bad'),dict(a,workflow_run={'id':13,'head_sha':'a'*40})]:
   with self.assertRaises(ValueError):m.artifact_info([changed],self.run,direct_tv=True)
 def test_workflow_source_must_match_trusted_tools(self):
  with patch.object(m,'content_bytes',return_value=b'foreign workflow'),self.assertRaises(ValueError):m.verify_direct_workflow('a'*40)
  raw=(ROOT/'.github/workflows/tv-candidate.yml').read_bytes()
  with patch.object(m,'content_bytes',return_value=raw):m.verify_direct_workflow('a'*40)
 def test_zip_rejects_traversal_symlink_duplicate_and_oversize(self):
  for name,mode,duplicate in [('../manifest.json',0,False),('manifest.json',0o120777,False),('manifest.json',0,True)]:
   with tempfile.TemporaryDirectory() as temp:
    archive=Path(temp)/'candidate.zip'
    with zipfile.ZipFile(archive,'w') as z:
     info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,b'{}')
     if duplicate:z.writestr(name,b'{}')
    with self.assertRaises(ValueError):m.read_tv_archive(archive,hashlib.sha256(archive.read_bytes()).hexdigest(),{},Path(temp)/'out')
 def test_recheck_binds_direct_mode_and_attempt_artifact(self):
  meta=dict(self.validate(),artifact={'id':8,'sha256':'b'*64,'size':30})
  with patch.object(m,'inspect_build',return_value=meta) as check:
   m.recheck(meta);self.assertTrue(check.call_args.kwargs['direct_tv'])
  for field,value in [('attempt',3),('artifact',{'id':9,'sha256':'c'*64,'size':30})]:
   with patch.object(m,'inspect_build',return_value=dict(meta,**{field:value})),self.assertRaises(ValueError):m.recheck(meta)
 def bundle(self):
  import sys
  sys.path.insert(0,str(ROOT))
  from cytv import package
  metadata=dict(self.validate(),artifact={'id':8,'sha256':'b'*64,'size':30})
  infra={n:b'fixture' for n in m.infrastructure_paths()};infra['updater/updater/release-public.pem']=(ROOT/'updater-service/release-public.pem').read_bytes();infra['updater/package.json']=json.dumps({'name':'com.cleanyourtv.root.updater.service','version':self.versions['updater']}).encode()
  components=[];files={}
  for name,app in [('root','com.cleanyourtv.root.preview'),('root-updater','com.cleanyourtv.root.updater')]:
   version=self.versions['root' if name=='root' else 'updater'];prefix='usr/palm/applications/'+app+'/'
   payload={prefix+'appinfo.json':json.dumps({'id':app,'version':version,'type':'web','main':'index.html'}).encode(),prefix+'index.html':b'fixture','usr/palm/packages/'+app+'/packageinfo.json':json.dumps({'id':app,'app':app,'version':version,'services':[app+'.service']}).encode()}
   if name=='root':payload.update({'usr/palm/services/'+app+'.service/'+n[8:]:b for n,b in infra.items() if n.startswith('service/')})
   raw=package.ipk(app,version,payload);filename=app+'_'+version+'_all.ipk';files[filename]=raw
   components.append({'name':name,'kind':'ipk','application':app,'version':version,'url':'https://github.com/'+m.REPO+'/releases/download/'+metadata['release']+'/'+filename,'size':len(raw),'sha256':m.digest(raw)})
  filename='root-infrastructure_'+self.versions['root']+'.tar.gz';raw=package.tgz(infra,directories=False);files[filename]=raw
  components.append({'name':'root-infrastructure','kind':'infrastructure','version':self.versions['root'],'url':'https://github.com/'+m.REPO+'/releases/download/'+metadata['release']+'/'+filename,'size':len(raw),'sha256':m.digest(raw)})
  files['manifest.json']=json.dumps({'schema':1,'release':metadata['release'],'edition':'root','supervisor':1,'minimumSupervisorVersion':'1.1.1','notes':'fixture','components':components}).encode()
  p={k:metadata[k] for k in ('source','run_id','attempt','versions','public_key_sha256')};p.update(schema=1,workflow=m.DIRECT_WORKFLOW,repository=m.REPO);files['PROVENANCE.json']=json.dumps(p).encode()
  return files,metadata
 def test_complete_bundle_preserves_package_bytes_and_replaces_untrusted_notes(self):
  files,meta=self.bundle()
  with tempfile.TemporaryDirectory() as temp:
   archive=Path(temp)/'candidate.zip'
   with zipfile.ZipFile(archive,'w') as z:
    for n,b in files.items():z.writestr(n,b)
   out=Path(temp)/'result';m.read_tv_archive(archive,m.digest(archive.read_bytes()),meta,out)
   signed=json.loads((out/'PROVENANCE.json').read_text());self.assertEqual(signed['source'],meta['source'])
   self.assertEqual(json.loads((out/'manifest.json').read_text())['notes'],m.notes_for(meta))
   for n,b in files.items():
    if n not in ('manifest.json','PROVENANCE.json'):self.assertEqual((out/n).read_bytes(),b)
   with self.assertRaises(ValueError):m.read_tv_archive(archive,'0'*64,meta,Path(temp)/'bad')
 def test_bundle_rejects_changed_provenance_versions_key_and_incomplete_packages(self):
  for field,value in [('source','c'*40),('run_id',13),('attempt',1),('workflow','.github/workflows/cytv.yml'),('public_key_sha256','0'*64)]:
   files,meta=self.bundle();p=json.loads(files['PROVENANCE.json']);p[field]=value;files['PROVENANCE.json']=json.dumps(p).encode()
   with self.subTest(field=field),self.assertRaises(ValueError):m.validate_tv_bundle(files,meta)
  files,meta=self.bundle();manifest=json.loads(files['manifest.json']);manifest['components'][0]['version']='9.9.9';files['manifest.json']=json.dumps(manifest).encode()
  with self.assertRaises(ValueError):m.validate_tv_bundle(files,meta)
  files,meta=self.bundle();del files[next(n for n in files if n.endswith('.ipk'))]
  with self.assertRaises(ValueError):m.validate_tv_bundle(files,meta)
 def test_complete_zip_rejects_link_and_oversized_metadata(self):
  for damage in ('link','metadata','path'):
   files,meta=self.bundle()
   with tempfile.TemporaryDirectory() as temp:
    archive=Path(temp)/'candidate.zip'
    with zipfile.ZipFile(archive,'w') as z:
     for n,b in files.items():
      info=zipfile.ZipInfo('../'+n if damage=='path' and n=='manifest.json' else n)
      if damage=='link' and n=='manifest.json':info.external_attr=0o120777<<16
      z.writestr(info,b'x'*65537 if damage=='metadata' and n=='manifest.json' else b)
    with self.subTest(damage=damage),self.assertRaises(ValueError):m.read_tv_archive(archive,m.digest(archive.read_bytes()),meta,Path(temp)/'out')
 def test_nested_archives_reject_missing_runtime_foreign_paths_and_changed_key(self):
  from cytv import package
  for damage in ('key','missing','path','version','service'):
   files,meta=self.bundle();manifest=json.loads(files['manifest.json']);c=manifest['components'][2];name=c['url'].rsplit('/',1)[1];infra=m.bounded_package_module().archive(files[name])
   if damage=='key':infra['updater/updater/release-public.pem']=b'foreign key'
   if damage=='missing':del infra[next(n for n in infra if n.startswith('runtime/'))]
   if damage=='path':infra['foreign/file']=b'foreign'
   if damage=='version':infra['updater/package.json']=b'{"name":"com.cleanyourtv.root.updater.service","version":"9.9.9"}'
   if damage=='service':infra[next(n for n in infra if n.startswith('service/'))]=b'changed'
   raw=package.tgz(infra,directories=False);files[name]=raw;c['size']=len(raw);c['sha256']=m.digest(raw);files['manifest.json']=json.dumps(manifest).encode()
   with self.subTest(damage=damage),self.assertRaises(ValueError):m.validate_tv_bundle(files,meta)

 def test_nested_gzip_expansion_is_bounded_before_tar_parsing(self):
  import gzip
  with patch.object(m,'MAX_TAR',1024):
   parser=m.bounded_package_module()
   with self.assertRaisesRegex(ValueError,'expanded'):parser.archive(gzip.compress(b'0'*1025))
 def test_builder_refuses_uncommitted_source(self):
  spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build-tv-candidate.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
  with tempfile.TemporaryDirectory() as temp,patch.object(builder.subprocess,'check_output',side_effect=['a'*40+'\n',b' M source.py\n']):
   with self.assertRaisesRegex(ValueError,'Clean'):builder.build(Path(temp)/'out','a'*40,12,2)

if __name__=='__main__':unittest.main()

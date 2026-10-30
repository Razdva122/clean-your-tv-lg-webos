"""Root QA signing admission must bind trusted successful builds and exact archives."""
import copy,json,hashlib,importlib.util,io,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('root_candidate_feeds',ROOT/'scripts/root-candidate-feeds.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class AdmissionTests(unittest.TestCase):
 def setUp(self):
  self.run={'id':12,'run_attempt':1,'head_sha':'a'*40,'head_branch':'release/next','head_repository':{'full_name':m.REPO},'event':'push','path':'.github/workflows/cytv.yml','status':'completed','conclusion':'success'}
  self.jobs=[{'name':name,'conclusion':'success'} for name in m.BUILD_JOBS]
  self.versions={'release':'1.5.0','cytv':'0.6.0','home':'1.6.0','helper':'0.6.20','root':'0.6.0','updater':'0.3.3','android':'0.5.0','android_version_code':15}
 def check(self,run=None,jobs=None,tag='v1.5.0',published=()):return m.validate_run(self.run if run is None else run,self.jobs if jobs is None else jobs,tag,self.versions,published)
 def test_complete_origin_build_is_admitted(self):self.assertEqual(self.check()['source'],'a'*40)
 def test_foreign_or_incomplete_runs_are_rejected(self):
  cases=[('head_branch','main'),('event','pull_request'),('path','.github/workflows/tests.yml'),('status','in_progress'),('conclusion','failure'),('run_attempt',0),('head_sha','bad'),('head_repository',{'full_name':'foreign/repo'})]
  for field,value in cases:
   run=copy.deepcopy(self.run);run[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):self.check(run=run)
 def test_missing_required_job_and_wrong_release_are_rejected(self):
  with self.assertRaises(ValueError):self.check(jobs=self.jobs[:-1])
  with self.assertRaises(ValueError):self.check(tag='v1.5.1')
  with self.assertRaises(ValueError):self.check(tag='v1.5.0',published=['v1.5.0'])
 def test_only_one_current_digest_bound_cli_artifact_is_accepted(self):
  artifact={'id':34,'name':'cytv-macos-arm64','expired':False,'size_in_bytes':50,'digest':'sha256:'+'b'*64,'workflow_run':{'id':12,'head_sha':'a'*40}}
  self.assertEqual(m.artifact_info([artifact],self.run)['id'],34)
  for entries in ([],[artifact,artifact],[dict(artifact,expired=True)],[dict(artifact,digest=None)],[dict(artifact,workflow_run={'id':999,'head_sha':'a'*40})]):
   with self.assertRaises(ValueError):m.artifact_info(entries,self.run)
 def test_exact_archive_digest_and_single_regular_cli_are_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'cli.zip';out=Path(tmp)/'cli'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('cytv',b'compiled fixture')
   digest=hashlib.sha256(archive.read_bytes()).hexdigest();m.read_cli_archive(archive,digest,out);self.assertEqual(out.read_bytes(),b'compiled fixture')
   with self.assertRaises(ValueError):m.read_cli_archive(archive,'0'*64,Path(tmp)/'wrong')
   with zipfile.ZipFile(archive,'w') as z:z.writestr('../cytv',b'outside')
   with self.assertRaises(ValueError):m.read_cli_archive(archive,hashlib.sha256(archive.read_bytes()).hexdigest(),Path(tmp)/'outside')

 def preliminary(self,run=None,jobs=None,source='a'*40,branch='codex/device-qa'):
  selected=dict(self.run,head_branch=branch,event='workflow_dispatch',status='in_progress',conclusion=None) if run is None else run
  jobs=[self.package_job()] if jobs is None else jobs
  return m.validate_run(selected,jobs,'v1.5.0',self.versions,[],preliminary=True,source_sha=source,branch=branch)
 def package_job(self):
  return {'id':56,'name':m.PRELIMINARY_JOB,'status':'completed','conclusion':'success','run_id':12,'head_sha':'a'*40,'run_attempt':1}
 def test_preliminary_job_identity_status_and_attempt_are_bound(self):
  job=self.package_job();metadata=self.preliminary(jobs=[job])
  self.assertEqual(metadata['package_job'],job)
  for field,value in (('id',None),('status','queued'),('run_id',13),('head_sha','b'*40),('run_attempt',2)):
   with self.subTest(field=field),self.assertRaises(ValueError):self.preliminary(jobs=[dict(job,**{field:value})])
  with self.assertRaises(ValueError):self.preliminary(jobs=[job,job])
 def test_inspection_resolves_actual_branch_and_attempt_specific_jobs(self):
  from unittest.mock import patch
  import subprocess
  run=dict(self.run,head_branch='codex/device-qa',event='workflow_dispatch',status='in_progress',conclusion=None)
  artifact={'id':34,'name':'cytv-macos-arm64','expired':False,'size_in_bytes':50,'digest':'sha256:'+'b'*64,'workflow_run':{'id':12,'head_sha':'a'*40}}
  for damage in (None,'missing-branch','moved-branch','tag-collision','tag-network-error','old-attempt','queued-job','duplicate-job'):
   calls=[]
   def api(path,paginate=False):
    calls.append(path)
    missing=lambda:subprocess.CalledProcessError(1,['gh'],output=b'{"status":"404"}')
    if path=='actions/runs/12':return run
    if path=='git/ref/heads/codex/device-qa':
     if damage=='missing-branch':raise missing()
     return {'ref':'refs/heads/codex/device-qa','object':{'type':'commit','sha':('c' if damage=='moved-branch' else 'a')*40}}
    if path=='git/ref/tags/codex/device-qa':
     if damage=='tag-network-error':raise subprocess.CalledProcessError(1,['gh'],output=b'connection failed')
     if damage=='tag-collision':return {'ref':'refs/tags/codex/device-qa','object':{'type':'commit','sha':'a'*40}}
     raise missing()
    if path=='actions/runs/12/attempts/1/jobs?per_page=10':
     job=self.package_job()
     if damage=='old-attempt':job['run_attempt']=0
     if damage=='queued-job':job['status']='queued'
     return [{'jobs':[job,job] if damage=='duplicate-job' else [job]}]
    if path=='releases?per_page=100':return [[]]
    if path=='actions/runs/12/artifacts?per_page=100':return [{'artifacts':[artifact]}]
    raise AssertionError('Unexpected API: '+path)
   def contents(name,source):
    if name=='release-plan.json':return {'version':'1.5.0'}
    return dict(self.versions,release='1.4.1') if source=='main' else self.versions
   with self.subTest(damage=damage),patch.object(m,'api',side_effect=api),patch.object(m,'contents',side_effect=contents):
    if damage is None:
     metadata=m.inspect_build(12,'v1.5.0',preliminary=True,source_sha='a'*40,branch='codex/device-qa')
     self.assertEqual(metadata['package_job']['id'],56)
    else:
     with self.assertRaises((ValueError,subprocess.CalledProcessError)):m.inspect_build(12,'v1.5.0',preliminary=True,source_sha='a'*40,branch='codex/device-qa')
 def test_small_job_pages_preserve_complete_attempt_admission(self):
  from unittest.mock import patch
  import subprocess
  run=dict(self.run,run_attempt=2)
  artifact={'id':34,'name':'cytv-macos-arm64','expired':False,'size_in_bytes':50,'digest':'sha256:'+'b'*64,'workflow_run':{'id':12,'head_sha':'a'*40}}
  final={'name':'validation / full-release','conclusion':'success'}
  first=[dict(name=name,conclusion='success') for name in sorted(m.BUILD_JOBS) if name!=final['name']]+[{'name':'scope','conclusion':'success'}]
  self.assertEqual(len(first),10)
  for damage in (None,'missing-second-page','failed-second-page','later-page-error'):
   calls=[]
   def output(args):
    path=args[2].removeprefix('repos/'+m.REPO+'/');calls.append((path,args[3:]))
    if path=='actions/runs/12':return json.dumps(run).encode()
    if path=='actions/runs/12/attempts/2/jobs?per_page=100':raise subprocess.CalledProcessError(1,args,output=b'HTTP 502')
    if path=='actions/runs/12/attempts/2/jobs?per_page=10':
     self.assertEqual(args[3:],['--paginate','--slurp'])
     pages=[{'total_count':11,'jobs':first}]
     if damage=='later-page-error':raise subprocess.CalledProcessError(1,args,output=json.dumps(pages).encode())
     if damage!='missing-second-page':pages.append({'total_count':11,'jobs':[dict(final,conclusion='failure') if damage=='failed-second-page' else final]})
     return json.dumps(pages).encode()
    if path=='releases?per_page=100':return b'[[]]'
    if path=='actions/runs/12/artifacts?per_page=100':return json.dumps([{'artifacts':[artifact]}]).encode()
    raise AssertionError('Unexpected API: '+path)
   def contents(name,source):
    if name=='release-plan.json':return {'version':'1.5.0'}
    return dict(self.versions,release='1.4.1') if source=='main' else self.versions
   with self.subTest(damage=damage),patch.object(m.subprocess,'check_output',side_effect=output),patch.object(m,'contents',side_effect=contents):
    if damage is None:
     metadata=m.inspect_build(12,'v1.5.0')
     self.assertEqual(metadata['attempt'],2);self.assertEqual(metadata['artifact']['id'],34)
    else:
     with self.assertRaises((ValueError,subprocess.CalledProcessError)):m.inspect_build(12,'v1.5.0')
 def test_preliminary_admits_only_finished_arm64_job_while_validation_is_pending(self):
  value=self.preliminary()
  self.assertIs(value['preliminary'],True);self.assertEqual(value['branch'],'codex/device-qa')
  self.assertEqual(value['source'],'a'*40)
 def test_preliminary_exact_source_branch_origin_and_successful_job_are_required(self):
  for field,value in (('head_sha','b'*40),('head_branch','other'),('event','pull_request'),('head_repository',{'full_name':'foreign/repo'}),('path','.github/workflows/tests.yml'),('status','completed'),('run_attempt',2)):
   run=dict(self.run,head_branch='codex/device-qa',event='workflow_dispatch',status='in_progress',conclusion=None);run[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):self.preliminary(run=run)
  for branch in ('refs/pull/1/head','refs/tags/v1.5.0','bad..branch','bad branch','-bad'):
   with self.subTest(branch=branch),self.assertRaises(ValueError):self.preliminary(branch=branch)
  for source in ('','bad','B'*40):
   with self.subTest(source=source),self.assertRaises(ValueError):self.preliminary(source=source)
  for jobs in ([],[{'name':'other','conclusion':'success'}],[{'name':m.PRELIMINARY_JOB,'conclusion':'failure'}],[{'name':m.PRELIMINARY_JOB,'conclusion':'success','head_sha':'b'*40,'run_attempt':1}]):
   with self.subTest(jobs=jobs),self.assertRaises(ValueError):self.preliminary(jobs=jobs)
  jobs=[{'name':m.PRELIMINARY_JOB,'conclusion':'success','head_sha':'a'*40,'run_attempt':1},{'name':'validation / tests (ubuntu-latest)','conclusion':'failure'}]
  with self.assertRaises(ValueError):self.preliminary(jobs=jobs)
 def test_preliminary_finished_success_is_still_marked_preliminary(self):
  run=dict(self.run,head_branch='codex/device-qa',event='workflow_dispatch')
  self.assertIs(self.preliminary(run=run)['preliminary'],True)
 def test_default_does_not_accept_preliminary_dispatch_parameters(self):
  with self.assertRaises(ValueError):m.validate_run(self.run,self.jobs,'v1.5.0',self.versions,[],source_sha='a'*40,branch='release/next')
 def test_preliminary_payload_build_uses_only_trusted_tools_and_metadata(self):
  from unittest.mock import patch
  metadata=self.preliminary()
  with patch.object(m.subprocess,'run') as run:
   m.prepare_inputs(metadata,Path('/untrusted/candidate'),Path('/data/payload'),Path('/data/output'),'notes')
  args=run.call_args.args[0]
  self.assertEqual(args[3],str(m.ROOT));self.assertEqual(run.call_args.kwargs['cwd'],m.ROOT)
  self.assertNotIn('/untrusted/candidate',str(args))
  self.assertEqual(json.loads(args[-1]),self.versions)
 def test_preliminary_recheck_preserves_exact_mode_source_branch_and_artifact(self):
  from unittest.mock import patch
  metadata=dict(self.preliminary(),artifact={'id':34,'sha256':'b'*64,'size':50})
  with patch.object(m,'inspect_build',return_value=metadata) as inspect:
   m.recheck(metadata)
   inspect.assert_called_once_with(12,'v1.5.0',preliminary=True,source_sha='a'*40,branch='codex/device-qa')
  for key,value in (('attempt',2),('source','c'*40),('artifact',{'id':35,'sha256':'c'*64,'size':50})):
   with self.subTest(key=key),patch.object(m,'inspect_build',return_value=dict(metadata,**{key:value})),self.assertRaises(ValueError):m.recheck(metadata)
 def test_signing_workflow_keeps_protected_tools_and_no_publication_gate(self):
  text=(ROOT/'.github/workflows/publish-release.yml').read_text()
  self.assertIn("github.ref == 'refs/heads/release/next' && inputs.publish == false",text)
  self.assertIn("!inputs.preliminary_root_qa && !inputs.candidate_source_sha && !inputs.candidate_branch",text)
  self.assertIn('path: qa-tools\n          ref: ${{ github.sha }}',text)
  self.assertIn('args+=(--preliminary --source-sha "$SOURCE_SHA" --branch "$SOURCE_BRANCH")',text)
 def test_preliminary_notes_match_trusted_signer_and_cannot_claim_final_validation(self):
  metadata=dict(self.preliminary(),artifact={'sha256':'b'*64})
  self.assertIn('not final release acceptance',m.notes_for(metadata))
  result=m.subprocess.check_output(['node','-e',"const f=require('./scripts/sign-root-candidate.cjs');process.stdout.write(f.notesFor(JSON.parse(process.argv[1])))",json.dumps(metadata)],cwd=ROOT,text=True)
  self.assertEqual(result,m.notes_for(metadata))

if __name__=='__main__':unittest.main()

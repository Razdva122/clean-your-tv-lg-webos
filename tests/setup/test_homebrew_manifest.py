"""Data-only Homebrew metadata and publication gates using real small IPKs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cytv import package, python_runtime
from homebrew.build import APP_ID, APP_PREFIX, IDENTITIES, installer_ipk

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/homebrew-manifest.py'
URL = 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v9.8.7/'
ICON = 'https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/' + 'a'*40 + '/assets/icons/installer-256.png'
SOURCE = 'https://github.com/Razdva122/clean-your-tv-lg-webos'
def encoded(value): return json.dumps(value, sort_keys=True).encode()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def inventory(files): return {n: {'size':len(v), 'sha256':digest(v)} for n,v in files.items()}

def fixture(version='1.2.3'):
    files={}; components={}; versions={}; packages={}
    for key, app in IDENTITIES.items():
        name=key+'.ipk'; version_value='2.3.4'
        info={'id':app,'version':version_value}
        if key == 'root':
            info.update(cytvProductGeneration=2,visible=False)
        content={name: package.ipk(app,version_value,{'usr/palm/applications/'+app+'/appinfo.json':encoded(info)}),
                 'must-not-run.py': b'raise RuntimeError("artifact code executed")'}
        if key in ('root', 'root-updater'):
            content['personalize.py'] = b'# Shared Home settings reader fixture.\n'
        bundle = {'files': {n: digest(v) for n, v in content.items()}}
        if key == 'supervisor':
            bundle['product_schema'] = 2
        content['bundle.json'] = encoded(bundle)
        components[key]=inventory(content); versions[key]=version_value; packages[key]=name
        files.update({key+'/'+n:v for n,v in content.items()})
    files['baseline/baseline.json'] = encoded({
        'schema': 2,
        'edition': 'root',
        'components': [{'name': 'root'}, {'name': 'root-infrastructure'}],
    })
    runtime_files={'bin/python3.13':b'not executable on this host','LICENSE':b'Python license fixture'}
    binding={'schema':1,'archive_sha256':python_runtime.SHA256,'files':{n:digest(v) for n,v in runtime_files.items()}}
    runtime_files['.cytv-runtime.json']=encoded(binding)
    files['runtime.tar.gz']=package.tgz(runtime_files,executable={'bin/python3.13'})
    files['runtime-binding.json']=encoded(binding)
    files['runtime-provenance.json']=encoded({'sha256':python_runtime.SHA256,'normalized_sha256':digest(files['runtime.tar.gz'])})
    import io,tarfile
    with tarfile.open(fileobj=io.BytesIO(files['runtime.tar.gz'])) as archive:
        records={m.name:{'size':m.size,'sha256':digest(archive.extractfile(m).read()),'mode':m.mode} for m in archive if m.isfile()}
    files['manifest.json']=encoded({'schema':1,'files':inventory(files),'components':components,'versions':versions,'packages':packages,
        'runtime':{'files':records,'archive_sha256':python_runtime.SHA256}})
    app={'id':APP_ID,'title':'Clean Your TV','type':'web','main':'index.html','version':version}
    return {APP_PREFIX+'appinfo.json':encoded(app),**{APP_PREFIX+'payload/'+n:v for n,v in files.items()}}

def ipk(files=None, version='1.2.3'): return installer_ipk(version,files or fixture(version))

class HomebrewFixture:
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.exists(): raise AssertionError('Homebrew manifest release gate is required')
        spec=importlib.util.spec_from_file_location('homebrew_manifest',SCRIPT)
        cls.release=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.release)
    def setUp(self):
        self.raw=ipk();self.url=URL+APP_ID+'_1.2.3_all.ipk'
    def manifest(self,raw=None):return self.release.manifest(raw or self.raw,self.url,ICON,SOURCE)
    def accepted(self,metadata):
        return {'schema':1,'release':'v9.8.7','version':metadata['version'],'ipk_sha256':digest(self.raw),'manifest_sha256':digest(encoded(metadata)),
                'hardware_acceptance':'Physical TV record reviewed by operator','human_review':'Named maintainer review recorded'}

class HomebrewManifest(HomebrewFixture, unittest.TestCase):
    def test_catalog_filename_matches_installer_and_generated_manifest(self):
        app = json.loads((ROOT / 'homebrew/app/appinfo.json').read_text())
        manifest = self.manifest()
        self.assertEqual(manifest['id'], app['id'])
        entry = ROOT / 'homebrew/catalog' / (manifest['id'] + '.yml')
        self.assertTrue(entry.is_file(), f'Missing catalog entry {entry.name}')

    def test_reads_real_package_and_hashes_without_running_embedded_code(self):
        with patch('subprocess.run',side_effect=AssertionError('must not execute')),patch('subprocess.check_output',side_effect=AssertionError('must not execute')):
            value=self.manifest()
        self.assertEqual({k:value[k] for k in ('id','title','type','version','rootRequired','ipkSize')},
            {'id':APP_ID,'title':'Clean Your TV','type':'web','version':'1.2.3','rootRequired':True,'ipkSize':len(self.raw)})
        self.assertEqual(value['ipkHash']['sha256'],digest(self.raw))
    def test_malformed_identity_and_control_version_drift_fail(self):
        files=fixture(); info=json.loads(files[APP_PREFIX+'appinfo.json']);info['id']='foreign.app';files[APP_PREFIX+'appinfo.json']=encoded(info)
        for raw in (b'broken',ipk(files),ipk(fixture('1.2.4'))):
            with self.subTest(raw=raw[:8]),self.assertRaises((ValueError,KeyError)):self.manifest(raw)
    def test_immutable_https_urls_required(self):
        for url in (self.url.replace('https:','http:'),self.url.replace('/download/v9.8.7/','/latest/download/'),self.url+'?token=x','https://example.org/a.ipk'):
            with self.subTest(url=url),self.assertRaises(ValueError):self.release.manifest(self.raw,url,ICON,SOURCE)
    def test_inner_and_outer_inventories_fail_even_when_outer_hash_recomputed(self):
        for inner in (False,True):
            files=fixture();prefix=APP_PREFIX+'payload/'
            if inner:
                files[prefix+'root/must-not-run.py']=b'changed'
                m=json.loads(files[prefix+'manifest.json']);m['files']['root/must-not-run.py']=inventory({'x':b'changed'})['x'];files[prefix+'manifest.json']=encoded(m)
            else:files[prefix+'root/must-not-run.py']=b'changed'
            with self.subTest(inner=inner),self.assertRaises(ValueError):self.manifest(ipk(files))
    def test_strict_root_and_outer_hash_and_version_are_reverified(self):
        value=self.manifest()
        for changed in ({**value,'rootRequired':False},{**value,'rootRequired':'optional'},{**value,'ipkHash':{'sha256':'0'*64}},{**value,'version':'9.9.9'}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):self.release.verify_manifest(self.raw,changed)
    def test_acceptance_binds_exact_artifacts_and_independent_non_dev_version(self):
        value=self.manifest();raw=encoded(value);approval=self.accepted(value)
        self.release.verify_accepted(self.raw,raw,approval)
        for change in ({'ipk_sha256':'0'*64},{'manifest_sha256':'0'*64},{'version':'1.2.4'},{'hardware_acceptance':''},{'human_review':''}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.release.verify_accepted(self.raw,raw,{**approval,**change})
        dev=ipk(version='0.0.0');metadata=self.release.manifest(dev,URL+APP_ID+'_0.0.0_all.ipk',ICON,SOURCE)
        with self.assertRaises(ValueError):self.release.verify_accepted(dev,encoded(metadata),{**approval,'version':'0.0.0','ipk_sha256':digest(dev),'manifest_sha256':digest(encoded(metadata))})
    def test_checksum_inventory_must_include_manifest_and_ipk(self):
        value=self.manifest();raw=encoded(value);approval=self.accepted(value);name=self.url.rsplit('/',1)[1]
        sums={name:digest(self.raw),'homebrew-manifest.json':digest(raw)}
        self.release.verify_publication(self.raw,raw,approval,sums)
        for removed in (name,'homebrew-manifest.json'):
            with self.subTest(removed=removed),self.assertRaises(ValueError):self.release.verify_publication(self.raw,raw,approval,{k:v for k,v in sums.items() if k!=removed})


class HomebrewReleaseIntegration(HomebrewFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        import runpy
        self.assemble=runpy.run_path(str(ROOT/'scripts/assemble-release.py'))
        self.prepare=runpy.run_path(str(ROOT/'scripts/prepare-release.py'))
    def test_unaccepted_candidate_artifacts_are_omitted_from_public_assembly(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);(folder/'homebrew-candidate').mkdir()
            (folder/'homebrew-candidate'/self.url.rsplit('/',1)[1]).write_bytes(self.raw)
            output=folder/'out';output.mkdir()
            self.assertIsNone(self.assemble['assemble_homebrew'](folder,output,None,{}))
            self.assertEqual(list(output.iterdir()),[])
    def test_accepted_assembly_and_carry_forward_preserve_original_immutable_url(self):
        metadata=self.manifest();raw=encoded(metadata);approval=self.accepted(metadata)
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);candidate=folder/'homebrew-candidate';candidate.mkdir()
            (candidate/self.url.rsplit('/',1)[1]).write_bytes(self.raw)
            (candidate/'homebrew-manifest.json').write_bytes(raw)
            output=folder/'out';output.mkdir()
            result=self.assemble['assemble_homebrew'](folder,output,approval,{})
            self.assertEqual(result,approval)
            files={'homebrew-manifest.json':raw,self.url.rsplit('/',1)[1]:self.raw}
            current={};target=folder/'next';target.mkdir()
            carried=self.prepare['prepare_homebrew'](current,{'homebrew':approval},lambda name:files[name],lambda name:files[name])
            self.assertEqual(current['homebrew'],approval)
            self.assertEqual(carried,files)
            self.assertEqual(json.loads(carried['homebrew-manifest.json'])['ipkUrl'],self.url)
            # Orphan assets from releases with no approved provenance are never adopted.
            self.assertEqual(self.prepare['prepare_homebrew']({}, {},lambda name:self.fail('orphan fetched'),lambda name:self.fail('orphan fetched')),{})
    def test_no_root_release_rejects_different_desktop_bytes_before_copy(self):
        from homebrew.tests.test_installer_package import InstallerPackageTests
        from homebrew.build import NO_ROOT_FILES
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            desktop = folder / 'desktop'
            desktop.mkdir()
            InstallerPackageTests().no_root_payload(desktop)
            reference = {p.name: p.read_bytes() for p in desktop.iterdir()}
            files = fixture()
            prefix = APP_PREFIX + 'payload/'
            files.update({prefix + 'no-root/' + name: raw for name, raw in reference.items()})
            manifest = json.loads(files[prefix + 'manifest.json'])
            manifest['files'].update(inventory({'no-root/' + name: raw for name, raw in reference.items()}))
            files[prefix + 'manifest.json'] = encoded(manifest)
            self.raw = ipk(files)
            candidate = folder / 'homebrew-candidate'
            candidate.mkdir()
            metadata = self.manifest()
            approval = self.accepted(metadata)
            (candidate / self.url.rsplit('/', 1)[1]).write_bytes(self.raw)
            (candidate / 'homebrew-manifest.json').write_bytes(encoded(metadata))
            out = folder / 'result'
            out.mkdir()
            assemble = self.assemble['assemble_homebrew']
            other = dict(reference)
            other['helper.ipk'] += b'changed'
            other['payload.json'] = encoded({'files': {name: digest(other[name]) for name in NO_ROOT_FILES}})
            with self.assertRaisesRegex(ValueError, 'Homebrew differs from desktop: helper.ipk'):
                assemble(folder, out, approval, other)
            self.assertEqual(list(out.iterdir()), [])
            self.assertEqual(assemble(folder, out, approval, reference), approval)

    def test_carried_assets_and_changed_version_require_approval(self):
        metadata=self.manifest();raw=encoded(metadata);approval=self.accepted(metadata)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.prepare['prepare_homebrew']({}, {'homebrew':approval},lambda n:b'changed',lambda n:b'changed')

    def test_publication_rechecks_installer_bytes_and_checksum_membership(self):
        import subprocess
        metadata=self.manifest();raw=encoded(metadata);approval=self.accepted(metadata);name=self.url.rsplit('/',1)[1]
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/name).write_bytes(self.raw);(folder/'homebrew-manifest.json').write_bytes(raw)
            (folder/'BUILD-INFO.json').write_bytes(encoded({'homebrew':approval}))
            sums={name:digest(self.raw),'homebrew-manifest.json':digest(raw)}
            def check(expected=True):
                (folder/'SHA256SUMS').write_text(''.join(v+'  '+k+'\n' for k,v in sums.items()))
                command=['node','-e',"require('./scripts/publish-release.cjs').verifyHomebrewRelease(process.argv[1],JSON.parse(require('fs').readFileSync(process.argv[1]+'/BUILD-INFO.json')))",str(folder)]
                result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode==0,expected,result.stderr)
            check()
            sums.pop('homebrew-manifest.json');check(False)
            sums['homebrew-manifest.json']=digest(raw);(folder/name).write_bytes(b'wrong outer bytes');check(False)

    def test_accepted_promotion_requires_successful_candidate_job(self):
        gate=self.assemble['validate_homebrew_job']
        gate([],False)
        gate([{'name':'homebrew','conclusion':'success'}],True)
        for jobs in ([],[{'name':'homebrew','conclusion':'skipped'}],[{'name':'homebrew','conclusion':'failure'}]):
            with self.subTest(jobs=jobs),self.assertRaises(ValueError):gate(jobs,True)

    def test_unrelated_release_does_not_rebuild_or_promote_old_accepted_installer(self):
        approval=self.accepted(self.manifest())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'homebrew').mkdir()
            (root/'homebrew/release.json').write_bytes(encoded(approval))
            (root/'release-versions.json').write_bytes(encoded({'release':'9.8.8'}))
            self.assertIsNone(self.assemble['selected_homebrew_approval'](root))
            (root/'release-versions.json').write_bytes(encoded({'release':'9.8.7'}))
            self.assertEqual(self.assemble['selected_homebrew_approval'](root),approval)

    def test_publication_fetches_original_immutable_release_and_rejects_changed_bytes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            code="""
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {verifyHomebrewOrigin}=require('./scripts/publish-release.cjs');
const folder=process.argv[1],bytes=Buffer.from('original'),sha256=require('crypto').createHash('sha256').update(bytes).digest('hex');
const installer={tag:'v9.8.7',filename:'io.github.razdva122.cytvinstaller_1.2.3_all.ipk',sha256};
let calls=0;
function download(args){calls++;assert.equal(args[2],'v9.8.7');assert.equal(args[4],installer.filename);fs.writeFileSync(path.join(args[6],installer.filename),calls===1?bytes:Buffer.from('changed'));}
verifyHomebrewOrigin(installer,folder,download);
assert.throws(()=>verifyHomebrewOrigin(installer,folder,download),/homebrew-origin-package-mismatch/);
assert.equal(calls,2);
"""
            result=subprocess.run(['node','-e',code,directory],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_release_approval_must_equal_the_committed_source_record(self):
        import subprocess
        approval=self.accepted(self.manifest())
        self.prepare['verify_homebrew_approval']({'homebrew':approval},approval)
        with self.assertRaises(ValueError):self.prepare['verify_homebrew_approval']({'homebrew':approval},{**approval,'ipk_sha256':'0'*64})
        code="""
const assert=require('assert/strict'),verify=require('./scripts/publish-release.cjs').verifyHomebrewApproval;
const approval={schema:1,release:'v9.8.7',version:'1.2.3',ipk_sha256:'exact',manifest_sha256:'exact',hardware_acceptance:'record',human_review:'record'};
verify({homebrew:approval},approval);
assert.throws(()=>verify({homebrew:approval},{...approval,ipk_sha256:'forged'}),/homebrew-source-approval-mismatch/);
assert.throws(()=>verify({homebrew:approval},null),/homebrew-source-approval-mismatch/);
"""
        result=subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_source_approval_reads_the_exact_git_blob_and_fails_closed(self):
        import subprocess,base64
        approval=self.accepted(self.manifest())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'homebrew').mkdir()
            (root/'homebrew/release.json').write_bytes(encoded(approval))
            def git(*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL)
            git('init');git('add','homebrew/release.json')
            git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','approval')
            commit=git('rev-parse','HEAD').decode().strip()
            def provider(*args):
                ref=args[-1].rsplit('=',1)[1]
                blob=git('show',ref+':homebrew/release.json')
                return encoded({'content':base64.b64encode(blob).decode()})
            with patch.dict(self.prepare['verify_homebrew_source'].__globals__,gh=provider):
                self.prepare['verify_homebrew_source']({'homebrew':approval},commit)
                with self.assertRaises(ValueError):self.prepare['verify_homebrew_source']({'homebrew':{**approval,'version':'9.9.9'}},commit)
                with self.assertRaises(subprocess.CalledProcessError):self.prepare['verify_homebrew_source']({'homebrew':approval},'0'*40)
            code="""
const cp=require('child_process'),assert=require('assert/strict');
const verify=require('./scripts/publish-release.cjs').verifyHomebrewSource;
const repository=process.argv[1],commit=process.argv[2];
function provider(args){const ref=args[1].split('?ref=')[1];const blob=cp.execFileSync('git',['show',ref+':homebrew/release.json'],{cwd:repository,stdio:['ignore','pipe','pipe']});return JSON.stringify({content:blob.toString('base64')});}
const approval=JSON.parse(cp.execFileSync('git',['show',commit+':homebrew/release.json'],{cwd:repository}));
verify({source_commit:commit,homebrew:approval},provider);
assert.throws(()=>verify({source_commit:commit,homebrew:{...approval,version:'9.9.9'}},provider),/homebrew-source-approval-mismatch/);
assert.throws(()=>verify({source_commit:'0'.repeat(40),homebrew:approval},provider));
"""
            result=subprocess.run(['node','-e',code,directory,commit],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_workflow_failure_policy_and_resolver_follow_selected_acceptance(self):
        import os,runpy,textwrap
        from unittest.mock import Mock
        workflow=(ROOT/'.github/workflows/cytv.yml').read_text()
        scope=workflow.split('  scope:\n',1)[1].split('  android:\n',1)[0]
        self.assertIn("homebrew_required: ${{ steps.scope.outputs.homebrew_required }}",scope)
        self.assertIn("continue-on-error: ${{ needs.scope.outputs.homebrew_required != 'true' }}",workflow.split('  homebrew:\n',1)[1])
        code=textwrap.dedent(scope.split("          python - <<'PY'\n",1)[1].split('          PY\n',1)[0])
        required_jobs=runpy.run_path(str(ROOT/'scripts/release-flow.py'))['BUILD_JOBS']
        commit='a'*40
        run={'conclusion':'success','status':'completed','head_sha':commit,'head_branch':'main',
             'event':'push','path':'.github/workflows/cytv.yml','head_repository':{'full_name':'Razdva122/clean-your-tv-lg-webos'},'id':123}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'homebrew').mkdir();output=root/'output'
            (root/'release-versions.json').write_bytes(encoded({'release':'9.8.7'}))
            approval=self.accepted(self.manifest())
            for selected,record in ((False,None),(True,approval),(False,{**approval,'release':'v9.8.6'})):
                with self.subTest(selected=selected,record=record):
                    path=root/'homebrew/release.json'
                    if record is None:
                        if path.exists():path.unlink()
                    else:path.write_bytes(encoded(record))
                    output.write_text('')
                    with patch.dict(os.environ,RELEASE_SOURCE_ROOT=str(root),GITHUB_OUTPUT=str(output)):
                        exec(compile(code,'cytv.yml scope policy','exec'),{})
                        resolver=runpy.run_path(str(ROOT/'scripts/assemble-release.py'))['resolve_build_source']
                    self.assertEqual(output.read_text().strip(),'homebrew_required='+str(selected).lower())
                    # An ignored job can fail while the workflow succeeds. A selected
                    # accepted job remains mandatory even if that overall success is forged.
                    jobs=[{'name':name,'conclusion':'success'} for name in required_jobs]+[{'name':'homebrew','conclusion':'failure'}]
                    with patch.dict(resolver.__globals__,github=Mock(side_effect=[run,jobs])):
                        if selected:
                            with self.assertRaisesRegex(ValueError,'successful exact candidate'):resolver(commit,123)
                        else:self.assertEqual(resolver(commit,123),run)
                    if selected:
                        with patch.dict(resolver.__globals__,github=Mock(return_value={**run,'conclusion':'failure'})):
                            with self.assertRaisesRegex(ValueError,'successful trusted'):resolver(commit,123)

#!/usr/bin/env python3
"""Build a reproducible complete offline bootstrap from verified component bundles."""
import argparse
import hashlib
import json
import importlib.util
import io
import re
import tarfile
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cytv import package, python_runtime
from homebrew.payload import checked_bundle, inventory, read_file, validate_runtime

IDENTITIES={'root':'com.cleanyourtv.root.preview','root-updater':'com.cleanyourtv.root.updater','supervisor':'com.cleanyourtv.system.updater'}

def build_payload(root_bundle, root_updater_bundle, supervisor_bundle, runtime_archive, output):
    output=Path(output).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)): raise ValueError('Unsafe output')
    inputs=dict(zip(IDENTITIES,(root_bundle,root_updater_bundle,supervisor_bundle)))
    components={}; versions={}; package_names={}
    for key,root in inputs.items():
        root=Path(root);components[key]=checked_bundle(root)
        ipks=[n for n in components[key] if n.endswith('.ipk')]
        if len(ipks)!=1: raise ValueError('Expected one component package')
        package_names[key]=ipks[0]
        files=package.data_files(read_file(root/ipks[0]))
        app=IDENTITIES[key]
        info=json.loads(files['usr/palm/applications/'+app+'/appinfo.json'])
        if info.get('id')!=app: raise ValueError('Component identity mismatch')
        versions[key]=info['version']
    # Shared protocol/binding sources must come from the same component baseline.
    for name in ('installation.py','observed_install.py','installer_status.py','startup_hook.py','package_data.py','package_identity.py','startup_guard.py','python_binding.py','python_boot.js'):
        hashes={components[key].get(name,{}).get('sha256') for key in inputs}
        if len(hashes)!=1 or None in hashes: raise ValueError('Mismatched component baseline: '+name)
    for name in ('store.py','package.py'):
        hashes={components[key].get(('system_updater/support/' if key=='supervisor' else 'updater/')+name,{}).get('sha256') for key in inputs}
        if len(hashes)!=1 or None in hashes: raise ValueError('Mismatched component parser baseline: '+name)
    # Reuse each component's authoritative inventory contract, including required files.
    project=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(project/'root-edition'))
    from deploy import verify_bundle as verify_root
    from updater.bootstrap import verify_bundle as verify_updater
    verify_root(root_bundle);verify_updater(root_updater_bundle)
    spec=importlib.util.spec_from_file_location('homebrew_supervisor_setup',project/'system-updater/setup.py')
    setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    setup.verify_bundle(supervisor_bundle)
    raw=python_runtime._verified_bytes(Path(runtime_archive))
    output.mkdir()
    try:
        for key,root in inputs.items():
            for name in components[key]:
                target=output/key/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(read_file(Path(root)/name))
        spec=importlib.util.spec_from_file_location('homebrew_supervisor_builder',Path(__file__).resolve().parents[1]/'system-updater/build.py')
        supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
        supervisor.prepare_baseline(output,'root',output/'baseline')
        binding=python_runtime.normalize_to_file(raw,output/'runtime.tar.gz')
        runtime_files=validate_runtime(output/'runtime.tar.gz',binding)
        (output/'runtime-binding.json').write_text(json.dumps(binding,sort_keys=True,separators=(',',':')))
        provenance={'url':python_runtime.URL,'sha256':python_runtime.SHA256,'size':python_runtime.SIZE,
                    'license':'Python-2.0; included runtime LICENSE and component licenses',
                    'normalized_sha256':hashlib.sha256(read_file(output/'runtime.tar.gz')).hexdigest()}
        if not any(n=='LICENSE' or n.endswith('/LICENSE') for n in runtime_files): raise ValueError('Runtime license missing')
        (output/'runtime-provenance.json').write_text(json.dumps(provenance,sort_keys=True,separators=(',',':')))
        (output/'runtime.js').write_bytes(read_file(Path(__file__).with_name('runtime.js')))
        bootstrap={'shell':python_runtime._SHELL,'smoke':python_runtime.SMOKE,'inspect_probe':python_runtime._PROBE_BODY.split('with tempfile.TemporaryDirectory')[0]+"\nprint('CYTV_SYSTEM_PYTHON')\n",'system_probe':python_runtime.SYSTEM_PROBE,'promote':python_runtime._PROMOTE}
        (output/'runtime-bootstrap.json').write_text(json.dumps(bootstrap,sort_keys=True,separators=(',',':')))
        manifest={'schema':1,'files':inventory(output),'components':components,'versions':versions,'packages':package_names,
                  'runtime':{'archive_sha256':python_runtime.SHA256,'files':runtime_files,
                             'max_unpacked':python_runtime.MAX_UNPACKED,'max_files':python_runtime.MAX_FILES,
                             'required_space':320*1024*1024}}
        (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
        return output/'manifest.json'
    except BaseException:
        shutil.rmtree(output);raise

APP_ID='com.cleanyourtv.installer'
APP_PREFIX='usr/palm/applications/'+APP_ID+'/'
PACKAGE_INFO='usr/palm/packages/'+APP_ID+'/packageinfo.json'


def installer_files(raw):
    """Dedicated bounded installer reader; ordinary IPK 16 MiB limits stay intact."""
    if len(raw)>128*1024*1024:raise ValueError('Installer package is too large')
    parts=package.read_ar(raw)
    if set(parts)!={'debian-binary','control.tar.gz','data.tar.gz'} or parts['debian-binary']!=b'2.0\n':raise ValueError('Invalid installer archive')
    result={};seen=set();total=0
    with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']),mode='r:gz') as archive:
        for entry in archive:
            name=entry.name.rstrip('/') if entry.isdir() else entry.name
            package.safe_name(name)
            if name in seen or len(seen)>=36000:raise ValueError('Duplicate or excessive installer entries')
            seen.add(name)
            if entry.isdir():
                if not (APP_PREFIX.startswith(name+'/') or name.startswith(APP_PREFIX) or PACKAGE_INFO.startswith(name+'/')):raise ValueError('Foreign installer directory')
                continue
            # Root media exceeds ordinary limits in both the component and rollback cache.
            root_ipk=re.fullmatch(re.escape(APP_PREFIX+'payload/root/'+IDENTITIES['root'])+r'_(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)_all\.ipk',name)
            baseline_cache=re.fullmatch(re.escape(APP_PREFIX+'payload/baseline/cache/')+r'[0-9a-f]{64}',name)
            limit=64*1024*1024 if name==APP_PREFIX+'payload/runtime.tar.gz' or root_ipk or baseline_cache else 16*1024*1024
            if not entry.isfile() or entry.size<0 or entry.size>limit or not (name.startswith(APP_PREFIX) or name==PACKAGE_INFO):raise ValueError('Unsupported installer member')
            total+=entry.size
            if total>256*1024*1024:raise ValueError('Installer content is too large')
            result[name]=archive.extractfile(entry).read()
    return result


def installer_metadata(raw):
    """Read final installer metadata without relaxing component package parsers."""
    files=installer_files(raw)
    info=json.loads(files.get(APP_PREFIX+'appinfo.json',b'{}'))
    if (info.get('id'),info.get('title'),info.get('type'),info.get('main'))!=(APP_ID,'CYTV Installer','web','index.html'):raise ValueError('Invalid installer identity')
    if not isinstance(info.get('version'),str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',info['version']) or len(info['version'])>32:raise ValueError('Invalid installer version')
    control=None
    parts=package.read_ar(raw)
    if len(parts['control.tar.gz'])>1024*1024:raise ValueError('Oversized control')
    with tarfile.open(fileobj=io.BytesIO(parts['control.tar.gz']),mode='r:gz') as archive:
        for entry in archive:
            if entry.isdir():continue
            if entry.name!='control' or not entry.isfile() or entry.size>65536 or control is not None:raise ValueError('Invalid installer control')
            control=archive.extractfile(entry).read().decode('utf-8')
    fields=dict(line.split(': ',1) for line in (control or '').splitlines() if ': ' in line)
    if fields.get('Package')!=APP_ID or fields.get('Version')!=info['version']:raise ValueError('Installer control mismatch')
    return info


def verify_offline(payload):
    """Reuse the exact component/runtime contracts before packaging any bytes."""
    payload=Path(payload)
    manifest=json.loads(read_file(payload/'manifest.json'))
    actual=inventory(payload);actual.pop('manifest.json')
    if manifest.get('schema')!=1 or actual!=manifest.get('files'):raise ValueError('Offline inventory mismatch')
    for name in IDENTITIES:
        if checked_bundle(payload/name)!=manifest['components'][name]:raise ValueError('Offline component mismatch')
    binding=json.loads(read_file(payload/'runtime-binding.json'))
    records=validate_runtime(payload/'runtime.tar.gz',binding)
    if records!=manifest['runtime']['files'] or manifest['runtime']['archive_sha256']!=python_runtime.SHA256:raise ValueError('Offline runtime mismatch')
    provenance=json.loads(read_file(payload/'runtime-provenance.json'))
    if provenance.get('sha256')!=python_runtime.SHA256 or provenance.get('normalized_sha256')!=actual['runtime.tar.gz']['sha256']:raise ValueError('Offline provenance mismatch')
    return manifest


def build_installer(payload, output, version='0.0.0'):
    from scripts.tv_web_build import compile_web
    if not isinstance(version,str) or len(version)>32 or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',version):raise ValueError('Invalid installer version')
    output=Path(output).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('Unsafe output')
    manifest=verify_offline(payload)
    source=Path(__file__).parent;project=source.parent
    app={name:read_file(source/'app'/name) for name in ('appinfo.json','index.html','app.js','bridge.js','style.css','i18n.js')}
    info=json.loads(app['appinfo.json']);info['version']=version
    app['appinfo.json']=(json.dumps(info,sort_keys=True)+'\n').encode()
    app['candidate.js']=('window.InstallerCandidate='+json.dumps(manifest['versions'],sort_keys=True)+';\n').encode()
    app['index.html']=app['index.html'].replace(b'<script src="i18n.js">',b'<script src="candidate.js"></script><script src="i18n.js">')
    # Existing installer icon provenance: assets/icons/README.md (installer.svg).
    app['icon.png']=read_file(project/'assets/icons/installer-256.png')
    for name in ('NotoSans.ttf','NotoSans-OFL.txt','NotoSansDevanagari.ttf','NotoSansDevanagari-OFL.txt','NotoSansKR.ttf','NotoSansKR-OFL.txt','NotoSansSC.ttf','NotoSansSC-OFL.txt','NotoSansTC.ttf','NotoSansTC-OFL.txt'):
        app['fonts/'+name]=read_file(project/'launcher/fonts'/name)
    # Backend and offline runtime are deliberately added AFTER web compilation.
    files={APP_PREFIX+name:raw for name,raw in compile_web(app).items()}
    files[APP_PREFIX+'bootstrap.js']=read_file(source/'bootstrap.js').replace(b'__CYTV_PAYLOAD_SHA256__',hashlib.sha256(read_file(Path(payload)/'manifest.json')).hexdigest().encode())
    for name in (*manifest['files'],'manifest.json'):files[APP_PREFIX+'payload/'+name]=read_file(Path(payload)/name)
    files[PACKAGE_INFO]=(json.dumps({'id':APP_ID,'version':version,'app':APP_ID,'services':[]},sort_keys=True)+'\n').encode()
    raw=package.ipk(APP_ID,version,files)
    installer_metadata(raw)
    if installer_files(raw)!=files:raise ValueError('Final installer bytes differ')
    output.mkdir()
    try:
        target=output/(APP_ID+'_'+version+'_all.ipk');target.write_bytes(raw)
        metadata={'schema':1,'application_id':APP_ID,'version':version,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'payload_manifest_sha256':hashlib.sha256(read_file(Path(payload)/'manifest.json')).hexdigest(),'payload_bytes':sum(record['size'] for record in manifest['files'].values()),'required_runtime_free_bytes':manifest['runtime']['required_space'],'hardware_validated':False}
        (output/'installer-build.json').write_text(json.dumps(metadata,sort_keys=True,indent=2)+'\n')
        return target
    except BaseException:
        shutil.rmtree(output);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer-payload',type=Path,help='Package an already built complete offline payload')
    parser.add_argument('--version',default='0.0.0',help='Separate installer development/candidate version')
    for name in ('root-bundle','root-updater-bundle','supervisor-bundle','runtime-archive'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=vars(parser.parse_args());payload=args.pop('installer_payload');version=args.pop('version')
    if payload:
        if any(args[name] is not None for name in ('root_bundle','root_updater_bundle','supervisor_bundle','runtime_archive')):parser.error('Choose payload build or installer packaging')
        print(build_installer(payload,args['output'],version))
    else:
        if any(value is None for value in args.values()):parser.error('All component bundles and runtime archive are required')
        print(build_payload(**args))

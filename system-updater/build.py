#!/usr/bin/env python3
"""Reproducible independent supervisor, offline baselines and public release sets."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cytv import package

SERVICE='com.cleanyourtv.system.updater.service'
APP='com.cleanyourtv.system.updater'
VERSION='1.1.2'
APPS={'home':'com.gathin.tvhome','helper':'com.local.nativehome','updater':'com.cleanyourtv.updater','root':'com.cleanyourtv.root.preview','root-updater':'com.cleanyourtv.root.updater'}

def digest(raw):return hashlib.sha256(raw).hexdigest()

def source(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():raise ValueError('Missing or indirect source: '+str(path))
    return path.read_bytes()

def assigned(path,name):
    for node in ast.parse(source(path)).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):return ast.literal_eval(node.value)
    raise ValueError('Missing inventory')


def build(output, legacy_node_prototype=False):
    output=Path(output).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('Indirect output')
    code={'system_updater/__init__.py':b'', 'system_updater/support/__init__.py':b''}
    for name in ('core.py','device.py','cli.py','policy.js'):
        code['system_updater/'+name]=source(ROOT/'system-updater'/name)
    for name in ('store.py','package.py','profile.py','luna.py'):
        code['system_updater/support/'+name]=source(ROOT/'root-edition/updater'/name)
    for name in ('startup_hook.py','package_data.py','package_identity.py','startup_guard.py','installation.py','observed_install.py','installer_status.py','python_binding.py','python_boot.js'):
        code[name]=source(ROOT/'root-edition'/name)
    for name in ('release-public.pem','ca-bundle.crt','ca-LICENSE.txt'):
        code['system_updater/'+name]=source(ROOT/'updater-service'/name)
    runtime=assigned(ROOT/'root-edition/deploy.py','RUNTIME_FILES')
    updater=assigned(ROOT/'root-edition/build_updater.py','UPDATER_FILES')
    support=assigned(ROOT/'root-edition/build_updater.py','SUPPORT')+assigned(ROOT/'root-edition/build_updater.py','COORDINATOR_FILES')
    private=assigned(ROOT/'root-edition/provision.py','PRIVATE_FILES')
    infra=['support/python_binding.py','support/python_boot.js','support/package_data.py','support/package_identity.py','support/updater/store.py','support/updater/package.py','support/startup_guard.py']+['service/'+n for n in private]+['runtime/'+n for n in runtime]+['updater/updater/'+n for n in updater]+['updater/'+n for n in support]+['updater/updater/release-public.pem','updater/service.js','updater/run-updater.py','updater/services.json','updater/package.json']
    code['infrastructure-paths.json']=(json.dumps(sorted(infra))+'\n').encode()
    code['service.js']=source(ROOT/'system-updater/service.js')
    code['run-system-updater.py']=b'from system_updater.cli import entry\nentry()\n'
    code['services.json']=(json.dumps({'id':SERVICE,'services':[{'name':SERVICE}]})+'\n').encode()
    code['package.json']=(json.dumps({'name':SERVICE,'version':VERSION,'main':'service.js'})+'\n').encode()
    sp='usr/palm/services/'+SERVICE+'/'
    ap='usr/palm/applications/'+APP+'/'
    files={sp+'service.js':b"'use strict';require('/var/lib/clean-your-tv-system-updater/code/service.js');\n",
           sp+'package.json':code['package.json'], sp+'services.json':code['services.json'],
           ap+'appinfo.json':json.dumps({'id':APP,'version':VERSION,'type':'web','main':'index.html','title':'System Updater','visible':False,'icon':'icon.png'}).encode(),
           ap+'index.html':b'<!doctype html><title>System Updater</title><p>Open Software updates from Home.</p>',
           ap+'icon.png':source(ROOT/'updater-app/updater-icon.png') if (ROOT/'updater-app/updater-icon.png').exists() else source(ROOT/'assets/icons/installer.png'),
           'usr/palm/packages/'+APP+'/packageinfo.json':json.dumps({'id':APP,'version':VERSION,'app':APP,'services':[SERVICE]}).encode()}
    sys.path.insert(0,str(ROOT/'root-edition'))
    from startup_hook import packaged_content
    files[ap+'startup.sh']=packaged_content(APP)
    code['system-updater.ipk']=package.ipk(APP,VERSION,files,executable={ap+'startup.sh'})
    code['setup-system-updater.py']=source(ROOT/'system-updater/setup.py')
    if legacy_node_prototype:
        from scripts.root_node_build import compile_root_node
        code = compile_root_node(code)
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in code.items():
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    (output/'bundle.json').write_text(json.dumps({'schema':1,'supervisor':1,'health_lock_wait_seconds':10,'files':{n:digest(b) for n,b in sorted(code.items())}},indent=2)+'\n')
    return output/'system-updater.ipk'

def component(name,raw,local=True,release=None):
    result={'name':name,'kind':'ipk','application':APPS[name],'sha256':digest(raw),'size':len(raw)}
    info=json.loads(package.data_files(raw)['usr/palm/applications/'+APPS[name]+'/appinfo.json'])
    if info['id']!=APPS[name]:raise ValueError('Package identity mismatch')
    result['version']=info['version']
    if local:result['local']=True
    else:
        arch='arm' if name=='helper' else 'all'
        result['url']='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/'+release+'/'+APPS[name]+'_'+info['version']+'_'+arch+'.ipk'
    return result

def infrastructure(payload):
    files={}
    for folder,prefix in (('root',''),('root-updater','updater/')):
        root=Path(payload)/folder
        manifest=json.loads(source(root/'bundle.json'))
        for name,expected in manifest['files'].items():
            package.safe_name(name)
            if (folder=='root' and not name.startswith('runtime/')) or (folder=='root-updater' and name in ('root-updater.ipk','setup-updater.py')):continue
            raw=source(root/name)
            if digest(raw)!=expected:raise ValueError('Infrastructure bundle hash mismatch')
            files[prefix+name]=raw
    root=Path(payload)/'root';manifest=json.loads(source(root/'bundle.json'))
    for name in ('python_binding.py','python_boot.js','package_data.py','package_identity.py','updater/store.py','updater/package.py','startup_guard.py'):
        binding=source(root/name)
        if digest(binding)!=manifest['files'].get(name):raise ValueError('Root Python binding helper hash mismatch')
        files['support/'+name]=binding
    raw=source(root/manifest['package'])
    if manifest['package'] in manifest['files'] and digest(raw)!=manifest['files'][manifest['package']]:raise ValueError('Root package hash mismatch')
    package_files=package.data_files(raw)
    for name in assigned(ROOT/'root-edition/provision.py','PRIVATE_FILES'):
        files['service/'+name]=package_files['usr/palm/services/com.cleanyourtv.root.preview.service/'+name]
    return package.tgz(files,directories=False),{n:digest(b) for n,b in sorted(files.items())}

def release_set(payload,edition,release,local=True,notes='Computer-provisioned baseline.'):
    if edition not in ('root','no-root'):raise ValueError('Invalid edition')
    payload=Path(payload);raws={}
    if edition=='no-root':
        for name,filename in (('home','launcher.ipk'),('helper','helper.ipk'),('updater','updater.ipk')):
            raws[name]=source(payload/filename)
    if edition=='root':
        root=json.loads(source(payload/'root/bundle.json'))
        raws['root']=source(payload/'root'/root['package'])
        raws['root-updater']=source(payload/'root-updater/root-updater.ipk')
    components=[component(n,b,local,release) for n,b in raws.items()]
    if edition=='root':
        raw,files=infrastructure(payload);raws['root-infrastructure']=raw
        item={'name':'root-infrastructure','kind':'infrastructure','version':components[-2]['version'],'sha256':digest(raw),'size':len(raw)}
        if local:item.update(local=True,files=files,absent=[])
        else:item['url']='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/'+release+'/root-infrastructure_'+item['version']+'.tar.gz'
        components.append(item)
    manifest={'schema':1,'edition':edition,'release':release,'supervisor':1,'notes':notes,'components':components}
    if edition=='root' and not local:manifest['minimumSupervisorVersion']='1.1.1'
    return manifest,raws

def prepare_baseline(payload,edition,output,release=None):
    release=release or 'v'+json.loads((ROOT/'release-versions.json').read_text())['release']
    manifest,raws=release_set(payload,edition,release)
    output=Path(output);output.mkdir(parents=True,exist_ok=False);(output/'cache').mkdir()
    for item in manifest['components']:(output/'cache'/item['sha256']).write_bytes(raws[item['name']])
    (output/'baseline.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return output

def prepare_release(payload,output,release,notes):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifests={}
    for edition in ('root','no-root'):
        manifest,raws=release_set(payload,edition,release,local=False,notes=notes)
        manifests[edition]=manifest
        for item in manifest['components']:
            filename=item['url'].rsplit('/',1)[1];raw=raws[item['name']];target=output/filename
            if target.exists() and target.read_bytes()!=raw:raise ValueError('Release asset collision')
            target.write_bytes(raw)
    (output/'system-manifests.json').write_text(json.dumps(manifests,indent=2)+'\n')
    return manifests

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--legacy-node-prototype',action='store_true',help='Host-only Node 0.12 prototype; admission remains Node 8+')
    args=parser.parse_args()
    print(build(args.output,legacy_node_prototype=args.legacy_node_prototype))

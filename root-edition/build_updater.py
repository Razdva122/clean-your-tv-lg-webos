#!/usr/bin/env python3
"""Build a separate Root Updater and its explicit one-time host setup bundle."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
UPDATER_FILES=('core.py','store.py','profile.py','device.py','package.py','cli.py','fetch.js','bridge.js','luna.py','bootstrap.py','ca-bundle.crt','ca-LICENSE.txt')
SUPPORT=('installation.py','observed_install.py','installer_status.py','provision.py','deploy.py','setup.py','system_permissions.py','activity.py','startup_hook.py','package_data.py','package_identity.py','startup_guard.py','python_binding.py','python_boot.js')
COORDINATOR_FILES=('coordinator_inventory.py', 'install_driver.py', 'install_device.py', 'system_setup.py', 'root_package.py', 'app-inventory.js', 'cleanup_root_updater.py', 'cleanup_system_updater.py', 'cleanup_legacy_permissions.py', 'cleanup_app_permissions.py', 'cleanup_root_archive.py', 'system_updater/__init__.py', 'system_updater/core.py', 'system_updater/device.py', 'system_updater/support/__init__.py', 'system_updater/support/package.py', 'system_updater/support/store.py', 'system_updater/support/profile.py', 'system_updater/support/luna.py')
APP='com.cleanyourtv.root.updater'


def source(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():raise ValueError('Missing or indirect updater source')
    return path.read_bytes()


def build(output, legacy_node_prototype=False):
    version=json.loads(source(ROOT.parent/'release-versions.json'))['updater']
    output=Path(output).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('Indirect build output')
    spec=importlib.util.spec_from_file_location('root_ipk_builder',ROOT/'build.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    code={'updater/'+name:source(ROOT/'updater'/name) for name in UPDATER_FILES}
    code.update({name:source(ROOT/name) for name in SUPPORT})
    for name in ('coordinator_inventory.py','install_driver.py','install_device.py'):
        code[name]=source(ROOT/name)
    code['system_setup.py']=source(ROOT.parent/'system-updater/setup.py')
    code['root_package.py']=source(ROOT.parent/'cytv/package.py')
    code['app-inventory.js']=source(ROOT/'service/app-inventory.js')
    import sys
    sys.path.insert(0,str(ROOT.parent))
    sys.path.insert(0,str(ROOT))
    from cytv import root_updater_remove, system_updater_remove, legacy_permissions_remove, app_permissions_remove, root_archive
    for name,module in (('root_updater',root_updater_remove),('system_updater',system_updater_remove),('legacy_permissions',legacy_permissions_remove),('app_permissions',app_permissions_remove),('root_archive',root_archive)):
        code['cleanup_'+name+'.py']=module.SCRIPT.encode()
    code['system_updater/__init__.py']=b''
    code['system_updater/support/__init__.py']=b''
    for name in ('core.py','device.py'):
        code['system_updater/'+name]=source(ROOT.parent/'system-updater'/name)
    for name in ('package.py','store.py','profile.py','luna.py'):
        code['system_updater/support/'+name]=source(ROOT/'updater'/name)
    code['updater/release-public.pem']=source(ROOT.parent/'updater-service/release-public.pem')
    code['service.js']=source(ROOT/'updater/service.js')
    code['run-updater.py']=b'from updater.cli import entry\nentry()\n'
    code['services.json']=(json.dumps({'id':APP+'.service','services':[{'name':APP+'.service'}]})+'\n').encode()
    code['package.json']=(json.dumps({'name':APP+'.service','version':version,'main':'service.js'})+'\n').encode()
    code['setup-updater.py']=source(ROOT/'setup_updater.py')
    files={}
    prefix='usr/palm/applications/'+APP+'/'
    app={'id':APP,'version':version,'vendor':'Clean Your TV','type':'web','main':'index.html','title':'Root Updater','icon':'root-updater-icon.png','largeIcon':'root-updater-largeIcon.png','iconColor':'#241d19','titleVisible':True,'noSplashOnLaunch':True,'disableBackHistoryAPI':True,'requiredPermissions':[]}
    from startup_hook import packaged_content
    files[prefix+'startup.sh']=packaged_content(APP)
    files[prefix+'appinfo.json']=(json.dumps(app)+'\n').encode()
    files[prefix+'root-updater-icon.png']=source(ROOT/'assets/updater.png')
    files[prefix+'root-updater-largeIcon.png']=source(ROOT/'assets/updater-large.png')
    files[prefix+'root-settings.css']=source(ROOT/'ui/root-settings.css')
    files[prefix+'i18n.js']=source(ROOT.parent/'launcher/i18n.js')
    for name in ('catalogs.js', 'i18n.css', 'fonts/NotoSans.ttf', 'fonts/NotoSans-OFL.txt', 'fonts/NotoSansDevanagari.ttf', 'fonts/NotoSansDevanagari-OFL.txt', 'fonts/NotoSansKR.ttf', 'fonts/NotoSansKR-OFL.txt', 'fonts/NotoSansSC.ttf', 'fonts/NotoSansSC-OFL.txt', 'fonts/NotoSansTC.ttf', 'fonts/NotoSansTC-OFL.txt'):
        files[prefix+name]=source(ROOT.parent/'launcher'/name)
    files[prefix+'root-locales.js']=source(ROOT/'ui/root-locales.js')
    files[prefix+'release-notes.js']=source(ROOT.parent/'launcher/release-notes.js')
    files[prefix+'system-updates.js']=source(ROOT.parent/'launcher/system-updates.js')
    files[prefix+'root-updates.js']=source(ROOT/'ui/root-updates.js')
    files[prefix+'index.html']=b'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=1920"><title>Root Updater</title><link rel="stylesheet" href="root-settings.css"><link rel="stylesheet" href="i18n.css"></head><body style="background:#10121a;color:white"><script src="i18n.js"></script><script src="catalogs.js"></script><script src="root-locales.js"></script><script src="release-notes.js"></script><script src="system-updates.js"></script><script src="root-updates.js"></script><script>HomeI18n.ready(function(){document.title=HomeI18n.t("Root Updater");function openRecovery(failed){RootUpdates.open({recovery:true,standalone:true,error:failed?"Could not open Home.":"",onClose:function(){var bridge=new PalmServiceBridge();bridge.onservicecallback=function(raw){bridge.cancel();try{if(JSON.parse(raw).returnValue!==true)openRecovery(true);}catch(_){openRecovery(true);}};bridge.call("luna://com.webos.applicationManager/launch",JSON.stringify({id:"com.cleanyourtv.root.preview"}));}});}document.addEventListener("webOSRelaunch",function(){openRecovery();});document.addEventListener("visibilitychange",function(){if(!document.hidden&&!RootUpdates.isOpen())openRecovery();});openRecovery();});</script></body></html>\n'
    sp='usr/palm/services/'+APP+'.service/'
    compiled=builder.compile_web({name[len(prefix):]:raw for name,raw in files.items() if name.startswith(prefix)})
    files.update({prefix+name:raw for name,raw in compiled.items()})
    files[sp+'service.js']=b"'use strict';require('/var/lib/clean-your-tv-root-updater/code/service.js');\n"
    files[sp+'package.json']=code['package.json'];files[sp+'services.json']=code['services.json']
    files['usr/palm/packages/'+APP+'/packageinfo.json']=(json.dumps({'id':APP,'version':version,'app':APP,'services':[APP+'.service']})+'\n').encode()
    control=('Package: '+APP+'\nVersion: '+version+'\nSection: misc\nPriority: optional\nArchitecture: all\nMaintainer: Clean Your TV\nDescription: Independent Root application updater and recovery\n').encode()
    code['root-updater.ipk']=builder.ar({'debian-binary':b'2.0\n','control.tar.gz':builder.tgz({'control':control}),'data.tar.gz':builder.tgz(files,{prefix+'startup.sh'})})
    if legacy_node_prototype:
        from scripts.root_node_build import compile_root_node
        code = compile_root_node(code)
    output.mkdir(exist_ok=False)
    for name,raw in code.items():
        target=output/name;target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
    (output/'bundle.json').write_text(json.dumps({'schema':1,'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(code.items())}},indent=2)+'\n')
    return output/'root-updater.ipk'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--legacy-node-prototype',action='store_true',help='Host-only Node 0.12 prototype; admission remains Node 8+')
    args=parser.parse_args()
    print(build(args.output,legacy_node_prototype=args.legacy_node_prototype))

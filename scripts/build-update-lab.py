#!/usr/bin/env python3
"""Build disposable update fixtures locally. Never connects to a TV."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
stage=ROOT/'build/update-lab';out=ROOT/'dist/update-lab'
if stage.exists(): shutil.rmtree(stage)
if out.exists(): shutil.rmtree(out)
stage.mkdir(parents=True);out.mkdir(parents=True)
app='com.cleanyourtv.updatetest';updater='com.cleanyourtv.updaterlab'
cli=os.environ.get('ARES_PACKAGE','ares-package')
def clone(source,name):
    dest=stage/name;shutil.copytree(ROOT/source,dest,ignore=shutil.ignore_patterns('state','node_modules'))
    for p in dest.rglob('*'):
        if p.is_file() and p.suffix in ('.js','.json','.html'):
            p.write_text(p.read_text().replace('com.gathin.tvhome',app).replace('com.cleanyourtv.updater',updater))
    return dest
def package(*dirs): subprocess.run([cli,*map(str,dirs),'-o',str(out)],check=True,cwd=ROOT)
renewal=clone('renewal-service','renewal')
p=renewal/'service.js';s=p.read_text()
# Fixture only: no token reads, LG HTTP requests, or real scheduled activities.
s,count=re.subn(r'\breturn\s+worker\.run\(\s*\)\s*;',"return Promise.resolve({status:'healthy',remainingSeconds:300000});",s)
if count!=1:raise ValueError('Expected one renewal worker fixture')
s,count=re.subn(r'(?ms)^\s*schedule:\s*function\s*\(\s*\)\s*\{.*?^\}\);',
    " schedule:function(){return Promise.resolve({returnValue:true});},\n cancel:function(){return Promise.resolve({returnValue:true});}\n});",s)
if count!=1:raise ValueError('Expected one renewal activity fixture')
p.write_text(s)
for version in ('1.2.0','1.2.1'):
    home=clone('launcher','home-'+version)
    for p in home.glob('*.js'): p.write_text(p.read_text().replace(json.loads((ROOT/'launcher/appinfo.json').read_text())['version'],version))
    p=home/'appinfo.json';info=json.loads(p.read_text());info.update(id=app,version=version,title='Update Test '+version,supportGIP=False);p.write_text(json.dumps(info))
    p=home/'index.html';p.write_text(p.read_text().replace('<script src="native-bootstrap.js"></script>','').replace('<script src="helper-control.js"></script>',''))
    for name in ('native-bootstrap.js','helper-control.js'): (home/name).unlink(missing_ok=True)
    (home/'apps.js').write_text('window.TV_APPS='+json.dumps({'apps':[{'id':'com.webos.app.browser','title':'Test Browser Tile','icon':'brand-v2-icon.png'}] if version=='1.2.0' else [],'inputs':[]})+';')
    package(home,renewal)
service=clone('updater-service','service');ui=clone('updater-app','updater')
for name in ('i18n.js', 'catalogs.js', 'i18n.css'):
    shutil.copy2(ROOT/'launcher'/name, ui/name)
shutil.copy2(ROOT/'root-edition/ui/root-locales.js', ui/'root-locales.js')
(ui/'fonts').mkdir(exist_ok=True)
for font in (ROOT/'launcher/fonts').glob('NotoSans*'):
    shutil.copy2(font, ui/'fonts'/font.name)
p=ui/'appinfo.json';info=json.loads(p.read_text());info.update(title='Updater Lab');p.write_text(json.dumps(info))
p=service/'service.js';s,count=re.subn(r"await\s+require\(\s*(['\"])\./transport\1\s*\)\.get\(\s*channel(?:\s*\+\s*\(\s*resolution\s*===\s*['\"]1280x720['\"]\s*\?\s*['\"]update-720p\.json['\"]\s*:\s*['\"]update\.json['\"]\s*\))?\s*\)","fs.readFileSync(__dirname+'/update.json','utf8')",p.read_text())
if count!=1:raise ValueError('Expected one updater feed fixture')
s,count=re.subn(r"\bhelper\s*:\s*\(\s*await\s+app\(\s*(['\"])com\.local\.nativehome\1\s*\)\s*\)\.version","helper:'0.6.13'",s)
if count!=1:raise ValueError('Expected one Helper version fixture')
p.write_text(s)
p=service/'policy.js';p.write_text(p.read_text().replace('https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/','http://127.0.0.1:18999/'))
# An ephemeral lab key never leaves this process. The production key is not used.
subprocess.run(['node','-e',r'''
const fs=require('fs'),crypto=require('crypto'),path=require('path');const [dir,out]=process.argv.slice(1);
const keys=crypto.generateKeyPairSync('rsa',{modulusLength:2048});fs.writeFileSync(path.join(dir,'release-public.pem'),keys.publicKey.export({type:'spki',format:'pem'}));
function signed(home,release){const file='com.cleanyourtv.updatetest_'+home+'_all.ipk';const m={schema:1,home,release,helper:'0.6.13',url:'http://127.0.0.1:18999/'+release+'/'+file,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,file))).digest('hex'),notes:'Disposable local update test; no production apps are modified.'};const bytes=Buffer.from(JSON.stringify(m));return {payload:bytes.toString('base64'),signature:crypto.sign('RSA-SHA256',bytes,keys.privateKey).toString('base64')};}
const metadata=signed('1.2.1','v0.8.1');metadata.previous=signed('1.2.0','v0.8.0');fs.writeFileSync(path.join(dir,'update.json'),JSON.stringify(metadata));
''',str(service),str(out)],check=True)
package(ui,service)
for version,release in (('1.2.0','v0.8.0'),('1.2.1','v0.8.1')):
    dest=out/'http'/release;dest.mkdir(parents=True);shutil.copy2(out/(app+'_'+version+'_all.ipk'),dest)
# Copy only the setup program and the modules it requires, never keys/state.
for name in ('scripts/update-permissions.cjs','scripts/lib/update-permissions.cjs','updater-service/permissions.js'):
    dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.glob('*.ipk'))))
print('Built isolated lab in',out)

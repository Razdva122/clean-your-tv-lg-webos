'use strict';
const assert=require('node:assert/strict'),crypto=require('node:crypto');
const {signFeeds}=require('../../scripts/sign-release-feeds.cjs');
const policy=require('../../system-updater/policy');
const {privateKey,publicKey}=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
const base='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.0.3/';
const descriptor=(name,application)=>({name,application,version:'1.0.0',kind:'ipk',url:base+application+'_1.0.0_all.ipk',sha256:'a'.repeat(64),size:12});
const set=(edition,components)=>({schema:1,release:'v1.0.3',edition,supervisor:1,notes:'Changes',components,...(edition==='root'?{minimumSupervisorVersion:'1.1.1'}:{})});
const manifests={
root:{schema:1,edition:'root',application:'com.cleanyourtv.root.preview',release:'v1.0.3',version:'1.0.0',runtime:1,updater:1,profile:1,url:base+'com.cleanyourtv.root.preview_1.0.0_all.ipk',sha256:'a'.repeat(64),size:12,notes:'Root'},
home:{schema:1,release:'v1.0.3',home:'1.0.1',helper:'1.0.0',url:base+'com.gathin.tvhome_1.0.1_all.ipk',sha256:'a'.repeat(64),notes:'Home'},
previous:{schema:1,release:'v1.0.3',home:'1.0.0',helper:'1.0.0',url:base+'com.gathin.tvhome_1.0.0_all.ipk',sha256:'b'.repeat(64),notes:'Prior'},
system:{'root':set('root',[descriptor('root','com.cleanyourtv.root.preview'),descriptor('root-updater','com.cleanyourtv.root.updater'),{name:'root-infrastructure',kind:'infrastructure',version:'1.0.0',url:base+'root-infrastructure_1.0.0.tar.gz',sha256:'b'.repeat(64),size:42}]),'no-root':set('no-root',[descriptor('home','com.gathin.tvhome'),{...descriptor('helper','com.local.nativehome'),url:base+'com.local.nativehome_1.0.0_arm.ipk'},descriptor('updater','com.cleanyourtv.updater')])}};
const feeds=signFeeds(manifests,privateKey,publicKey);
for(const edition of ['root','no-root'])assert.deepEqual(policy.verify(feeds['system-update-'+edition+'.json'],publicKey),manifests.system[edition]);
assert.throws(()=>signFeeds({...manifests,system:{root:manifests.system.root}},privateKey,publicKey));
console.log('PASS both edition release sets signed and verified from exact descriptors');
const {verifySystemRelease}=require('../../scripts/publish-release.cjs');
const assets={},system=JSON.parse(JSON.stringify(manifests.system));
for(const manifest of Object.values(system))for(const item of manifest.components){
 const filename=item.url.split('/').pop(),raw=Buffer.from(filename);
 item.sha256=crypto.createHash('sha256').update(raw).digest('hex');item.size=raw.length;assets[filename]=raw;
}
const exact=signFeeds({...manifests,system},privateKey,publicKey);
const build={tag:'v1.0.3',versions:{home:'1.0.0',helper:'1.0.0',updater:'1.0.0',root:'1.0.0'}};
for(const edition of ['root','no-root'])assert.equal(verifySystemRelease(exact['system-update-'+edition+'.json'],build,assets,publicKey).edition,edition);
assert.throws(()=>verifySystemRelease(exact['system-update-root.json'],{...build,versions:{...build.versions,root:'9.0.0'}},assets,publicKey),/version/);
assert.throws(()=>verifySystemRelease(exact['system-update-no-root.json'],build,{},publicKey),/package/);
console.log('PASS publication verifies both system feeds against final asset bytes and versions');
assert.throws(()=>verifySystemRelease(exact['system-update-root.json'],{...build,versions:{}},assets,publicKey),/version/);

for(const minimum of [undefined,'1.1.0']){
 const bad=JSON.parse(JSON.stringify(manifests));
 if(minimum===undefined)delete bad.system.root.minimumSupervisorVersion;else bad.system.root.minimumSupervisorVersion=minimum;
 assert.throws(()=>signFeeds(bad,privateKey,publicKey),/supervisor/);
}
const unsafe=JSON.parse(JSON.stringify(system.root));unsafe.release='v1.4.1';unsafe.components.forEach(c=>{c.url=c.url.replace('/v1.0.3/','/v1.4.1/');});delete unsafe.minimumSupervisorVersion;
const unsafeRaw=Buffer.from(JSON.stringify(unsafe)),unsafeFeed={payload:unsafeRaw.toString('base64'),signature:crypto.sign('RSA-SHA256',unsafeRaw,privateKey).toString('base64')};
assert.throws(()=>verifySystemRelease(unsafeFeed,{...build,tag:'v1.4.1'},assets,publicKey),/supervisor/);
console.log('PASS new Root signing/publication requires the safe supervisor minimum');

const oldProof=JSON.parse(JSON.stringify(system.root));delete oldProof.minimumSupervisorVersion;
const oldBytes=Buffer.from(JSON.stringify(oldProof)),oldFeed={payload:oldBytes.toString('base64'),signature:crypto.sign('RSA-SHA256',oldBytes,privateKey).toString('base64')};
assert.equal(verifySystemRelease(oldFeed,build,assets,publicKey).release,'v1.0.3');
console.log('PASS historical publication verification remains available');
const hd=JSON.parse(JSON.stringify(manifests));
for(const edition of ['root','no-root']){
 hd.system[edition+'-720p']=JSON.parse(JSON.stringify(hd.system[edition]));
 hd.system[edition+'-720p'].components.find(c=>c.name===(edition==='root'?'root':'home')).url=hd.system[edition+'-720p'].components.find(c=>c.name===(edition==='root'?'root':'home')).url.replace('_all.ipk','_720p_all.ipk');
}
const hdFeeds=signFeeds(hd,privateKey,publicKey);
for(const edition of ['root','no-root']){
 assert.ok(hdFeeds['system-update-'+edition+'-720p.json'],'Missing HD system feed');
 assert.deepEqual(policy.verify(hdFeeds['system-update-'+edition+'-720p.json'],publicKey),hd.system[edition+'-720p']);
}
const incomplete=JSON.parse(JSON.stringify(hd));delete incomplete.system['root-720p'];
assert.throws(()=>signFeeds(incomplete,privateKey,publicKey),/system-release-set/);
console.log('PASS HD feeds preserve schema1 and exact signed descriptors; incomplete variant sets refused');
assert.throws(()=>verifySystemRelease(exact['system-update-root.json'],build,assets,publicKey,'1280x720'),/graphics/);
const switched=JSON.parse(JSON.stringify(hd));switched.system['root-720p']=switched.system.root;
assert.throws(()=>signFeeds(switched,privateKey,publicKey),/graphics/);
console.log('PASS signing and publication reject signed FHD envelopes in HD slots');
const legacyHd={...hd,'root-720p':{...hd.root,url:hd.root.url.replace('_all.ipk','_720p_all.ipk')},'home-720p':{...hd.home,url:hd.home.url.replace('_all.ipk','_720p_all.ipk')},'previous-720p':{...hd.previous,url:hd.previous.url.replace('_all.ipk','_720p_all.ipk')}};
const allFeeds=signFeeds(legacyHd,privateKey,publicKey);
assert.ok(allFeeds['root-update-720p.json']);assert.ok(allFeeds['update-720p.json']);
assert.deepEqual(allFeeds['update-720p.json'].previous,allFeeds['previous-update-720p.json']);
assert.throws(()=>signFeeds({...legacyHd,'root-720p':legacyHd.root},privateKey,publicKey),/graphics/);
console.log('PASS HD legacy feeds retain signed exact rollback and refuse FHD slot substitution');
const {verifyRootRelease,verifyHomeRelease}=require('../../scripts/publish-release.cjs');
assert.throws(()=>verifyRootRelease(allFeeds['root-update-720p.json'],build,Buffer.from('unused'),publicKey),/graphics/);
assert.throws(()=>verifyHomeRelease(allFeeds['update-720p.json'],build,Buffer.from('unused'),publicKey),/graphics/);
const {verifyGraphicsInventory}=require('../../scripts/publish-release.cjs');
assert.equal(typeof verifyGraphicsInventory,'function','Publication needs explicit historical graphics admission');
assert.equal(verifyGraphicsInventory({tag:'v1.5.4'}),false);
assert.throws(()=>verifyGraphicsInventory({tag:'v2.0.0'}),/graphics/);
const graphics={'1920x1080':{launcher:'launcher.ipk',root:'root'},'1280x720':{launcher:'launcher-720p.ipk',root:'root-720p'}};
assert.equal(verifyGraphicsInventory({tag:'v2.0.0',graphics,no_root_ota_720p:null}),true);
assert.throws(()=>verifyGraphicsInventory({tag:'v2.0.0',graphics}),/lineage/);
const {verifyHdHomeInventory}=require('../../scripts/publish-release.cjs');
assert.equal(typeof verifyHdHomeInventory,'function');
const record={version:'2.0.0',helper:'1.0.0',sha256:'a'.repeat(64),previous_version:'1.2.0',previous_sha256:'b'.repeat(64),feed_sha256:'c'.repeat(64)};
const declared={versions:{home:'2.0.0',helper:'1.0.0'},no_root_ota_720p:record};
assert.throws(()=>verifyHdHomeInventory(declared,[]),/lineage/);
const hdAssets=[{name:'update-720p.json'},{name:'previous-update-720p.json'}];
assert.equal(verifyHdHomeInventory(declared,hdAssets),true);
assert.equal(verifyHdHomeInventory({no_root_ota_720p:null},[]),false);
assert.throws(()=>verifyHdHomeInventory({no_root_ota_720p:null},hdAssets),/lineage/);

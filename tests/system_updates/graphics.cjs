const assert=require('node:assert/strict'),system=require('../../system-updater/policy'),root=require('../../root-edition/updater/fetch');
const prefix='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v2.0.0/';
for(const edition of ['root','no-root'])for(const resolution of ['1280x720','1920x1080']){
 assert.equal(system.feedName(edition,resolution),'system-update-'+edition+(resolution==='1280x720'?'-720p':'')+'.json');
 const name=edition==='root'?'root':'home',application=edition==='root'?'com.cleanyourtv.root.preview':'com.gathin.tvhome';
 const m={edition,release:'v2.0.0',components:[{name,application,version:'2.0.0',url:prefix+application+'_2.0.0'+(resolution==='1280x720'?'_720p':'')+'_all.ipk'}]};
 assert.equal(system.graphics(m,resolution),m);
 assert.throws(()=>system.graphics(m,resolution==='1280x720'?'1920x1080':'1280x720'),/graphics/);
}
for(const invalid of [undefined,null,'720p','1920x720',{},true])assert.throws(()=>system.feedName('root',invalid));
for(const invalid of ['__proto__','constructor',null,undefined,'other'])assert.throws(()=>system.feedName(invalid,'1280x720'));
assert.equal(root.feedName('1280x720'),'root-update-720p.json');assert.equal(root.feedName('1920x1080'),'root-update.json');
console.log('PASS strict graphics feeds and cross-channel manifest refusal');

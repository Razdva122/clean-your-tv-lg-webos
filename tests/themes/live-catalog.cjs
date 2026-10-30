'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const real=require('../../launcher/theme-data.js');
const local=JSON.parse(fs.readFileSync('launcher/theme-catalog.json'));
const sha='a'.repeat(40),api='https://api.github.com/repos/Razdva122/clean-your-tv-lg-webos/git/ref/heads/main';
let remote=structuredClone(local),mode='',calls=[];
const context={Promise,ThemeData:Object.assign({},real,{request:async(url,limit,isLocal,signal)=>{
 calls.push({url,limit,isLocal});if(signal&&signal.cancelled)throw Error('Cancelled');
 if(isLocal)return real.encode(JSON.stringify(url==='builtin-themes.json'?JSON.parse(fs.readFileSync('launcher/builtin-themes.json')):local));
 if(mode==='offline')throw Error('Network error');
 if(mode==='cancel'){signal.cancelled=true;throw Error('Cancelled');}
 return real.encode(JSON.stringify(url===api?{ref:'refs/heads/main',object:{sha,type:'commit'}}:remote));
}})};
vm.runInNewContext(fs.readFileSync('launcher/theme-manager.js','utf8'),context);
(async()=>{
 let shown;let items=await context.ThemeManager.catalog(null,entries=>{shown=entries;assert.equal(calls.length,2);});
 assert.equal(shown[2].preview,local.themes[2].preview);
 await assert.rejects(context.ThemeManager.catalog(null,()=>{throw Error('Render failed');}),/Render failed/);
 assert.equal(calls[2].url,api);assert.equal(calls[3].url,'https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/'+sha+'/launcher/theme-catalog.json');
 assert.equal(items[2].preview,'https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/'+sha+'/launcher/'+local.themes[2].preview);
 remote.themes[2].title='Reviewed update';remote.themes[0].title='Wrong built-in';
 items=await context.ThemeManager.catalog();assert.equal(items[2].title,'Reviewed update');assert.equal(items[0].title,'Classic');
 for(const edit of [r=>r.themes[2].digest='x',r=>r.themes[2].preview='../escape',r=>r.themes[2].url=r.themes[2].url.replace('raw.githubusercontent.com','evil.example'),r=>r.themes[2].id='github:other/repo:bad',r=>r.schemaVersion=9]){
  remote=structuredClone(local);edit(remote);items=await context.ThemeManager.catalog();assert.equal(items[2].title,local.themes[2].title);assert.ok(items.notice);
 }
 mode='offline';items=await context.ThemeManager.catalog();assert.ok(items.notice);assert.equal(items[2].preview,local.themes[2].preview);
 mode='cancel';await assert.rejects(context.ThemeManager.catalog({cancelled:false}),/Cancelled/);
 console.log('Live catalogue: pinned refresh, validation, local fallback and cancellation passed');
})().catch(e=>{console.error(e);process.exitCode=1;});

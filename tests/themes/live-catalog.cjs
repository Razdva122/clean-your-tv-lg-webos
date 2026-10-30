'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const real=require('../../launcher/theme-data.js');
const local=JSON.parse(fs.readFileSync('launcher/theme-catalog.json'));
const external=local.themes.find(item=>item.builtin!==true),externalIn=items=>items.find(item=>item.id===external.id);
assert.ok(external,'catalog fixture includes a reviewed external theme');
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
 assert.equal(externalIn(shown).preview,external.preview);
 await assert.rejects(context.ThemeManager.catalog(null,()=>{throw Error('Render failed');}),/Render failed/);
 assert.equal(calls[2].url,api);assert.equal(calls[3].url,'https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/'+sha+'/launcher/theme-catalog.json');
 assert.equal(externalIn(items).preview,'https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/'+sha+'/launcher/'+external.preview);
 externalIn(remote.themes).title='Reviewed update';remote.themes.filter(item=>item.builtin===true).forEach(item=>item.title='Wrong built-in');
 items=await context.ThemeManager.catalog();assert.equal(externalIn(items).title,'Reviewed update');
 for(const builtin of local.themes.filter(item=>item.builtin===true))assert.equal(items.find(item=>item.id===builtin.id).title,builtin.title,'live metadata cannot override bundled '+builtin.id);
 for(const edit of [r=>externalIn(r.themes).digest='x',r=>externalIn(r.themes).preview='../escape',r=>externalIn(r.themes).url=externalIn(r.themes).url.replace('raw.githubusercontent.com','evil.example'),r=>externalIn(r.themes).id='github:other/repo:bad',r=>r.schemaVersion=9]){
  remote=structuredClone(local);edit(remote);items=await context.ThemeManager.catalog();assert.equal(externalIn(items).title,external.title);assert.ok(items.notice);
 }
 mode='offline';items=await context.ThemeManager.catalog();assert.ok(items.notice);assert.equal(externalIn(items).preview,external.preview);
 mode='cancel';await assert.rejects(context.ThemeManager.catalog({cancelled:false}),/Cancelled/);
 console.log('Live catalogue: pinned refresh, validation, local fallback and cancellation passed');
})().catch(e=>{console.error(e);process.exitCode=1;});

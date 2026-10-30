'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const repo=process.cwd(),legacy=process.env.CYTV_LEGACY_THEME_DIR;
const directory=legacy||path.join(repo,'launcher'),data=require(path.join(directory,'theme-data.js'));
const manifest=JSON.parse(fs.readFileSync(path.join(repo,'tests/themes/fixtures/valid-manifest.json')));
manifest.layout={preset:'scenic-grid',columns:8,allowColumnOverride:false,spacingScale:1,textScale:1,focusScale:1.1,ribbon:{left:340,right:84,bottom:0,cardHeight:180,gap:0,skewDeg:-13,focusLift:36,iconScale:.65,shortcuts:'bottom-left',edgeNavigation:'shortcuts',labels:'focused-above',showClock:false}};
manifest.requires.capabilities=[legacy?'ribbon-layout-v1':'future-ribbon-layout-v2'];
const descriptor=Buffer.from(JSON.stringify(manifest));
const previous={id:'github:owner/repo:previous',title:'Previous',digest:'c'.repeat(64)},previousPack={prior:true};
const values=new Map([['tvhome.theme.choice.v1',JSON.stringify(previous)]]);
let puts=0,applies=0,resets=0,visual='',requests=[];
global.XMLHttpRequest=class{open(method,url){this.url=url;}send(){requests.push(this.url);this.status=200;this.responseURL=this.url;this.response=Uint8Array.from(descriptor).buffer;queueMicrotask(()=>this.onload());}};
const proxy={...data,request:async url=>Buffer.from(JSON.stringify(url==='appinfo.json'?{version:'99.0.0'}:{schemaVersion:1,themes:[{id:'builtin:alpine'}]})),verify:pack=>pack===previousPack?{manifest:{id:previous.id,title:previous.title}}:data.verify(pack,'99.0.0'),prepare:async pack=>pack===previousPack?{manifest:{id:previous.id,title:previous.title},assetHandles:{}}:data.prepare(pack,'99.0.0')};
const ctx={Promise,setTimeout,clearTimeout,Date,console,CustomEvent:function(t){this.type=t},requestAnimationFrame:fn=>fn(),document:{dispatchEvent(){}},localStorage:{getItem:k=>values.has(k)?values.get(k):null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},ThemeData:proxy,ThemeStore:{get:async()=>previousPack,list:async()=>[previousPack],put:async()=>{puts++}},ThemeRuntime:{apply:input=>{applies++;visual=input.manifest.id},reset:()=>{resets++;visual='builtin:classic'}}};ctx.window=ctx;
vm.runInNewContext(fs.readFileSync(path.join(directory,'theme-manager.js'),'utf8'),ctx);
(async()=>{
 await ctx.ThemeManager.start();assert.equal(visual,previous.id);
 const before=JSON.stringify([...values]);const initialApplies=applies;
 for(const [name,run] of [['LAN',()=>ctx.ThemeManager.installEnvelope({schemaVersion:1,descriptor:descriptor.toString('base64'),files:{}})],['URL',()=>ctx.ThemeManager.install({url:'https://raw.githubusercontent.com/owner/themes/'+'a'.repeat(40)+'/cytv-theme.json'})]]){
  await assert.rejects(run,/api-unsupported/);
  assert.equal(puts,0,name+' cannot store unsupported package');assert.equal(applies,initialApplies,name+' cannot apply unsupported theme');assert.equal(resets,0,name+' cannot reset accepted theme');assert.equal(visual,previous.id);assert.equal(JSON.stringify([...values]),before,name+' cannot alter saved selection/recovery state');assert.equal(ctx.ThemeManager.current().id,previous.id);
 }
 assert.equal(requests.length,1,'URL rejects descriptor before any theme assets download');
 console.log('PASS '+(legacy?'actual pre-ribbon Home':'unsupported future capability')+': URL and LAN reject api-unsupported; zero cache writes, apply/reset, saved selection changes; previous theme retained');
})().catch(e=>{console.error(e);process.exitCode=1});

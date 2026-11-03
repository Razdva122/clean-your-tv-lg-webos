const assert=require('assert'),vm=require('vm'),fs=require('fs'),data=require('../../launcher/user-data');
const profile={schema:1,inventory:{apps:[{id:'app',title:'App',icon:'data:image/png;base64,YQ=='}],inputs:[]},config:{columns:5,dockApps:[],hiddenApps:[]},settings:{'tvhome.order':'old'}};
const map=new Map([[data.key,JSON.stringify(profile)],['tvhome.order','new']]);
const storage={getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,v)};
let scripts=[];const context={HomeData:data,localStorage:storage,window:null,CONFIG:{},TV_APPS:{apps:[],inputs:[]},document:{createElement:()=>({}),body:{appendChild:s=>scripts.push(s)},querySelector:()=>null},setTimeout,clearTimeout};context.window=context;
vm.runInNewContext(fs.readFileSync('launcher/profile-bootstrap.js','utf8'),context);
assert.equal(map.get('tvhome.order'),'new');assert.equal(context.TV_APPS.apps[0].id,'app');assert.equal(scripts.length,1);assert.equal(scripts[0].src,'app.js');
console.log('PASS profile startup preserves live tile ordering');
// A timeout is not the same thing as a successful response containing no backup.
let timeout;
const blank={...context,TV_APPS:{apps:[],inputs:[]},localStorage:{getItem:()=>null,setItem:()=>{}},setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{},PalmServiceBridge:function(){this.call=()=>{};this.cancel=()=>{};}};blank.window=blank;
vm.runInNewContext(fs.readFileSync('launcher/profile-bootstrap.js','utf8'),blank);timeout();let error;blank.HomeProfile.capture(e=>{error=e;});assert(error,'capture must fail after restore timeout');
console.log('PASS failed restore cannot become an empty replacement profile');
const renewalCalls=[];
context.PalmServiceBridge=function(){this.cancel=()=>{};this.call=(uri)=>{renewalCalls.push(uri);this.onservicecallback(JSON.stringify({returnValue:true,state:{enabled:true,last:{status:'healthy'}}}));};};
let captured,captureError;context.HomeProfile.capture((e,p)=>{captureError=e;captured=p});assert(!captureError);assert(captured);assert.equal(captured.renewal.enabled,false);assert(renewalCalls.every(uri=>uri.endsWith('/status')));
console.log('PASS enabled renewal permits profile capture without changing its preference');
// Restoring an explicit preference to auto must reload even if both currently
// resolve to English, so the TV system locale can be queried on the new startup.
let pref='en',reloads=0,restoreScript;
const restoring={...context,TV_APPS:{apps:[],inputs:[]},CONFIG:{},
 localStorage:{getItem:()=>null,setItem:(k,v)=>{if(k==='tvhome.language')pref=v;},removeItem(){}},
 HomeI18n:{ready:cb=>cb(),preference:()=>pref,refresh:()=> 'en'},location:{reload:()=>reloads++},
 document:{...context.document,body:{appendChild:s=>{restoreScript=s;}}},
 PalmServiceBridge:function(){this.cancel=()=>{};this.call=uri=>{if(uri.endsWith('/restore'))this.onservicecallback(JSON.stringify({returnValue:true,result:{...profile,settings:{'tvhome.language':'auto'}}}));};}};
restoring.window=restoring;
vm.runInNewContext(fs.readFileSync('launcher/profile-bootstrap.js','utf8'),restoring);
assert.equal(pref,'auto');assert.equal(reloads,1,'restore must reinitialize TV auto-detection');
console.log('PASS restored language preference reinitializes automatic TV locale');

// The installed app manifest, not a source literal, supplies the health version.
for(const {version,id='com.gathin.tvhome',status=200,invalid=false,healthy} of [{version:'1.3.3',healthy:true},{version:'1.4.0',healthy:true},{version:'1.3.4',id:'foreign.app',healthy:false},{version:'1.3.4',status:404,healthy:false},{version:'1.3.4',invalid:true,healthy:false}]){
 const calls=[];let script;
 const run={...context,HomeI18n:null,TV_APPS:{apps:[{id:'app'}],inputs:[]},CONFIG:{},localStorage:{getItem:()=>null,setItem(){}},
  document:{...context.document,querySelector:()=>({}),body:{appendChild:s=>{script=s;}}},
  XMLHttpRequest:class{open(method,url){assert.equal(method,'GET');assert.equal(url,'appinfo.json');}send(){this.status=status;this.responseText=invalid?'{broken':JSON.stringify({id,version});this.onload();}},
  PalmServiceBridge:function(){this.cancel=()=>{};this.call=(uri,raw)=>{calls.push([uri,JSON.parse(raw)]);this.onservicecallback(JSON.stringify({returnValue:true,result:{}}));};}};
 run.window=run;vm.runInNewContext(fs.readFileSync('launcher/profile-bootstrap.js','utf8'),run);script.onload();
 assert.deepEqual(calls.filter(c=>c[0].endsWith('/healthy')).map(c=>c[1]),healthy?[{version}]:[]);
}
console.log('PASS No-root startup reports the installed app manifest version across releases');

// A retained local profile must not bypass rollback restoration, or overwrite
// subsequent edits again every time the old version starts.
const rollbackMemory=new Map([[data.key,JSON.stringify({...profile,config:{...profile.config,columns:7}})],['tvhome.order','later'],['tvhome.layout','later-layout'],['tvhome.columns.v1','{"version":1,"columns":4}'],['tvhome.theme.choice.v1','{"id":"builtin:alpine","title":"Alpine"}'],['tvhome.theme.trial.v1','{"kind":"trial"}'],['tvhome.wallpaper.preferences.v1','[{"id":"builtin:alpine","quality":"image","dim":0.4}]']]);
const rollbackStorage={getItem:k=>rollbackMemory.has(k)?rollbackMemory.get(k):null,setItem:(k,v)=>rollbackMemory.set(k,v),removeItem:k=>rollbackMemory.delete(k)};
function rollbackBoot(version='1.2.0',transaction='rollback-one'){
 let script;const run={...context,HomeI18n:null,TV_APPS:{apps:[],inputs:[]},CONFIG:{},localStorage:rollbackStorage,
 document:{...context.document,querySelector:()=>null,body:{appendChild:s=>{script=s;}}},
 XMLHttpRequest:class{open(method,url){assert.equal(url,'appinfo.json');}send(){this.status=200;this.responseText=JSON.stringify({id:'com.gathin.tvhome',version});this.onload();}},
 PalmServiceBridge:function(){this.cancel=()=>{};this.call=(uri,raw)=>{assert(uri.endsWith('/restore'));assert.equal(JSON.parse(raw).withTransaction,true);this.onservicecallback(JSON.stringify({returnValue:true,result:{profile,transaction:{id:transaction,status:'rolled-back',prior:{home:'1.2.0'}}}}));};}};
 run.window=run;vm.runInNewContext(fs.readFileSync('launcher/profile-bootstrap.js','utf8'),run);assert(script);return run;
}
let rollback=rollbackBoot();assert.equal(rollback.CONFIG.columns,5);assert.equal(rollbackMemory.get('tvhome.order'),'old');assert(!rollbackMemory.has('tvhome.layout'));
for(const key of ['tvhome.columns.v1','tvhome.theme.choice.v1','tvhome.theme.trial.v1','tvhome.wallpaper.preferences.v1'])assert(!rollbackMemory.has(key),'legacy No-root rollback still resets appearance');
rollbackMemory.set('tvhome.order','edited-after-rollback');rollback=rollbackBoot();assert.equal(rollbackMemory.get('tvhome.order'),'edited-after-rollback');
rollback=rollbackBoot('1.3.0','stale-rollback');assert.equal(rollbackMemory.get('tvhome.order'),'edited-after-rollback');
console.log('PASS rollback restores retained local settings once and rejects stale package versions');

// A deliberately empty Home with + hidden is valid, but a failed render is not.
for (const {showAddApp,rendered,healthy} of [{showAddApp:false,rendered:true,healthy:true},{showAddApp:false,rendered:false,healthy:false},{showAddApp:true,rendered:true,healthy:false}]) {
 const calls=[];let script;
 const memory=new Map([['tvhome.layout',JSON.stringify({version:1,ids:[],hidden:['app'],catalog:[],showAddApp})]]);
 const run={...context,HomeI18n:null,AppLibrary:require('../../launcher/app-library'),RootLauncherRendered:rendered,
  TV_APPS:{apps:[{id:'app',title:'App'}],inputs:[]},CONFIG:{columns:5,dockApps:[],hiddenApps:[]},
  localStorage:{getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v)},
  document:{...context.document,querySelector:()=>null,body:{appendChild:s=>{script=s;}}},
  XMLHttpRequest:class{open(){}send(){this.status=200;this.responseText=JSON.stringify({id:'com.gathin.tvhome',version:'1.4.1'});this.onload();}},
  PalmServiceBridge:function(){this.cancel=()=>{};this.call=(uri,raw)=>{calls.push([uri,JSON.parse(raw)]);this.onservicecallback(JSON.stringify({returnValue:true,result:{}}));};}};
 run.window=run;vm.runInNewContext(fs.readFileSync('launcher/profile-bootstrap.js','utf8'),run);script.onload();
 assert.equal(calls.some(c=>c[0].endsWith('/healthy')),healthy,'only an intentionally empty, completed render is healthy');
}
console.log('PASS intentionally empty Home startup health without masking render failures');

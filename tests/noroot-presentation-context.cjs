const assert=require('node:assert/strict');
const fs=require('node:fs');
const presentation=require('../launcher/home-presentation');
assert.equal(typeof presentation.nativeContext,'function','native context validator is required');
const valid={returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:20};
assert.deepEqual(presentation.nativeContext(valid,7),{eligible:true,content:true});
assert.deepEqual(presentation.nativeContext({...valid,eligible:false,content:null},7),{eligible:false,content:null});
assert.deepEqual(presentation.nativeContext({...valid,eligible:false,content:false},7),{eligible:false,content:false});
for(const reply of [null,{}, {...valid,returnValue:false}, {...valid,eligible:1}, {...valid,content:undefined}, {...valid,content:"false"}, {...valid,content:null},
 {...valid,generation:8}, {...valid,generation:'7'}, {...valid,generation:-1},
 {...valid,generation:1.2}, {...valid,observedAgeMs:-1}, {...valid,observedAgeMs:2001},
 {...valid,observedAgeMs:Infinity}, {...valid,observedAgeMs:NaN}, {...valid,observedAgeMs:'20'}]) {
 assert.equal(presentation.nativeContext(reply,7),null,'invalid/unmatched/stale reply must remain unknown');
}
assert.deepEqual(presentation.nativeContext({...valid,observedAgeMs:2000},7),{eligible:true,content:true});
for(const generation of [undefined,null,'7',NaN,Infinity,-1,1.5,9007199254740992])
 assert.equal(presentation.nativeContext({...valid,generation},generation),null,'invalid expected generation cannot authorize overlay');
let params;
const c=presentation.create({supported:true,query:(done,activation)=>{params=activation;done(true);}});
c.setTheme({presentation:'overlay'});
const activation={cytvHome:{reason:'home',generation:7}};
c.show(activation);assert.deepEqual(params,activation,'query receives current activation, not a stale global launch value');
c.suspend('settings');c.resume('settings');assert.deepEqual(params,activation,'modal return retains the current activation generation');
c.show({reason:'startup'});assert.equal(c.state().mode,'full');
require('acorn').parse(fs.readFileSync('launcher/home-presentation.js','utf8'),{ecmaVersion:5});
const info=JSON.parse(fs.readFileSync('launcher/appinfo.json','utf8'));
assert.equal(info.id,'com.gathin.tvhome');
assert.equal(info.defaultWindowType,'overlay','production Home needs a native overlay window, not transparent CSS in a card');
assert.equal(info.transparent,true);assert.equal(info.handlesRelaunch,true);
assert.equal(info.noSplashOnLaunch,true);assert.equal(info.spinnerOnLaunch,false);
assert.deepEqual(info.requiredACG,['application.launcher','network.query'],'overlay adds no permissions');
assert.equal(info.systemUpdateProtocol,1);
let contextReply;const frames=[];
const full=presentation.create({supported:true,queryFull:true,query:done=>contextReply=done,render:state=>frames.push(state)});
full.show({cytvHome:{reason:'home',generation:7}});
assert.equal(typeof contextReply,'function','native opaque themes also need a context decision before using the decoder');
assert.equal(frames.at(-1).content,null,'initial full rendering cannot reuse old decoder ownership');
contextReply(false);assert.equal(full.state().mode,'full');assert.equal(full.state().content,false);
full.show({});assert.equal(full.state().content,null,'new activation discards prior safe decoder context');
contextReply(true);assert.equal(full.state().mode,'full','non-Ribbon never becomes transparent');assert.equal(full.state().content,true);
assert.equal(presentation.nativeContext({...valid,observedAgeMs:1900},7,101),null,'transport time counts toward freshness');
assert.deepEqual(presentation.nativeContext({...valid,observedAgeMs:1900},7,100),{eligible:true,content:true});
assert.equal(presentation.nativeContext(valid,7,-1),null);
assert.equal(presentation.nativeContext(valid,7,Infinity),null);

full.show({});contextReply({eligible:false,content:null});assert.equal(full.state().content,null,'ineligible does not mean safe decoder ownership');
full.setTheme({presentation:'overlay'});contextReply({eligible:false,content:true});assert.equal(full.state().mode,'full','known content alone does not grant eligibility');
contextReply({eligible:true,content:true});assert.equal(full.state().mode,'full','a settled query cannot change mode twice');
full.show({});contextReply({eligible:true,content:true});assert.equal(full.state().mode,'overlay');

let exits=0,modal=false;
const standalone=presentation.create({supported:true,dismissFull:true,query:done=>done(null),close:()=>exits++,blocked:()=>modal});
standalone.show({reason:'startup'});assert.equal(standalone.state().mode,'full');
assert(standalone.dismiss(),'native opaque Home must have a Back exit without Helper');assert.equal(exits,1);
standalone.show({});standalone.relaunch({});assert.equal(exits,1,'Home relaunch does not toggle a non-overlay theme');assert.equal(standalone.state().mode,'full');
modal=true;standalone.sync();assert(!standalone.dismiss(),'Back still belongs to modal/editor owners');

console.log('PASS No-root native metadata, strict context/generation/age, decoder facts, current activation and ES5');

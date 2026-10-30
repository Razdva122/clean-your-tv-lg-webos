// Startup presentation is part of readiness, including bounded recovery.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const turn=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(){
 const values=new Map([['tvhome.theme.choice.v1',JSON.stringify({id:'builtin:alpine',title:'Alpine'})]]),frames=[],timers=new Map(),state={visual:'builtin:classic',presented:[]};let serial=0;
 const ctx={Promise,Date,CustomEvent:function(type){this.type=type;},document:{dispatchEvent(){}},requestAnimationFrame:fn=>frames.push(fn),setTimeout:(fn,delay)=>{timers.set(++serial,{fn,delay});return serial;},clearTimeout:id=>timers.delete(id),localStorage:{getItem:key=>values.has(key)?values.get(key):null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)},ThemeRuntime:{reset:()=>state.visual='builtin:classic',apply:input=>state.visual=input.manifest.id},ThemeData:{request:async url=>url==='appinfo.json'?{themeEngineVersion:'1.6.0'}:{schemaVersion:1,themes:[{id:'builtin:alpine',title:'Alpine',version:'1.0.0',url:'themes/alpine/cytv-theme.json',digest:'b'.repeat(64)}]},decode:JSON.stringify,load:async()=>({digest:'b'.repeat(64)}),prepare:()=>new Promise(resolve=>{state.release=()=>resolve({manifest:{id:'builtin:alpine',title:'Alpine'},assetHandles:{}});}),dispose(){}}};
 vm.runInNewContext(fs.readFileSync('launcher/theme-manager.js','utf8'),ctx);
 return {m:ctx.ThemeManager,state,values,frames,timers,present:()=>state.presented.push(state.visual),async paint(){while(frames.length){frames.shift()();await turn();}}};
}
(async()=>{
 let f=fixture(),ready=false;
 const boot=f.m.start(f.present).then(()=>ready=true);await turn();
 assert.equal(ready,false);assert.equal(f.state.presented.length,0);assert(f.values.has(f.m.trialKey));
 f.state.release();await turn();
 assert.deepEqual(f.state.presented,['builtin:alpine'],'saved appearance must be applied before exposing Home');
 assert.equal(ready,false,'readiness must wait for presentation frames');assert(f.values.has(f.m.trialKey),'boot marker survives until presentation');
 await f.paint();await boot;assert.equal(ready,true);assert(!f.values.has(f.m.trialKey));assert.equal(f.timers.size,0);
 f=fixture();const timed=f.m.start(f.present);await turn();const deadline=Array.from(f.timers.values()).find(t=>t.delay===8000);
 assert(deadline,'startup has a bounded fallback');deadline.fn();await turn();await f.paint();await timed;
 assert.deepEqual(f.state.presented,['builtin:classic']);assert.equal(f.m.current().id,'builtin:classic');assert.match(f.m.current().notice,/timed out/i);assert(!f.values.has(f.m.trialKey));
 f.state.release();await turn();await f.paint();assert.equal(f.m.current().id,'builtin:classic','late successful preparation cannot replace timeout fallback');assert.deepEqual(f.state.presented,['builtin:classic']);
 f=fixture();const cancelled=f.m.start(f.present);await turn();await f.m.cancel();f.state.release();await turn();await f.paint();await cancelled;
 assert.equal(f.m.current().id,'builtin:classic');assert(!f.values.has(f.m.trialKey),'safe cancelled startup retires only its own boot marker after fallback presentation');assert(f.values.has(f.m.choiceKey),'no-op cancellation does not discard the accepted saved choice');
 console.log('PASS theme startup presentation, first-frame marker/readiness ordering, bounded fallback and stale completion');
})().catch(error=>{console.error(error);process.exitCode=1;});

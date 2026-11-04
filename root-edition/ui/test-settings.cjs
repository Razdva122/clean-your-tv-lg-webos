const assert=require('node:assert/strict'),vm=require('vm'),fs=require('fs');
const buttons=[],listeners={},calls=[];let retry;let selected,phase='active',restores=0,failLaunch=false,delayStatus=false,delayLaunch=false,gateBackend=false;const pending=[],launches=[];
class Element {
 constructor(tag){this.tag=tag;this.hidden=false;this.disabled=false;this.attrs={};if(tag==='button')buttons.push(this);}
 appendChild(){} setAttribute(k,v){this.attrs[k]=v;} focus(){selected=this;if(this.onfocus)this.onfocus();}
}
const document={body:new Element('body'),activeElement:{focus(){selected='previous';}},createElement:t=>new Element(t),addEventListener:(n,f)=>listeners[n]=f};
const context={window:{RootUpdates:{open(){}}},document,Promise,setTimeout,clearTimeout,
 createRootExit:(call,launch)=>async()=>{restores++;phase='disabled';await launch();},
 PalmServiceBridge:class{cancel(){}call(uri,raw){calls.push({uri,payload:JSON.parse(raw)});let r={returnValue:true};
 if(JSON.parse(raw).startup){r.result={returnValue:true,result:{sources:{tv:true,youtube:false},active:phase==='active'}};this.onservicecallback(JSON.stringify(r));return;}
 if(uri.endsWith('/status')){if(delayStatus){pending.push(this);return;}r.result={returnValue:true,result:{intent:{phase},effective:gateBackend?{backend:'c1-native-gate'}:{}}};}
 if(uri.endsWith('/enable')){phase='active';r.result={returnValue:true,result:{}};}
 if(uri.endsWith('/launch')&&delayLaunch){launches.push(this);return;}
 if(uri.endsWith('/launch')&&failLaunch)r.returnValue=false;
 this.onservicecallback(JSON.stringify(r));}}
};
vm.runInNewContext(fs.readFileSync(__dirname+'/root-settings.js','utf8'),context);
const panel=context.window.RenewalPanel,tick=()=>new Promise(r=>setImmediate(r));
async function nextStatus(){await tick();return pending.shift();}
function key(keyCode){listeners.keydown({keyCode,preventDefault(){},stopImmediatePropagation(){}});}
(async()=>{
 panel.open();await tick();const sources=buttons.filter(b=>['LG Channels / Live TV','YouTube','HDMI'].includes(b.textContent));assert.equal(sources.length,2,'only two startup switches');assert(!buttons.some(b=>b.textContent==='HDMI'),'no HDMI startup switch');assert.equal(sources[0].attrs['aria-checked'],'true');assert.equal(sources[1].attrs['aria-checked'],'false');sources.forEach(b=>buttons.splice(buttons.indexOf(b),1));retry=buttons.splice(buttons.findIndex(b=>b.textContent==='Check status'),1)[0];assert.equal(selected,buttons[0]);assert.equal(buttons[0].attrs['aria-checked'],'true');
 key(39);assert.equal(selected,buttons[1]);key(13);key(13);await tick();
 assert.equal(calls.filter(c=>c.uri.endsWith('/launch')).length,1);assert.equal(restores,0);assert.equal(phase,'active');assert(!panel.isOpen());
 panel.open();await tick();buttons[0].onclick();await tick();assert.equal(restores,1);assert.equal(buttons[0].attrs['aria-checked'],'false');assert(panel.isOpen());assert(sources.every(b=>b.disabled),'Home Off disables sources');const writes=calls.filter(c=>c.payload.startup==='configure').length;sources[0].onclick();assert.equal(calls.filter(c=>c.payload.startup==='configure').length,writes);
 buttons[0].onclick();await tick();assert.equal(phase,'active');assert.equal(buttons[0].attrs['aria-checked'],'true');assert(!buttons[0].disabled);
 failLaunch=true;buttons[1].onclick();await tick();assert(panel.isOpen());assert.equal(phase,'active');assert(!buttons[1].disabled);key(461);assert(!panel.isOpen());
 // External emergency stop while the real Settings module remains open.
 failLaunch=false;panel.open();await tick();phase='disabled';delayStatus=true;
 document.hidden=true;if(listeners.visibilitychange)listeners.visibilitychange();
 document.hidden=false;if(listeners.visibilitychange)listeners.visibilitychange();
 const before=restores;buttons[0].onclick();await tick();
 assert.equal(restores,before,'resume must invalidate active cache before the first click');
 assert(buttons[0].disabled,'status unresolved: toggle unavailable');
 assert.equal(pending.length,1,'visible resumes status');
 (await nextStatus()).onservicecallback(JSON.stringify({returnValue:true,result:{returnValue:true,result:{intent:{phase:'disabled'}}}}));await tick();
 assert.equal(buttons[0].attrs['aria-checked'],'false');assert(!buttons[0].disabled);
 delayStatus=false;buttons[0].onclick();await tick();assert.equal(phase,'active');assert.equal(restores,before);
 // Each lifecycle refresh owns a generation, including failures and close/reopen.
 delayStatus=true;listeners.webOSRelaunch();const old=(await nextStatus());
 listeners.webOSRelaunch();await tick();assert.equal(pending.length,0,'a later refresh waits for the active read');
 const reply=(bridge,value)=>bridge.onservicecallback(JSON.stringify(value));
 const status=phase=>({returnValue:true,result:{returnValue:true,result:{intent:{phase}}}});
 reply(old,status('active'));await tick();assert(buttons[0].disabled,'stale completion cannot enable controls');
 reply((await nextStatus()),status('disabled'));await tick();assert.equal(buttons[0].attrs['aria-checked'],'false');
 assert.equal(phase,'active','status refresh never mutates backend intent');
 listeners.webOSRelaunch();const staleFailure=(await nextStatus());
 listeners.webOSRelaunch();await tick();assert.equal(pending.length,0);
 reply(staleFailure,{returnValue:false});await tick();assert(buttons[0].disabled);
 reply((await nextStatus()),status('disabled'));await tick();assert(!buttons[0].disabled);assert(retry.hidden);
 listeners.webOSRelaunch();reply((await nextStatus()),{returnValue:false});await tick();
 assert(buttons[0].disabled);assert(!retry.hidden);assert(!retry.disabled);
 retry.onclick();reply((await nextStatus()),{returnValue:true,result:{returnValue:true,result:{}}});await tick();
 assert(buttons[0].disabled);assert(!retry.hidden,'malformed successful status offers read-only retry');
 const enables=calls.filter(c=>c.uri.endsWith('/enable')).length;
 buttons[0].onclick();assert.equal(calls.filter(c=>c.uri.endsWith('/enable')).length,enables);
 retry.onclick();assert(retry.hidden);reply((await nextStatus()),status('disabled'));await tick();
 assert(!buttons[0].disabled);assert.equal(restores,before);
 listeners.webOSRelaunch();const closed=(await nextStatus());key(461);assert(!panel.isOpen());
 panel.open();await tick();assert.equal(pending.length,0);reply(closed,status('active'));await tick();assert(buttons[0].disabled);
 reply((await nextStatus()),status('disabled'));await tick();assert.equal(buttons[0].attrs['aria-checked'],'false');
 // Hiding invalidates an in-flight reply even before the visible event arrives.
 listeners.webOSRelaunch();const hidden=(await nextStatus());document.hidden=true;listeners.visibilitychange();
 reply(hidden,status('active'));await tick();assert(buttons[0].disabled);
 document.hidden=false;listeners.visibilitychange();reply((await nextStatus()),status('disabled'));await tick();
 delayStatus=false;phase='disabled';buttons[0].onclick();await tick();assert.equal(phase,'active');assert.equal(restores,before);
 buttons[0].onclick();await tick();assert.equal(phase,'disabled');assert.equal(restores,before+1);
 listeners.webOSRelaunch();await tick();assert.equal(phase,'disabled','explicit Off survives relaunch');
 assert.equal(calls.filter(c=>c.uri.endsWith('/enable')).length,enables+1,'only explicit later click enables');
 // Audio/Firmware hide only the parent panel; resume still invalidates it.
 phase='active';listeners.webOSRelaunch();await tick();
 let childClose;context.window.RootAudio={open(_request,onClose){childClose=onClose;}};
 buttons.find(b=>b.textContent==='HDMI sound').onclick();assert(!panel.isOpen());
 phase='disabled';listeners.webOSRelaunch();delayStatus=true;childClose();
 assert(buttons[0].disabled,'child return waits for fresh Home status');
 reply((await nextStatus()),status('disabled'));await tick();assert(!buttons[0].disabled);
 // A delayed failed one-time visit after resume cannot leave an inert enabled toggle.
 delayLaunch=true;buttons[1].onclick();listeners.webOSRelaunch();
 reply(launches.shift(),{returnValue:false});await tick();
 assert(buttons[0].disabled,'failed visit after resume must refresh before re-enabling');
 assert.equal(pending.length,1);reply((await nextStatus()),status('disabled'));await tick();
 assert(!buttons[0].disabled);delayStatus=false;delayLaunch=false;
 gateBackend=true;phase='active';listeners.webOSRelaunch();await tick();
 const gateRestores=restores;buttons[1].onclick();await tick();
 assert.equal(restores,gateRestores+1,'experimental LG Home releases routing before launch');
 assert.equal(phase,'disabled','experimental visit does not silently rearm');
 console.log('PASS Root switch, one-time visit, failure recovery, duplicate suppression and remote focus');
})().catch(e=>{console.error(e);process.exit(1);});

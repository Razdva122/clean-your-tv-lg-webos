// Catch overlapping Home/startup reads using the actual single-flight service handler.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const elements=[],listeners={};let phase='active',sources={tv:true,youtube:false,hdmi:false};
const pause=()=>new Promise(resolve=>setImmediate(resolve));
const handlers=require('../service/handlers')(async command=>{await pause();if(command==='enable')phase='active';if(command==='restore')phase='disabled';return {intent:{phase}};},null,async(command,next)=>{await pause();if(command==='configure')sources=next;return {sources,active:phase==='active'};});
class Element {
 constructor(tag){this.tag=tag;this.attrs={};this.hidden=false;this.disabled=false;elements.push(this);}
 appendChild(child){child.parent=this;}setAttribute(k,v){this.attrs[k]=v;}focus(){document.activeElement=this;if(this.onfocus)this.onfocus();}
}
const document={body:new Element('body'),activeElement:{focus(){}},createElement:tag=>new Element(tag),addEventListener:(name,fn)=>listeners[name]=fn};
const context={window:{},document,Promise,setTimeout,clearTimeout,
 createRootExit:()=>()=>handlers.restore({}),
 PalmServiceBridge:class{cancel(){}call(uri,raw){handlers[uri.split('/').pop()](JSON.parse(raw)).then(result=>this.onservicecallback(JSON.stringify({returnValue:true,result})));}}};
vm.runInNewContext(fs.readFileSync(__dirname+'/root-settings.js','utf8'),context);
const button=text=>elements.find(e=>e.tag==='button'&&e.textContent===text);
async function settle(){for(let i=0;i<8;i++)await pause();}
(async()=>{
 context.window.RenewalPanel.open();
 const home=button('Change Home'),youtube=button('YouTube');
 await pause();assert.equal(home.disabled,true,'Home stays unavailable while the startup read holds the service lock');
 home.onclick();assert.equal(phase,'active','pending refresh cannot mutate Home');
 await settle();
 assert.equal(home.disabled,false,'opening Settings must allow Home control with the real service lock');
 assert.equal(home.attrs['aria-checked'],'true');assert.equal(youtube.disabled,false);
 youtube.onclick();await settle();assert.equal(youtube.attrs['aria-checked'],'true');assert.equal(home.disabled,false);
 home.onclick();await settle();assert.equal(home.attrs['aria-checked'],'false');assert.equal(home.disabled,false);
 assert.equal(youtube.disabled,true);assert.equal(youtube.attrs['aria-checked'],'true','Off retains saved choices');
 // LG Home -> the existing Root window delivers visibility and relaunch together.
 document.hidden=true;listeners.visibilitychange();document.hidden=false;listeners.visibilitychange();listeners.webOSRelaunch();
 await settle();assert.equal(home.disabled,false,'returning after Home Off must not collide with its own status refresh');
 assert.equal(home.attrs['aria-checked'],'false');assert.equal(youtube.disabled,true);
 assert(elements.some(e=>e.textContent==='Available when Change Home is on.'),'return keeps the Home-Off reason');
 home.onclick();await settle();assert.equal(youtube.disabled,false);assert.equal(youtube.attrs['aria-checked'],'true');
 console.log('PASS Settings reads and writes with actual single-flight service handler');
})().catch(error=>{console.error(error);process.exit(1);});

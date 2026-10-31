const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function harness(root,system=false,blurHidden=true){
 const ids={},buttons=[],pending=[],calls=[],homePending=[],rpcCalls=[],systemPending=[],systemCalls=[],listeners={};let focused,allowColumns=true;
 class E{
  constructor(tag){this.tag=tag;this.attrs={};this.children=[];this.className='';this.hidden=false;this.disabled=false;if(tag==='button')buttons.push(this);this.classList={toggle:(n,on)=>{const has=this.className.split(' ').includes(n);if(on===undefined)on=!has;if(on&&!has)this.className+=' '+n;else if(!on)this.className=this.className.split(' ').filter(x=>x!==n).join(' ');},contains:n=>this.className.split(' ').includes(n),add:n=>{this.className+=' '+n;},remove:n=>{this.className=this.className.split(' ').filter(x=>x!==n).join(' ');}};}
  set innerHTML(html){for(const match of html.matchAll(/<(button|p|div|pre|span)\b[^>]*id="([^"]+)"[^>]*>/g)){const e=new E(match[1]);ids[match[2]]=e;e.parentNode=match[2]==='homeColumns'?new E('div'):this;this.children.push(e);}}
  set id(value){this._id=value;ids[value]=this;}get id(){return this._id;}
  set hidden(value){this._hidden=value;if(value&&blurHidden&&document.activeElement===this){document.activeElement=document.body;focused=document.body;}}get hidden(){return this._hidden;}
  appendChild(e){e.parentNode=this;this.children.push(e);}setAttribute(k,v){this.attrs[k]=v;}addEventListener(){}focus(){focused=this;document.activeElement=this;if(this.onfocus)this.onfocus();}querySelectorAll(){return buttons;}
 }
 const document={body:new E('body'),activeElement:{focus(){}},createElement:t=>new E(t),getElementById:id=>ids[id],addEventListener:(name,fn)=>{(listeners[name]||(listeners[name]=[])).push(fn);}};
 const updates={open(){},rpc(method,payload,callback){calls.push(method);assert.equal(method,'check');return root?new Promise((resolve,reject)=>pending.push({resolve,reject})):pending.push(callback);}};
 const window=root?{RootUpdates:updates}:{HomeUpdates:updates};window.HomeLayoutState={state:()=>({allowColumnOverride:allowColumns,columns:5})};
 const context={window,document,Promise,setTimeout:()=>1,clearTimeout(){},createRootExit:()=>async()=>{},PalmServiceBridge:class{cancel(){}call(uri,raw){rpcCalls.push(uri);if(system&&uri.startsWith('luna://com.cleanyourtv.system.updater.service/')){systemCalls.push({method:uri.split('/').pop(),payload:JSON.parse(raw)});systemPending.push(reply=>this.onservicecallback(JSON.stringify(reply)));return;}if(!root&&uri.endsWith('/homeStatus')){homePending.push(value=>this.onservicecallback(JSON.stringify(value)));return;}this.onservicecallback(JSON.stringify({returnValue:true,result:{returnValue:true,result:{intent:{phase:'disabled'}}},state:{enabled:false}}));}}};
 vm.runInNewContext(fs.readFileSync('launcher/layout-panel.js','utf8'),context);context.HomeLayoutPanel=window.HomeLayoutPanel;
 if(system)vm.runInNewContext(fs.readFileSync('launcher/system-updates.js','utf8'),context);
 vm.runInNewContext(fs.readFileSync(root?'root-edition/ui/root-settings.js':'launcher/renewal-panel.js','utf8'),context);
 return {panel:window.RenewalPanel,columns:()=>ids.homeColumns,focusOther:tag=>{const e=new E(tag);e.focus();return e;},blurToBody:()=>{document.activeElement=document.body;focused=document.body;},layoutChanged:()=>{allowColumns=false;const event={type:'home-layout-change'};(listeners['home-layout-change']||[]).forEach(fn=>fn(event));},calls,systemCalls,replySystem:value=>systemPending.shift()({returnValue:true,result:value}),failSystem:text=>systemPending.shift()({returnValue:false,errorText:text}),rpcCalls,routing:()=>ids.homeRoutingToggle,routingStatus:()=>ids.homeRoutingStatus,replyHome:value=>homePending.shift()(value),button:()=>root?buttons.find(b=>b.textContent==='Software updates'):ids.renewalUpdates,close:()=>root?buttons.find(b=>b.textContent==='Back to Home').onclick():ids.renewalClose.onclick(),reply:value=>{const done=pending.shift();if(root)done.resolve(value);else done(value);},fail:()=>{const done=pending.shift();if(root)done.reject(Error('offline'));else done(null);},focus:()=>focused};
}
(async()=>{
 // Columns can be the old navigation index while a theme's inline Apply owns
 // actual focus. Fixed-column layouts hide Columns during Apply.
 for(const root of [false,true]){
  for(const target of ['button','input']){
   const h=harness(root);h.panel.open();await tick();
   h.columns().focus();const actual=h.focusOther(target);
   h.layoutChanged();assert.equal(h.focus(),actual,'layout change preserves actual inline '+target+' focus in '+(root?'Root':'No-root'));
  }
  {
   const h=harness(root);h.panel.open();await tick();h.columns().focus();h.blurToBody();const actual=h.focus();
   h.layoutChanged();assert.equal(h.focus(),actual,'body focus without current Columns ownership is not a reason to redirect');
  }
  for(const blurred of [false,true]){
   const h=harness(root,false,blurred);h.panel.open();await tick();h.columns().focus();h.layoutChanged();
   assert.notEqual(h.focus(),h.columns(),'hidden focused Columns has a visible fallback');
   assert.equal(h.focus().hidden,false);assert.equal(h.focus().disabled,false);
  }
 }
 const home=harness(false);
 home.panel.open();
 assert.equal(home.routing().hidden,true,'a pending status must not appear off');
 home.replyHome({returnValue:true,enabled:true});
 assert.equal(home.routing().hidden,false);
 assert.equal(home.routing().disabled,false);
 assert.equal(home.routing().attrs['aria-checked'],'true');
 for(const reply of [{returnValue:false,errorText:'Home Helper data unavailable'},null,{returnValue:true,enabled:'false'}]){
  if(!home.routing().disabled)home.routing().focus();home.close();home.panel.open();
  assert.notEqual(home.focus(),home.routing(),'hiding the routing switch must preserve visible focus');
  assert.equal(home.routing().hidden,true,'rechecking must not show the previous choice as current');
  home.replyHome(reply);
  assert.equal(home.routing().hidden,true,'unknown status must not expose an off switch');
  assert.equal(home.routing().disabled,true);
  assert.match(home.routingStatus().textContent,/unknown/);
 }
 if(!home.routing().disabled)home.routing().focus();home.close();home.panel.open();
  assert.notEqual(home.focus(),home.routing(),'hiding the routing switch must preserve visible focus');home.replyHome({returnValue:true,enabled:false});
 assert.equal(home.routing().hidden,false,'a confirmed LG Home choice remains visible');
 assert.equal(home.routing().attrs['aria-checked'],'false');
 assert.equal(home.rpcCalls.some(uri=>uri.endsWith('/setHomeControl')||uri.includes('applicationManager')),false,'opening settings cannot change Home or launch Helper');
 for(const root of [false,true]){
  const h=harness(root);assert.equal(h.calls.length,0,'launcher startup must not check releases');
  h.panel.open();await tick();assert.equal(h.calls.length,1,'settings opening checks automatically');
  h.panel.open();assert.equal(h.calls.length,1,'already-open settings must not check twice');
  h.close();h.panel.open();await tick();assert.equal(h.calls.length,1,'coalesce an in-flight check');
  const focus=h.focus();
  h.reply(root?{canInstall:true,reason:'available'}:{state:'available',canInstall:false});await tick();
  assert.equal(h.button().attrs['data-update-available'],'true');
  assert.equal(h.button().attrs['aria-label'],'Software updates. Update available.');
  assert.equal(h.focus(),focus,'background check must not move remote focus');
  h.close();h.panel.open();await tick();assert.equal(h.calls.length,2);
  h.reply(root?{canInstall:false,reason:'current'}:{state:'newer-installed',canInstall:false});await tick();
  assert.equal(h.button().attrs['data-update-available'],'false','no newer version removes badge');
  assert.equal(h.button().attrs['aria-label'],'Software updates');
  h.close();h.panel.open();await tick();h.reply(root?{canInstall:false,reason:'missing-rollback'}:{state:'helper-update-required',canInstall:false});await tick();
  assert.equal(h.button().attrs['data-update-available'],'true','new release may require computer setup');
  h.close();h.panel.open();await tick();h.fail();await tick();
  assert.equal(h.button().attrs['data-update-available'],'true','network failure retains the last confirmed availability');
  assert(h.panel.isOpen(),'failed update checks must not block settings');
  h.close();h.panel.open();await tick();assert.equal(h.calls.length,5,'a failed request must not prevent the next settings check');h.reply(null);await tick();
 }
 for(const root of [false,true]){
  const h=harness(root,true);h.panel.open();h.panel.open();await tick();
  assert.equal(h.systemCalls.length,1,'reopening settings must coalesce the supervisor check');
  assert.equal(h.systemCalls[0]&&h.systemCalls[0].method,'status','settings must select the same supervisor as the update panel');
  assert.equal(h.calls.length,0,'legacy check must wait for proven supervisor absence');
  h.replySystem(null);await tick();
  assert.equal(h.systemCalls[1].payload.edition,root?'root':'no-root');
  h.replySystem({canInstall:true,components:[{installed:'1.0.0',version:'1.1.0'}]});await tick();
  assert.equal(h.button().attrs['data-update-available'],'true','system update must show a badge even when legacy Home has no update');
  h.close();h.panel.open();await tick();const focus=h.focus();h.replySystem(null);await tick();
  h.replySystem({canInstall:true,components:[{installed:'1.0.0',version:'1.0.0'}]});await tick();
  assert.equal(h.button().attrs['data-update-available'],'false','same-version legacy supervisor offers must not light the badge');
  assert.equal(h.focus(),focus);
  h.close();h.panel.open();await tick();h.replySystem(null);await tick();h.failSystem('Update information could not be verified.');await tick();
  assert.equal(h.calls.length,0,'a failed check on an existing supervisor must not switch feed');
  h.close();h.panel.open();await tick();h.failSystem('Service does not exist');await tick();
  assert.equal(h.calls.length,1,'only a missing supervisor may use the legacy badge');
  h.reply(root?{canInstall:true}:{state:'available'});await tick();
  assert.equal(h.button().attrs['data-update-available'],'true');
 }
 console.log('PASS both settings check releases on open, show accessible badges, coalesce requests and preserve focus');
})().catch(error=>{console.error(error);process.exit(1);});

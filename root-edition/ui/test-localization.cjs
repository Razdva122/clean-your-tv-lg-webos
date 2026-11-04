const assert=require('node:assert/strict'),vm=require('vm'),fs=require('fs');
const buttons=[],listeners={},calls=[];let languageOpened=0;let selected,phase='active',restores=0,failLaunch=false;
class Element {
 constructor(tag){this.tag=tag;this.hidden=false;this.disabled=false;this.attrs={};if(tag==='button')buttons.push(this);}
 appendChild(){} setAttribute(k,v){this.attrs[k]=v;} focus(){selected=this;if(this.onfocus)this.onfocus();}
}
const document={body:new Element('body'),activeElement:{focus(){selected='previous';}},createElement:t=>new Element(t),addEventListener:(n,f)=>listeners[n]=f};
const context={window:{close(){},HomeI18n:{t:s=>'translated:'+s,openLanguagePicker(){languageOpened++;}},RootUpdates:{open(){}}},document,Promise,setTimeout,clearTimeout,
 createRootExit:(call,launch)=>async()=>{restores++;phase='disabled';await launch();},
 PalmServiceBridge:class{cancel(){}call(uri,raw){calls.push({uri,payload:JSON.parse(raw)});let r={returnValue:true};
 if(uri.endsWith('/status'))r.result={returnValue:true,result:{intent:{phase}}};
 if(uri.endsWith('/enable')){phase='active';r.result={returnValue:true,result:{}};}
 if(uri.endsWith('/launch')&&failLaunch)r.returnValue=false;
 this.onservicecallback(JSON.stringify(r));}}
};
vm.runInNewContext(fs.readFileSync(__dirname+'/root-settings.js','utf8'),context);
const panel=context.window.RenewalPanel,tick=()=>new Promise(r=>setImmediate(r));
function key(keyCode){listeners.keydown({keyCode,preventDefault(){},stopImmediatePropagation(){}});}
(async()=>{
 panel.open();await tick();const language=buttons.find(b=>b.textContent==='translated:Language');assert(language,'localized language selector is available');language.onclick();assert.equal(languageOpened,1);assert.equal(buttons[0].textContent,'translated:Change Home');buttons[0].focus();assert.equal(selected,buttons[0]);assert.equal(buttons[0].attrs['aria-checked'],'true');
 key(39);assert.equal(selected,buttons[1]);key(13);key(13);await tick();
 assert.equal(calls.filter(c=>c.uri.endsWith('/launch')).length,1);assert.equal(restores,0);assert.equal(phase,'active');assert(!panel.isOpen());
 panel.open();await tick();buttons[0].onclick();await tick();assert.equal(restores,1);assert.equal(buttons[0].attrs['aria-checked'],'false');assert(panel.isOpen());
 buttons[0].onclick();await tick();assert.equal(phase,'active');assert.equal(buttons[0].attrs['aria-checked'],'true');assert(!buttons[0].disabled);
 failLaunch=true;buttons[1].onclick();await tick();assert(panel.isOpen());assert.equal(phase,'active');assert(!buttons[1].disabled);key(461);assert(!panel.isOpen());
 console.log('PASS Root switch, one-time visit, failure recovery, duplicate suppression and remote focus');
})().catch(e=>{console.error(e);process.exit(1);});

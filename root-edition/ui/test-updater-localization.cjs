const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const catalogs={};const catalogContext={window:{HomeI18n:{add:values=>Object.assign(catalogs,values)}}};
vm.runInNewContext(fs.readFileSync(__dirname+'/root-locales.js','utf8'),catalogContext);
const html=fs.readFileSync(__dirname+'/../../updater-app/index.html','utf8');
for(const locale of Object.keys(catalogs)){
 const elements={};for(const match of html.matchAll(/<(?:h1|p|button)[^>]*data-i18n="([^"]+)"[^>]*>/g)){const id=match[0].match(/id="([^"]+)"/);elements[id?id[1]:match[1]]={source:match[1],textContent:match[1],setAttribute(){},focus(){},click(){if(!this.disabled)this.onclick();}};}
 elements.status={textContent:'Reading status…'};
 for(const id of ['guidance','diagnostic','details'])elements[id]=elements[id]||{textContent:'',setAttribute(){}};
 let confirmation;const callbacks=[];let status='awaiting-launch';
 const tr=(source,params)=>String(catalogs[locale][source]||source).replace(/\{(\w+)\}/g,(_,key)=>params?.[key]??'{'+key+'}');
 const document={getElementById:id=>elements[id],body:{},addEventListener(){}};
 const context={window:{HomeI18n:{ready:cb=>callbacks.push(cb),t:tr,confirm:(options,accept)=>{confirmation={options,accept};},apply(){for(const element of Object.values(elements))if(element.source)element.textContent=tr(element.source);}}},document,setTimeout:()=>1,clearTimeout(){},PalmServiceBridge:class{cancel(){}call(uri){this.onservicecallback(JSON.stringify({returnValue:true,result:{status,prior:{home:'1.3.5'}}}));}}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/../../updater-app/app.js','utf8'),context);
 assert.equal(elements.refresh.onclick,undefined,'waits for TV locale');callbacks.forEach(cb=>cb());
 assert.equal(document.title,tr('Home Updater'));assert.equal(elements.refresh.textContent,tr('Refresh status'));
 assert.equal(elements.status.textContent,tr('An update is in progress.'));
 elements.restore.onclick();assert.equal(elements.restore.textContent,tr('Restore previous Home'));assert.equal(confirmation.options.action,'Restore previous Home');
 assert.equal(confirmation.options.message,tr('Restore the previous Home version and pre-update settings. Settings changed after the update will be lost. Keep the TV powered on.'));
 status='rolled-back';confirmation.accept();assert.equal(elements.status.textContent,tr('No recovery needed.'));
}
console.log('PASS independent updater startup, status, restore confirmation and diagnostic codes in thirteen languages');

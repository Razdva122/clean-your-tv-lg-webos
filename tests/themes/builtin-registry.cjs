'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('launcher/theme-manager.js','utf8');
const entry=(id='example')=>({id:'builtin:'+id,title:id==='example'?'Example':'Alpine',version:'1.0.0',url:'themes/'+id+'/cytv-theme.json',digest:'a'.repeat(64)});
const registry={schemaVersion:1,themes:[entry('alpine'),entry()]};
function fixture(saved,entries=registry){
 const values=new Map(saved?[['tvhome.theme.choice.v1',JSON.stringify(saved)]]:[]),calls=[],loaded=[],state={visual:'builtin:classic'};
 const local={schemaVersion:1,themes:[{id:'builtin:classic',title:'Classic',builtin:true,preview:'theme-catalog/classic.png'},{id:'builtin:example',title:'Example',builtin:true,preview:'themes/example/preview.png'}]};
 const remote={schemaVersion:1,themes:[...local.themes,{id:'builtin:future',title:'Future',builtin:true,preview:'themes/future/preview.png'}]};
 const context={Promise,Date,setTimeout,clearTimeout,requestAnimationFrame:fn=>fn(),CustomEvent:function(){},document:{dispatchEvent(){}},localStorage:{getItem:k=>values.has(k)?values.get(k):null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},ThemeRuntime:{reset(){state.visual='builtin:classic';},apply(input){state.visual=input.manifest.id;}},ThemeStore:{list:async()=>[],get:async()=>{throw Error('Built-ins must work offline without store');}},ThemeData:{decode:JSON.stringify,path(value){if(typeof value!=='string'||value.includes('..'))throw Error('Unsafe path');return value;},request:async(url,limit,isLocal)=>{calls.push({url,isLocal});if(url==='appinfo.json')return {version:'1.6.0'};if(url==='builtin-themes.json')return entries;if(url==='theme-catalog.json')return local;if(url.includes('api.github.com'))return {ref:'refs/heads/main',object:{sha:'a'.repeat(40),type:'commit'}};return remote;},load:async(record,version,signal,progress,isLocal)=>{assert.equal(isLocal,true);assert.equal(record.url,'themes/'+record.id.slice(8)+'/cytv-theme.json');loaded.push(record);return {id:record.id,digest:record.digest};},prepare:async pack=>({manifest:{id:pack.id,title:pack.id==='builtin:example'?'Example':'Alpine'},assetHandles:{}}),dispose(){}}};
 vm.runInNewContext(source,context);return {manager:context.ThemeManager,values,calls,loaded,state,local,remote};
}
(async()=>{
 let f=fixture();await f.manager.start();assert.equal(f.manager.current().id,'builtin:classic');assert.equal(f.calls.length,0,'Classic remains default without loading themes');
 const items=await f.manager.list();assert.deepEqual(Array.from(items,item=>item.id),['builtin:classic','builtin:alpine','builtin:example']);
 await f.manager.selectInstalled({id:'builtin:example',url:'https://evil.example/theme.json'});assert.equal(f.state.visual,'builtin:example');assert.equal(JSON.parse(f.values.get(f.manager.choiceKey)).id,'builtin:example');assert.equal(f.loaded[0].url,entry().url);
 await f.manager.begin({id:'builtin:alpine'});await f.manager.cancel();assert.equal(f.state.visual,'builtin:example');f.manager.reset();assert.equal(f.state.visual,'builtin:classic');assert.equal(f.values.has(f.manager.choiceKey),false);
 await assert.rejects(f.manager.selectInstalled({id:'builtin:unknown'}),/not installed/);await assert.rejects(f.manager.begin({id:'builtin:unknown'}),/Unknown built-in/);assert.equal(f.state.visual,'builtin:classic');
 f=fixture({id:'builtin:example',title:'Example'});await f.manager.start();assert.equal(f.state.visual,'builtin:example');assert.equal(f.calls.every(call=>call.isLocal===true),true,'saved bundled theme boots entirely offline');
 f=fixture({id:'builtin:unknown',title:'Unknown'});await f.manager.start();assert.equal(f.state.visual,'builtin:classic');assert.equal(f.values.has(f.manager.choiceKey),false);assert.match(f.manager.current().notice,/Unknown built-in/);
 f=fixture();const catalog=await f.manager.catalog();assert.deepEqual(Array.from(catalog,item=>item.id),['builtin:classic','builtin:example']);assert.equal(catalog.notice,undefined,'remote future built-ins do not break live catalog');
 for(const record of [{...entry(),id:'builtin:classic'},{...entry(),id:'builtin:../bad'},{...entry(),url:'https://evil.example/x'},{...entry(),url:'themes/example/../cytv-theme.json'},{...entry(),title:''},{...entry(),version:'latest'},{...entry(),digest:'x'}])await assert.rejects(fixture(null,{schemaVersion:1,themes:[record]}).manager.list(),/Built-in theme catalog/);
 await assert.rejects(fixture(null,{schemaVersion:1,themes:[entry(),entry()]}).manager.list(),/Built-in theme catalog/);
 await assert.rejects(fixture(null,{schemaVersion:1,themes:Array.from({length:33},(_,index)=>entry('theme-'+index))}).manager.list(),/Built-in theme catalog/);
 console.log('PASS generic trusted bundled registry, offline boot, selection, reset and unknown recovery');
})().catch(error=>{console.error(error);process.exitCode=1;});

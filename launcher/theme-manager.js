/* Accepted appearance, offline cache and durable trial/boot recovery. */
(function(root){
 'use strict';var data=root.ThemeData,choiceKey='tvhome.theme.choice.v1',trialKey='tvhome.theme.trial.v1',active={id:'builtin:classic',title:'Classic'},trial=null,ready,homeVersion,notice='',builtin,generation=0,rollback=null;
 function emit(){document.dispatchEvent(new CustomEvent('home-theme-change'));}
 function current(){return {id:active.id,title:active.title,digest:active.digest||null,notice:notice,trial:!!trial};}
 function classic(){root.ThemeRuntime.reset();active={id:'builtin:classic',title:'Classic'};}
 function persist(choice){localStorage.setItem(choiceKey,JSON.stringify(choice));if(localStorage.getItem(choiceKey)!==JSON.stringify(choice))throw Error('Could not save theme selection');}
 function recover(error){generation++;if(trial)clearTimeout(trial.timer);trial=null;rollback=null;classic();try{localStorage.removeItem(choiceKey);localStorage.removeItem(trialKey);}catch(_){}notice=error||'Theme recovery: Classic restored';emit();}
 function selection(){var raw=localStorage.getItem(choiceKey);if(raw===null)return {id:'builtin:classic',title:'Classic'};var s=JSON.parse(raw);if(!s||typeof s.id!=='string'||typeof s.title!=='string'||s.title.length>100||!/^builtin:[a-z0-9][a-z0-9-]{0,63}$/.test(s.id)&&!/^github:/.test(s.id)||s.id.indexOf('github:')===0&&!/^[a-f0-9]{64}$/.test(s.digest))throw Error('Invalid saved theme selection');return s;}
 // The caller exposes Home only after validated appearance (or bounded Classic recovery).
 function start(present){if(ready)return ready;if(root.CYTV_THEME_AUTHOR_PREVIEW){ready=Promise.resolve().then(function(){if(present)present();});return ready;}
  ready=new Promise(function(resolve,reject){
   var token=generation,marker=null,finished=false,timer=setTimeout(function(){finish(Error('Theme startup timed out. Classic restored'));},8000);
   function finish(error){
    if(finished)return;finished=true;clearTimeout(timer);
    try{if(error&&token===generation)recover(error.message);if(present)present();}catch(e){reject(e);return;}
    requestAnimationFrame(function(){requestAnimationFrame(function(){
     if(marker)try{if(localStorage.getItem(trialKey)===marker)localStorage.removeItem(trialKey);}catch(_){}
     emit();resolve();
    });});
   }
   Promise.resolve().then(function(){
    var saved;if(localStorage.getItem(trialKey)!==null){recover('An interrupted theme preview was reset to Classic');return;}
    saved=selection();if(saved.id==='builtin:classic')return;
    marker=JSON.stringify({kind:'boot',id:saved.id});localStorage.setItem(trialKey,marker);if(localStorage.getItem(trialKey)!==marker)throw Error('Could not save theme recovery marker');
    return environment().then(function(){return payload(saved);}).then(function(pack){return apply(pack,saved,token);});
   }).then(function(){finish();},finish);
  });return ready;
 }
 function bundled(id){return builtin&&builtin.themes.filter(function(entry){return entry.id===id;})[0];}
 function registry(){if(builtin)return Promise.resolve();return data.request('builtin-themes.json',65536,true).then(function(bytes){
  var catalog=JSON.parse(data.decode(bytes)),seen=Object.create(null);
  if(!catalog||catalog.schemaVersion!==1||!Array.isArray(catalog.themes)||catalog.themes.length>32)throw Error('Built-in theme catalog is invalid');
  catalog.themes.forEach(function(entry){
   if(!entry||typeof entry.id!=='string'||!/^builtin:[a-z0-9][a-z0-9-]{0,63}$/.test(entry.id)||entry.id==='builtin:classic'||seen[entry.id]||typeof entry.title!=='string'||!entry.title||entry.title.length>100||/[\u0000-\u001f\u007f]/.test(entry.title)||typeof entry.version!=='string'||entry.version.length>64||!/^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/.test(entry.version)||typeof entry.url!=='string'||!/^themes\/[a-z0-9][a-z0-9-]{0,63}\/cytv-theme\.json$/.test(entry.url)||typeof entry.digest!=='string'||! /^[a-f0-9]{64}$/.test(entry.digest))throw Error('Built-in theme catalog entry is invalid');
   seen[entry.id]=true;
  });builtin=catalog;
 });}
 function environment(){if(homeVersion&&builtin)return Promise.resolve();return data.request('appinfo.json',65536,true).then(function(a){var info=JSON.parse(data.decode(a)),engine=info.themeEngineVersion===undefined?info.version:info.themeEngineVersion;if(typeof engine!=='string'||engine.length>32||!/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(engine))throw Error('Home version unavailable');homeVersion=engine;return registry();});}
 function payload(s){if(s.id.indexOf('builtin:')===0){var entry=bundled(s.id);if(!entry)return Promise.reject(Error('Unknown built-in theme'));return data.load(entry,homeVersion,null,null,true);}return root.ThemeStore.get(s.digest).then(function(pack){if(!pack)throw Error('Saved theme files are missing');var parsed=data.verify(pack,homeVersion);if(parsed.manifest.id!==s.id)throw Error('Saved theme identity mismatch');return pack;});}
 function apply(pack,s,token){return data.prepare(pack,homeVersion,function(){return token!==undefined&&token!==generation;}).then(function(input){try{if(token!==undefined&&token!==generation)throw Error('Cancelled');root.ThemeRuntime.apply(input);active={id:s.id,title:input.manifest.title,digest:pack.digest};emit();}catch(e){data.dispose(input.assetHandles);throw e;}});}
 function list(){return start().then(environment).then(function(){return root.ThemeStore.list().catch(function(e){notice=e.message;return [];});}).then(function(packages){var items=[{id:'builtin:classic',title:'Classic',builtin:true}];builtin.themes.forEach(function(entry){items.push({id:entry.id,title:entry.title,builtin:true,version:entry.version,digest:entry.digest});});packages.forEach(function(pack){try{var parsed=data.verify(pack,homeVersion);if(parsed.manifest.id.indexOf('github:')!==0)throw Error('Invalid external identity');items.push({id:parsed.manifest.id,title:parsed.manifest.title,digest:pack.digest,version:parsed.manifest.themeVersion,license:parsed.manifest.license.identifier,author:parsed.manifest.author.name});}catch(_){notice='An invalid cached theme was ignored';}});return items;});}
 function preview(item){
  if(!item||typeof item.id!=='string'||item.id.indexOf('github:')!==0||! /^[a-f0-9]{64}$/.test(item.digest))return Promise.reject(Error('Invalid installed preview'));
  return environment().then(function(){return root.ThemeStore.get(item.digest);}).then(function(pack){
   if(!pack)throw Error('Installed theme files are missing');
   if(pack.digest!==item.digest)throw Error('Installed preview digest mismatch');
   var parsed=data.verify(pack,homeVersion),m=parsed.manifest;if(m.id!==item.id)throw Error('Installed preview identity mismatch');
   var asset=m.assets.filter(function(a){return a.id===m.previewAssetId;})[0];if(!asset)throw Error('Installed preview asset is missing');
   var url=root.URL.createObjectURL(new root.Blob([pack.files[asset.path]],{type:asset.mediaType})),disposed=false;
   return {url:url,dispose:function(){if(!disposed){disposed=true;root.URL.revokeObjectURL(url);}}};
  });
 }

 function begin(s,immediate){if(trial)return Promise.reject(Error('Finish the current theme preview first'));var token=++generation;return start().then(environment).then(function(){if(token!==generation)throw Error('Cancelled');var previous=selection();localStorage.setItem(trialKey,JSON.stringify({kind:'trial',id:s.id,previous:previous}));trial={previous:previous,choice:s,expires:Date.now()+20000,timer:null};
   return (s.id==='builtin:classic'?Promise.resolve().then(classic):payload(s).then(function(pack){return apply(pack,s,token);})).then(function(){if(token!==generation)throw Error('Cancelled');trial.expires=Date.now()+20000;if(!immediate)trial.timer=setTimeout(cancel,20000);emit();},function(e){if(token!==generation)throw e;return cancel().then(function(){throw e;});});
  });}
 function selectInstalled(s){if(trial)return Promise.reject(Error('Finish the current theme preview first'));var token=++generation;return list().then(function(items){
  if(token!==generation)throw Error('Cancelled');
  var installed=items.filter(function(item){return s&&item.id===s.id&&(item.builtin===true||item.digest===s.digest);})[0];
  if(!installed)throw Error('Theme is not installed');
  return begin(installed,true).then(confirm);
 });}

 function cancel(){var token=++generation;if(!trial&&!rollback)return Promise.resolve();var state={previous:trial?trial.previous:rollback.previous};if(trial)clearTimeout(trial.timer);trial=null;rollback=state;
  var restore=state.previous.id==='builtin:classic'?Promise.resolve().then(function(){if(token===generation)classic();}):payload(state.previous).then(function(pack){return apply(pack,state.previous,token);});
  return restore.catch(function(e){if(token===generation)recover(e.message);}).then(function(){if(rollback===state)rollback=null;if(token!==generation)return;try{localStorage.removeItem(trialKey);}catch(e){recover(e.message);}emit();});
 }

 function confirm(){if(!trial)return Promise.reject(Error('No theme preview to keep'));var state=trial;try{persist({id:active.id,title:active.title,digest:active.digest||null});localStorage.removeItem(trialKey);clearTimeout(state.timer);trial=null;rollback=null;notice='';emit();return Promise.resolve();}catch(e){try{persist(state.previous);}catch(_){recover(e.message);return Promise.reject(e);}return cancel().then(function(){throw e;});}}

 function savePackage(pack,signal){return data.prepare(pack,homeVersion,function(){return signal&&signal.cancelled;}).then(function(input){data.dispose(input.assetHandles);if(signal&&signal.cancelled)throw Error('Cancelled');var parsed=data.verify(pack,homeVersion);return root.ThemeStore.put(pack,parsed.size,signal).then(function(){emit();return {id:parsed.manifest.id,title:parsed.manifest.title,digest:pack.digest,version:parsed.manifest.themeVersion,author:parsed.manifest.author.name,license:parsed.manifest.license.identifier};});});}
 function install(entry,signal,progress){return start().then(environment).then(function(){return data.load(entry,homeVersion,signal,progress,false);}).then(function(pack){return savePackage(pack,signal);});}

 function installEnvelope(envelope,signal){return start().then(environment).then(function(){if(signal&&signal.cancelled)throw Error('Cancelled');return savePackage(data.unpackEnvelope(envelope,homeVersion),signal);});}
 function catalogEntries(bytes){
  var catalog=JSON.parse(data.decode(bytes));if(!catalog||catalog.schemaVersion!==1||!Array.isArray(catalog.themes)||catalog.themes.length>64)throw Error('Invalid theme catalog');var seen=Object.create(null);
  var entries=[];catalog.themes.forEach(function(item){
   if(!item||typeof item.id!=='string'||typeof item.title!=='string'||!item.title||item.title.length>100||seen[item.id])throw Error('Invalid theme catalog entry');seen[item.id]=true;
   if(item.builtin===true&&item.id!=='builtin:classic'&&!bundled(item.id))return;
   data.path(item.preview);if(!/^(theme-catalog|themes\/[a-z0-9][a-z0-9-]{0,63})\//.test(item.preview))throw Error('Invalid theme preview');
   if(item.builtin!==true){
    var origin=data.source(item.url),identity=/^github:([a-z0-9][a-z0-9-]*)\/([a-z0-9][a-z0-9._-]*):([a-z0-9][a-z0-9-]{0,63})$/.exec(item.id);
    if(item.builtin!==undefined||!origin.commit||!identity||identity[1]!==origin.owner||identity[2]!==origin.repo||! /^[a-f0-9]{64}$/.test(item.digest))throw Error('Invalid theme catalog source');
    ['version','author','license','description'].forEach(function(key){if(typeof item[key]!=='string'||!item[key]||item[key].length>(key==='description'?2000:200))throw Error('Invalid theme catalog details');});
   }
   entries.push(item);
  });return entries;
 }
 function catalog(signal,onLocal){
  var local,project='https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/';
  function cancelled(){if(signal&&signal.cancelled)throw Error('Cancelled');}
  return Promise.resolve().then(function(){cancelled();return registry();}).then(function(){cancelled();return data.request('theme-catalog.json',65536,true,signal);}).then(function(bytes){
   cancelled();var bundled=catalogEntries(bytes);if(onLocal)onLocal(bundled);local=bundled;return data.request('https://api.github.com/repos/Razdva122/clean-your-tv-lg-webos/git/ref/heads/main',65536,false,signal);
  }).then(function(bytes){
   cancelled();var ref=JSON.parse(data.decode(bytes)),commit=ref&&ref.object;if(!ref||ref.ref!=='refs/heads/main'||!commit||commit.type!=='commit'||! /^[a-f0-9]{40}$/.test(commit.sha))throw Error('Invalid theme catalog commit');
   var base=project+commit.sha+'/launcher/';return data.request(base+'theme-catalog.json',65536,false,signal).then(function(bytes){
    cancelled();var remote=catalogEntries(bytes),items=local.filter(function(item){return item.builtin===true;});
    remote.forEach(function(item){if(item.builtin!==true){item.preview=base+item.preview;items.push(item);}});return items;
   });
  }).catch(function(error){cancelled();if(error.message==='Cancelled'||!local)throw error;local.notice='Showing bundled themes. Live catalogue could not be refreshed.';return local;});
 }

 function remove(s){if(trial||active.digest===s.digest)return Promise.reject(Error('Switch to another theme before removing this version'));return root.ThemeStore.remove(s.digest).then(emit);}
 root.ThemeManager={start:start,list:list,preview:preview,current:current,begin:begin,selectInstalled:selectInstalled,cancel:cancel,confirm:confirm,install:install,installEnvelope:installEnvelope,catalog:catalog,remove:remove,resolve:function(url,signal){return start().then(environment).then(function(){return data.resolve(url,signal);});},remaining:function(){return trial?Math.max(0,Math.ceil((trial.expires-Date.now())/1000)):0;},reset:function(){generation++;if(trial)clearTimeout(trial.timer);trial=null;recover('Classic restored');},choiceKey:choiceKey,trialKey:trialKey};
}(this));

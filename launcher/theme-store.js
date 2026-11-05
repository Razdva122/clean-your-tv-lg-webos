/* Application-owned binary theme cache. Legacy profiles never contain image bytes. */
(function(root){
 'use strict';var database;
 function translate(source,values){var language=root.HomeI18n&&root.HomeI18n.language(),strings=root.HomeWallpaperLocales&&root.HomeWallpaperLocales[language],text=strings&&strings[source]||source;return text.replace(/\{([a-z]+)\}/g,function(_,key){return values[key];});}
 function budget(required,available,location){return {location:location||'TV app storage',required:required,available:available,shortfall:available===null?null:Math.max(0,required-available)};}
 function format(b){function mib(n,up){return ((up?Math.ceil(n*10/1048576):Math.floor(n*10/1048576))/10).toFixed(1);}return translate(b.available===null?'Storage estimate ({location}): required {required} MiB; available and shortfall could not be determined.':'Storage estimate ({location}): required {required} MiB; available {available} MiB; shortfall {shortfall} MiB.',{location:translate(b.location,{}),required:mib(b.required,true),available:b.available===null?'?':mib(b.available,false),shortfall:b.shortfall===null?'?':mib(b.shortfall,true)});}
 function full(b){var error=Error(format(b));error.code='storage-full';error.budget=b;return error;}
 function estimate(required){return new Promise(function(resolve){var settled=false,timer=setTimeout(function(){finish(null);},2000),nav=root.navigator||{};
  function finish(value){if(settled)return;settled=true;clearTimeout(timer);var available=value&&typeof value.usage==='number'&&typeof value.quota==='number'&&isFinite(value.usage)&&isFinite(value.quota)&&value.usage>=0&&value.quota>=value.usage?Math.floor(value.quota-value.usage):null;resolve(budget(required,available));}
  try{if(nav.storage&&typeof nav.storage.estimate==='function')Promise.resolve(nav.storage.estimate()).then(finish,function(){finish(null);});else if(nav.webkitTemporaryStorage&&typeof nav.webkitTemporaryStorage.queryUsageAndQuota==='function')nav.webkitTemporaryStorage.queryUsageAndQuota(function(usage,quota){finish({usage:usage,quota:quota});},function(){finish(null);});else finish(null);}catch(_){finish(null);}
 });}
 function check(required){return estimate(required).then(function(b){if(b.shortfall>0)throw full(b);return b;});}
 function quotaFailure(error,required){if(!error||error.name!=='QuotaExceededError')throw error;return estimate(required).then(function(b){if(!b.shortfall){b.available=null;b.shortfall=null;}throw full(b);});}
 root.StorageBudget={quotaFailure:quotaFailure,check:check,estimate:estimate,format:format,full:full,budget:budget};

 function open(){if(database)return database;database=new Promise(function(resolve,reject){if(!root.indexedDB)return reject(Error('Theme storage is unavailable'));var settled=false,request=root.indexedDB.open('ctv-themes-v1',1),timer=setTimeout(function(){settled=true;database=null;reject(Error('Theme storage timed out'));},8000);
  request.onupgradeneeded=function(){request.result.createObjectStore('packages',{keyPath:'digest'});};
  request.onsuccess=function(){clearTimeout(timer);var db=request.result;if(settled){db.close();return;}settled=true;db.onversionchange=function(){db.close();database=null;};resolve(db);};request.onerror=function(){if(settled)return;settled=true;clearTimeout(timer);database=null;reject(Error('Could not open theme storage'));};request.onblocked=function(){if(settled)return;settled=true;clearTimeout(timer);database=null;reject(Error('Close other Home windows before changing themes'));};
 });return database;}
 function operation(mode,action,signal){return open().then(function(db){return new Promise(function(resolve,reject){
  if(signal&&signal.cancelled){reject(Error('Cancelled'));return;}
  var tx=db.transaction(['packages'],mode),result,previousCancel=signal&&signal.cancel,timer=setTimeout(function(){try{tx.abort();}catch(_){}reject(Error('Theme storage timed out'));},8000);
  function abort(){if(previousCancel)previousCancel();try{tx.abort();}catch(_){}}
  function cleanup(){clearTimeout(timer);if(signal&&signal.cancel===abort)signal.cancel=previousCancel;}
  if(signal)signal.cancel=abort;
  tx.oncomplete=function(){cleanup();resolve(result);};tx.onabort=tx.onerror=function(event){cleanup();var cause=tx.error||event&&event.target&&event.target.error;reject(tx.storageError||cause&&cause.name==='QuotaExceededError'&&cause||Error(signal&&signal.cancelled?'Cancelled':'Could not save theme. Check available app storage.'));};
  try{action(tx.objectStore('packages'),function(v){result=v;},tx);}catch(e){cleanup();try{tx.abort();}catch(_){}reject(e);}
 });});}
 function list(){return operation('readonly',function(store,set){var out=[],cursor=store.openCursor();cursor.onsuccess=function(){var c=cursor.result;if(c){out.push(c.value);c.continue();}else set(out);};});}
 function put(pack,size,signal,report){return check(size*2+1048576).then(function(b){if(report)report(b);return operation('readwrite',function(store,set,tx){var total=size,count=1,cursor=store.openCursor();cursor.onsuccess=function(){if(signal&&signal.cancelled){tx.abort();return;}var c=cursor.result;if(c){if(c.key!==pack.digest){var stored=c.value;if(!stored.descriptor||!stored.files){tx.abort();return;}var storedSize=stored.descriptor.byteLength||0;Object.keys(stored.files).forEach(function(k){storedSize+=stored.files[k].byteLength||0;});total+=storedSize;count++;}c.continue();}else if(total>64*1024*1024){tx.storageError=full(budget(size,Math.max(0,64*1024*1024-(total-size)),'Theme cache'));tx.abort();}else if(count>8){tx.storageError=Error('Remove a downloaded theme before adding another (8 themes maximum).');tx.abort();}else{pack.size=size;store.put(pack);set(pack.digest);}};},signal).catch(function(error){return quotaFailure(error,size*2+1048576);});});}
 root.ThemeStore={list:list,clear:function(){return operation('readwrite',function(store){store.clear();});},get:function(digest){return operation('readonly',function(store,set){var r=store.get(digest);r.onsuccess=function(){set(r.result);};});},put:put,remove:function(digest){return operation('readwrite',function(store){store.delete(digest);});}};
}(this));

/* Application-owned binary theme cache. Legacy profiles never contain image bytes. */
(function(root){
 'use strict';var database;
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
  tx.oncomplete=function(){cleanup();resolve(result);};tx.onabort=tx.onerror=function(){cleanup();reject(Error(signal&&signal.cancelled?'Cancelled':'Could not save theme. Check available app storage.'));};
  try{action(tx.objectStore('packages'),function(v){result=v;},tx);}catch(e){cleanup();try{tx.abort();}catch(_){}reject(e);}
 });});}
 function list(){return operation('readonly',function(store,set){var out=[],cursor=store.openCursor();cursor.onsuccess=function(){var c=cursor.result;if(c){out.push(c.value);c.continue();}else set(out);};});}
 function put(pack,size,signal){return operation('readwrite',function(store,set,tx){var total=size,count=1,cursor=store.openCursor();cursor.onsuccess=function(){if(signal&&signal.cancelled){tx.abort();return;}var c=cursor.result;if(c){if(c.key!==pack.digest){var stored=c.value;if(!stored.descriptor||!stored.files){tx.abort();return;}var storedSize=stored.descriptor.byteLength||0;Object.keys(stored.files).forEach(function(k){storedSize+=stored.files[k].byteLength||0;});total+=storedSize;count++;}c.continue();}else if(total>64*1024*1024||count>8)tx.abort();else{pack.size=size;store.put(pack);set(pack.digest);}};},signal);}
 root.ThemeStore={list:list,clear:function(){return operation('readwrite',function(store){store.clear();});},get:function(digest){return operation('readonly',function(store,set){var r=store.get(digest);r.onsuccess=function(){set(r.result);};});},put:put,remove:function(digest){return operation('readwrite',function(store){store.delete(digest);});}};
}(this));

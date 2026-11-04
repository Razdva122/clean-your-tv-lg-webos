/* Temporary edition-owned LS2 receiver. PINs exist only in the active view. */
(function(root){
 'use strict';var limit=ThemePolicy.limits.envelopeBytes,chunkLimit=48*1024;
 function service(){return 'luna://'+(document.querySelector('script[src="root-settings.js"]')?'com.cleanyourtv.root.preview.service':'com.gathin.tvhome.renewal')+'/';}
 function rpc(method,payload,signal){return new Promise(function(resolve,reject){var bridge,done=false,timer=setTimeout(function(){finish(Error('Theme receiver unavailable. Update Home and its service, then try again.'));},method==='themeReceiverStart'?10000:5000);
  function finish(error,value){if(done)return;done=true;clearTimeout(timer);if(bridge&&!(error&&method==='themeReceiverStart'))try{bridge.cancel();}catch(_){}if(error)reject(error);else resolve(value);}
  try{bridge=new root.PalmServiceBridge();bridge.onservicecallback=function(raw){var response;try{response=JSON.parse(raw);}catch(_){finish(Error('Invalid theme receiver response'));return;}
   if(method==='themeReceiverStart'&&(done||signal&&signal.cancelled)&&response&&response.returnValue===true&&typeof response.sessionId==='string'){stop(response.sessionId);try{bridge.cancel();}catch(_){}finish(Error('Cancelled'));return;}
   if(signal&&signal.cancelled){finish(Error('Cancelled'));return;}if(!response||response.returnValue!==true){finish(Error('Theme receiver unavailable. Update Home and its service, then try again.'));return;}finish(null,response);
  };bridge.call(service()+method,JSON.stringify(payload));}catch(_){finish(Error('Theme receiver unavailable. Update Home and its service, then try again.'));}
 });}
 function stop(id){return rpc('themeReceiverStop',{sessionId:id}).catch(function(){});}
 function privateAddress(value){var p=typeof value==='string'&&value.split('.');return p&&p.length===4&&p.every(function(v){return /^(0|[1-9][0-9]{0,2})$/.test(v)&&+v<=255;})&&(+p[0]===10||+p[0]===192&&+p[1]===168||+p[0]===172&&+p[1]>=16&&+p[1]<=31);}
 function start(signal,kind){return rpc('themeReceiverStart',kind==='wallpaper'?{kind:'wallpaper'}:{},signal).then(function(s){if(kind==='wallpaper'&&(s.kind!=='wallpaper'||s.wallpaperProtocol!==1)){if(typeof s.sessionId==='string')stop(s.sessionId);throw Error('Wallpaper receiver unavailable. Update Home and its service.');}if(typeof s.sessionId!=='string'||!s.sessionId||s.sessionId.length>200||!/^\d{6}$/.test(s.pin)||!Array.isArray(s.addresses)||!s.addresses.length||s.addresses.length>32||!s.addresses.every(privateAddress)||s.port!==8879||typeof s.expiresAt!=='number'||s.expiresAt<=Date.now()||s.expiresAt>Date.now()+610000){if(typeof s.sessionId==='string')stop(s.sessionId);throw Error('Invalid theme receiver response');}return s;});}
 function status(id,signal){return rpc('themeReceiverStatus',{sessionId:id},signal).then(function(s){if(['waiting','receiving','received'].indexOf(s.state)<0)throw Error('Theme receiver session expired. Try again.');if(s.state==='received'&&(!Number.isInteger(s.size)||s.size<=0||s.size>limit))throw Error('Invalid received theme size');return s;});}
 function read(id,size,signal){if(!Number.isInteger(size)||size<=0||size>limit)return Promise.reject(Error('Invalid received theme size'));var bytes=new Uint8Array(size),offset=0;
  function next(){if(signal&&signal.cancelled)throw Error('Cancelled');return rpc('themeReceiverRead',{sessionId:id,offset:offset},signal).then(function(part){if(part.offset!==offset||typeof part.data!=='string'||part.data.length>4*Math.ceil(chunkLimit/3)||part.data.length%4!==0||/[^A-Za-z0-9+/=]/.test(part.data)||/=[^=]|={3}/.test(part.data))throw Error('Invalid received theme chunk');var raw=atob(part.data),end=offset+raw.length;if(!raw.length||raw.length>chunkLimit||end>size||part.nextOffset!==end||part.done!==(end===size))throw Error('Invalid received theme chunk');for(var i=0;i<raw.length;i++)bytes[offset+i]=raw.charCodeAt(i);offset=end;if(!part.done)return next();if(signal&&signal.cancelled)throw Error('Cancelled');return JSON.parse(root.ThemeData.decode(bytes));});}
  return Promise.resolve().then(next);
 }
 root.ThemeReceiver={start:start,status:status,read:read,stop:stop};
}(this));

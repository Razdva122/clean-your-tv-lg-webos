'use strict';
var fs=require('fs'),path=require('path'),os=require('os'),crypto=require('crypto'),http=require('http');
function error(message){return new Error('Wallpaper cache '+message);}
exports.create=function(options){
 options=options||{};var sessions={},ttl=options.ttlMs||90000,base=options.directory||path.join(os.tmpdir(),'cytv-wallpaper-'+crypto.createHash('sha256').update(options.appId||'home').digest('hex').slice(0,16));
 function remove(s){if(!s||s.dead)return;s.dead=true;clearTimeout(s.timer);delete sessions[s.id];if(s.server)try{s.server.close();}catch(_){}s.sockets.forEach(function(socket){socket.destroy();});Object.keys(s.files).forEach(function(q){try{fs.unlinkSync(path.join(s.dir,q+'.mp4'));}catch(_){}});try{fs.rmdirSync(s.dir);}catch(_){}if(s.release)try{s.release();}catch(_){}}
 function touch(s){try{var now=new Date();fs.utimesSync(s.dir,now,now);}catch(_){}clearTimeout(s.timer);s.expires=Date.now()+ttl;s.timer=setTimeout(function(){remove(s);},ttl);}
 function current(p){var s=p&&sessions[p.sessionId];if(!s||s.dead)throw error('unavailable');if(Date.now()>=s.expires){remove(s);throw error('expired');}return s;}
 function start(p){return Promise.resolve().then(function(){
  if(Object.keys(sessions).length>=2)throw error('busy');if(!p||!Array.isArray(p.variants)||!p.variants.length||p.variants.length>2)throw error('invalid variants');
  var files={},total=0;p.variants.forEach(function(v){if(!v||['4k','1080p'].indexOf(v.quality)<0||files[v.quality]||typeof v.size!=='number'||v.size%1||v.size<1||v.size>(v.quality==='4k'?12582912:4194304)||typeof v.sha256!=='string'||! /^[a-f0-9]{64}$/.test(v.sha256))throw error('invalid variant');files[v.quality]={size:v.size,sha256:v.sha256,offset:0};total+=v.size;});if(total>16777216)throw error('too large');
  var ownSize=total;Object.keys(sessions).forEach(function(id){total+=sessions[id].size;});if(total>33554432)throw error('busy');
  try{fs.mkdirSync(base,448);}catch(e){if(e.code!=='EEXIST')throw e;}var stat=fs.lstatSync(base);if(!stat.isDirectory()||stat.isSymbolicLink()||(stat.mode&63)||typeof process.getuid==='function'&&stat.uid!==process.getuid())throw error('unsafe directory');
  // Recover bounded private leftovers after an interrupted service process.
  fs.readdirSync(base).forEach(function(id){if(!/^[a-f0-9]{48}$/.test(id)||sessions[id])return;var dir=path.join(base,id),entry=fs.lstatSync(dir);if(!entry.isDirectory()||entry.isSymbolicLink())throw error('unsafe directory');var stale=Date.now()-entry.mtime.getTime()>=ttl;['4k','1080p'].forEach(function(q){var name=path.join(dir,q+'.mp4'),file;try{file=fs.lstatSync(name);}catch(e){if(e.code==='ENOENT')return;throw e;}if(!file.isFile()||file.isSymbolicLink())throw error('unsafe file');if(stale)fs.unlinkSync(name);else total+=file.size;});if(stale)try{fs.rmdirSync(dir);}catch(_){} });if(total>33554432)throw error('busy');

  var id=crypto.randomBytes(24).toString('hex'),s={id:id,files:files,size:ownSize,dir:path.join(base,id),sockets:[],dead:false,server:null,release:null};
  fs.mkdirSync(s.dir,448);try{Object.keys(files).forEach(function(q){var fd=fs.openSync(path.join(s.dir,q+'.mp4'),'wx',384);fs.closeSync(fd);});if(typeof options.hold==='function')s.release=options.hold();sessions[id]=s;touch(s);return {sessionId:id};}catch(e){remove(s);throw e;}
 });}
 function write(p){var s=current(p),f=s.files[p.quality];if(s.server||!f||p.offset!==f.offset||typeof p.data!=='string'||!p.data.length||p.data.length>65536||! /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(p.data))throw error('invalid chunk');var bytes=Buffer.from(p.data,'base64');if(!bytes.length||bytes.length>49152||bytes.length>f.size-f.offset)throw error('invalid chunk');fs.appendFileSync(path.join(s.dir,p.quality+'.mp4'),bytes);f.offset+=bytes.length;touch(s);return {nextOffset:f.offset};}
 function commit(p){return Promise.resolve().then(function(){var s=current(p);if(s.server)throw error('already committed');try{Object.keys(s.files).forEach(function(q){var f=s.files[q];if(f.offset!==f.size||crypto.createHash('sha256').update(fs.readFileSync(path.join(s.dir,q+'.mp4'))).digest('hex')!==f.sha256)throw error('hash mismatch');});}catch(e){remove(s);throw e;}
  return new Promise(function(resolve,reject){var token=crypto.randomBytes(16).toString('hex');s.server=http.createServer(function(req,res){
   function end(code){res.writeHead(code,{'Connection':'close','Cache-Control':'no-store'});res.end();}
   if(s.dead||req.socket.remoteAddress!=='127.0.0.1'||req.headers.origin&&req.headers.origin!=='null'||['GET','HEAD'].indexOf(req.method)<0)return end(403);
   var quality=Object.keys(s.files).filter(function(q){return req.url==='/'+token+'/'+q+'.mp4';})[0];if(!quality)return end(404);
   var f=s.files[quality],start=0,last=f.size-1,range=req.headers.range,status=200;
   if(range){var match=/^bytes=(\d*)-(\d*)$/.exec(range);if(!match||!match[1]&&!match[2])return end(416);if(!match[1]){var suffix=+match[2];if(!suffix||!isFinite(suffix))return end(416);start=Math.max(0,f.size-suffix);}else{start=+match[1];if(match[2])last=Math.min(last,+match[2]);}if(!isFinite(start)||!isFinite(last)||start>last||start>=f.size)return end(416);status=206;}
   var headers={'Content-Type':'video/mp4','Content-Length':last-start+1,'Accept-Ranges':'bytes','Cache-Control':'no-store','Connection':'close','Access-Control-Allow-Origin':'null'};if(status===206)headers['Content-Range']='bytes '+start+'-'+last+'/'+f.size;res.writeHead(status,headers);if(req.method==='HEAD'){res.end();return;}var stream=fs.createReadStream(path.join(s.dir,quality+'.mp4'),{start:start,end:last});stream.on('error',function(){res.destroy();});res.on('close',function(){stream.destroy();});stream.pipe(res);
  });s.server.on('connection',function(socket){s.sockets.push(socket);socket.setTimeout(15000,function(){socket.destroy();});socket.on('close',function(){var i=s.sockets.indexOf(socket);if(i>=0)s.sockets.splice(i,1);});});s.server.on('error',function(e){remove(s);reject(e);});s.server.listen(0,'127.0.0.1',function(){if(s.dead){s.server.close();reject(error('expired'));return;}var handles={};Object.keys(s.files).forEach(function(q){handles[q]='http://127.0.0.1:'+s.server.address().port+'/'+token+'/'+q+'.mp4';});touch(s);resolve({handles:handles});});
  });
 });}
 return {start:start,write:write,commit:commit,keepAlive:function(p){var s=current(p);touch(s);return {};},stop:function(p){remove(sessions[p&&p.sessionId]);return {};}};
};

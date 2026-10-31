// Model webOS identities over real temporary files: no privileged chown needed.
const a=require('node:assert/strict'),fs=require('fs'),os=require('os'),path=require('path'),vm=require('vm');
const source=fs.readFileSync(require.resolve('../app/state-permissions'),'utf8');
function fixture(options={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'cytv-owners-')),state=path.join(root,'state'),key=path.join(state,'ssap-key.json');
 fs.mkdirSync(state,0o775);fs.chmodSync(state,options.directoryMode||0o775);
 fs.writeFileSync(key,options.content||'{"key":"test-private-key"}');fs.chmodSync(key,options.keyMode||0o775);
 fs.writeFileSync(path.join(state,'apps.json'),'["test.app"]');fs.chmodSync(path.join(state,'apps.json'),0o775);
 const owners=new Map([[state,{uid:options.directoryOwner||5999,gid:5000}],[key,{uid:5580,gid:options.keyGroup||5000}],[path.join(state,'apps.json'),{uid:5580,gid:5000}]]),fds=new Map();
 let actor=5367;const primaryGroup=options.primaryGroup||5000;
 const denied=()=>Object.assign(Error('denied'),{code:'EPERM'});
 function stat(p,s){return Object.assign(Object.create(s),owners.get(p)||{uid:actor,gid:primaryGroup});}
 const io=Object.assign({},fs,{
  openSync(p,...args){const fd=fs.openSync(p,...args);fds.set(fd,p);return fd;},
  closeSync(fd){fds.delete(fd);return fs.closeSync(fd);},
  fstatSync(fd){return stat(fds.get(fd),fs.fstatSync(fd));},
  lstatSync(p){return stat(p,fs.lstatSync(p));},
  fchmodSync(fd,mode){if(io.fstatSync(fd).uid!==actor)throw denied();fs.fchmodSync(fd,mode);},
  fchownSync(fd,uid,gid){if(io.fstatSync(fd).uid!==actor||gid!==5000)throw denied();owners.set(fds.get(fd),{uid,gid});},
  writeSync(...args){if(options.writeFailure)throw denied();return fs.writeSync(...args);},
  readSync(fd,buffer,offset,length,position){
   if(options.readFailure)throw denied();
   if(options.shortRead)return 0;
   return fs.readSync(fd,buffer,offset,options.partialRead?Math.min(length,3):length,position);
  },
  fsyncSync(fd){
   fs.fsyncSync(fd);
   if(options.concurrentUpdate){const tmp=key+'.new';fs.writeFileSync(tmp,'{"key":"newer-key"}');fs.renameSync(tmp,key);}
  },
  renameSync(from,to){
   if(options.renameFailure)throw Object.assign(denied(),{code:options.renameCode||'EPERM'});
   fs.renameSync(from,to);owners.set(to,owners.get(from)||{uid:actor,gid:primaryGroup});owners.delete(from);
  }
 });
 const sandbox={module:{exports:{}},Buffer,process:{getuid:()=>actor,getgid:()=>primaryGroup,getgroups:()=>[5000,primaryGroup]},require:n=>n==='fs'?io:require(n)};
 vm.runInNewContext(source,sandbox);const logs=[];
 return {state,key,owners,logs,run(uid=5367,initializeControl=false){actor=uid;return sandbox.module.exports(state,x=>logs.push(x),initializeControl);},close(){fs.rmSync(root,{recursive:true,force:true});}};
}
function test(name,options,check){const f=fixture(options);try{check(f);console.log('PASS: '+name);}finally{f.close();}}
test('foreign 0775 directory with protected developer-owned key remains usable',{keyMode:0o640},f=>{
 a.equal(f.run(),true);a.equal(fs.statSync(f.state).mode&0o777,0o775);a.equal(f.owners.get(f.key).uid,5580);
});
test('foreign boot-expanded key is replaced and readable by the service group',{},f=>{
 const before=fs.statSync(f.key).ino;a.equal(f.run(),true);a.notEqual(fs.statSync(f.key).ino,before);
 a.equal(fs.statSync(f.key).mode&0o777,0o640);a.equal(fs.readFileSync(f.key,'utf8'),'{"key":"test-private-key"}');
 a.deepEqual(f.owners.get(f.key),{uid:5367,gid:5000});a.equal(f.run(5380),true);
 a.equal(fs.readFileSync(path.join(f.state,'apps.json'),'utf8'),'["test.app"]');
 a.equal(fs.readdirSync(f.state).length,2);a.equal(JSON.stringify(f.logs).includes('test-private-key'),false);
});
test('replacement keeps the shared supplementary group instead of the helper primary group',{primaryGroup:5367},f=>{
 a.equal(f.run(),true);a.deepEqual(f.owners.get(f.key),{uid:5367,gid:5000});a.equal(f.run(5380),true);
});
test('partial descriptor reads preserve the complete pairing key',{partialRead:true},f=>{
 a.equal(f.run(),true);a.equal(fs.readFileSync(f.key,'utf8'),'{"key":"test-private-key"}');
});
for(const failure of ['renameFailure','writeFailure','readFailure','shortRead'])test(failure+' preserves original key and removes staging files',{[failure]:true},f=>{
 const before=fs.statSync(f.key).ino;a.equal(f.run(),false);a.equal(fs.statSync(f.key).ino,before);
 a.equal(fs.readFileSync(f.key,'utf8'),'{"key":"test-private-key"}');a.equal(fs.readdirSync(f.state).length,2);
});
test('an observed concurrent pairing update survives failed replacement',{concurrentUpdate:true},f=>{
 a.equal(f.run(),false);a.equal(fs.readFileSync(f.key,'utf8'),'{"key":"newer-key"}');a.equal(fs.readdirSync(f.state).length,2);
});
test('missing staging directory is a failure, not missing pairing',{renameFailure:true,renameCode:'ENOENT'},f=>a.equal(f.run(),false));
test('world-writable foreign directory is rejected',{directoryMode:0o777},f=>a.equal(f.run(),false));
test('untrusted directory owner is rejected',{directoryOwner:6000},f=>a.equal(f.run(),false));
test('replacement cannot silently change the shared group',{keyGroup:6000},f=>a.equal(f.run(),false));
test('invalid key is never copied into a trusted replacement',{content:'invalid'},f=>a.equal(f.run(),false));
test('recovered key enables foreground and power subscriptions with existing Back policy',{},f=>{
 const {EventEmitter}=require('events'),policy=require('../app/screen-policy')(['test.app']);
 let socket,returns=0,power=0,now=0;
 class WS extends EventEmitter{
  constructor(){super();socket=this;this.sent=[];}
  send(raw){this.sent.push(JSON.parse(raw));}
  terminate(){}
 }
 const context={module:{exports:{}},require(n){
  if(n==='./state-permissions')return()=>f.run();
  if(n==='os')return{networkInterfaces:()=>({lan:[{internal:false,family:'IPv4',address:'192.0.2.1'}]})};
  if(n==='./websocket')return WS;
  return require(n);
 },setTimeout(){return 1;},clearTimeout(){},setInterval(){return 2;},clearInterval(){}};
 vm.runInNewContext(fs.readFileSync(require.resolve('../app/screen-watch'),'utf8'),context);
 const watch=context.module.exports(f.state,()=>{},id=>{if(policy.next(id,now))returns++;},()=>policy.reset(),()=>power++);
 a.ok(socket,'SSAP must start after repairing the actual state files');
 socket.emit('open');a.equal(socket.sent[0].payload['client-key'],'test-private-key');
 socket.emit('message',JSON.stringify({type:'registered'}));
 a.deepEqual(socket.sent.slice(1).map(m=>m.id),['foreground','power']);
 function foreground(id,time){now=time;socket.emit('message',JSON.stringify({id:'foreground',payload:{appId:id}}));}
 foreground('test.app',0);foreground('com.webos.app.home',100);a.equal(returns,1);
 foreground('test.app',200);policy.back(true,300);policy.back(false,1400);foreground('com.webos.app.home',1500);a.equal(returns,1);
 socket.emit('message',JSON.stringify({id:'power',payload:{state:'Active'}}));a.equal(power,1);
 watch.close();
});

for(const mode of [0o640,0o660])test('startup replaces foreign control without losing pairing at '+mode.toString(8),{keyMode:0o640,primaryGroup:6575},f=>{
 const control=path.join(f.state,'control.json');fs.writeFileSync(control,'{"cmd":"stop"}');fs.chmodSync(control,mode);
 f.owners.set(control,{uid:5999,gid:5000});const original=fs.statSync(control).ino;
 a.equal(f.run(6575,true),true);a.notEqual(fs.statSync(control).ino,original);
 a.equal(fs.readFileSync(control,'utf8'),'{}');a.equal(fs.statSync(control).mode&0o777,0o660);
 a.deepEqual(f.owners.get(control),{uid:6575,gid:5000});
 a.equal(fs.readFileSync(f.key,'utf8'),'{"key":"test-private-key"}');a.equal(f.owners.get(f.key).uid,5580);
 a.equal(fs.readdirSync(f.state).length,3);
});
test('ordinary permission checks preserve pending control commands',{keyMode:0o640},f=>{
 const control=path.join(f.state,'control.json');fs.writeFileSync(control,'{"cmd":"stop"}');
 a.equal(f.run(),true);a.equal(fs.readFileSync(control,'utf8'),'{"cmd":"stop"}');
});
test('failed control replacement preserves existing command and pairing',{keyMode:0o640,renameFailure:true},f=>{
 const control=path.join(f.state,'control.json');fs.writeFileSync(control,'{"cmd":"stop"}');
 a.equal(f.run(6575,true),false);a.equal(fs.readFileSync(control,'utf8'),'{"cmd":"stop"}');
 a.equal(fs.readFileSync(f.key,'utf8'),'{"key":"test-private-key"}');a.equal(fs.readdirSync(f.state).length,3);
});

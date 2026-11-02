// Real kernel ownership/permission enforcement, run with sudo on Linux CI.
const a=require('node:assert/strict'),fs=require('fs'),os=require('os'),path=require('path'),cp=require('child_process');
if(process.platform!=='linux'||process.getuid()!==0){
 console.log('SKIP: real multi-UID permissions require Linux root (covered by CI)');
}else{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'cytv-uids-')),state=path.join(root,'state'),key=path.join(state,'ssap-key.json');
 const modulePath=require.resolve('../app/state-permissions');
 // Copy the runtime to a traversable temporary directory, independent of checkout permissions.
 fs.copyFileSync(modulePath,path.join(root,'state-permissions.js'));fs.chmodSync(root,0o755);
 function run(uid,script,primary=5000){
  const result=cp.spawnSync(process.execPath,['-e',
   'process.setgroups([5000]);process.setgid('+primary+');process.setuid('+uid+');'+script],{encoding:'utf8'});
  a.equal(result.status,0,result.stderr||result.stdout);
 }
 const check='if(!require('+JSON.stringify(path.join(root,'state-permissions.js'))+')('+JSON.stringify(state)+'))process.exit(1);';
 try{
  fs.mkdirSync(state);fs.chownSync(state,5999,5000);fs.chmodSync(state,0o775);
  fs.writeFileSync(key,'{"key":"test-key"}');fs.chownSync(key,5580,5000);fs.chmodSync(key,0o775);
  fs.writeFileSync(path.join(state,'apps.json'),'["test.app"]');fs.chownSync(path.join(state,'apps.json'),5580,5000);fs.chmodSync(path.join(state,'apps.json'),0o775);
  run(5367,check);
  a.equal(fs.statSync(key).uid,5367);a.equal(fs.statSync(key).gid,5000);a.equal(fs.statSync(key).mode&0o777,0o640);
  run(5380,check+'if(JSON.parse(require("fs").readFileSync('+JSON.stringify(key)+')).key!=="test-key")process.exit(2);');
  const control=path.join(state,'control.json');
  for(const mode of [0o640,0o660]){
   fs.writeFileSync(control,'{"cmd":"stop"}');fs.chownSync(control,5999,5000);fs.chmodSync(control,mode);
   run(6575,'if(!require('+JSON.stringify(path.join(root,'state-permissions.js'))+')('+JSON.stringify(state)+',null,true))process.exit(4);',6575);
   a.equal(fs.statSync(control).uid,6575);a.equal(fs.statSync(control).gid,5000);a.equal(fs.statSync(control).mode&0o777,0o660);
   a.equal(fs.readFileSync(control,'utf8'),'{}');a.equal(JSON.parse(fs.readFileSync(key)).key,'test-key');
   run(5999,'require("fs").writeFileSync('+JSON.stringify(control)+','+JSON.stringify('{"cmd":"stop"}')+');');
  }
  // Developer Mode setup can still atomically upload a new key after repair.
  run(5580,'var fs=require("fs"),p='+JSON.stringify(key)+';fs.writeFileSync(p+".new",\'{"key":"updated-key"}\',{mode:0o640});fs.renameSync(p+".new",p);');
  run(5367,check);a.equal(JSON.parse(fs.readFileSync(key)).key,'updated-key');
  fs.chmodSync(key,0o775);fs.chmodSync(state,0o755);
  run(5367,'if(require('+JSON.stringify(path.join(root,'state-permissions.js'))+')('+JSON.stringify(state)+'))process.exit(3);');
  a.equal(fs.statSync(key).mode&0o777,0o775);
  const renewal=path.join(root,'renewal-state'),channel=path.join(renewal,'home-control');
  fs.mkdirSync(renewal);fs.mkdirSync(channel);
  for(const dir of [renewal,channel]){fs.chownSync(dir,5999,5000);fs.chmodSync(dir,0o2770);}
  const request=path.join(channel,'home-request'),response=path.join(channel,'home-response');
  run(5367,'var fs=require("fs"),p='+JSON.stringify(request)+';fs.writeFileSync(p+".tmp",JSON.stringify({id:"test"}),{mode:0o660});fs.chmodSync(p+".tmp",0o660);fs.renameSync(p+".tmp",p+".json");',5367);
  a.equal(fs.statSync(request+'.json').gid,5000,'setgid overrides the service primary group');
  run(6575,'var fs=require("fs");if(JSON.parse(fs.readFileSync('+JSON.stringify(request+'.json')+')).id!=="test")process.exit(5);var p='+JSON.stringify(response)+';fs.writeFileSync(p+".tmp",JSON.stringify({id:"test",enabled:true}),{mode:0o660});fs.chmodSync(p+".tmp",0o660);fs.renameSync(p+".tmp",p+".json");',6575);
  a.equal(fs.statSync(response+'.json').gid,5000,'controller reply inherits the same group');
  run(5367,'if(!JSON.parse(require("fs").readFileSync('+JSON.stringify(response+'.json')+')).enabled)process.exit(6);',5367);
  // A rejected Helper service call uses trusted SSH stop code. The live
  // controller must still be able to execute block() under another UID.
  fs.chmodSync(state,0o770);
  const stop=cp.execFileSync('python3',['-c','from cytv.helper_stop import PROGRAM; print(PROGRAM)'],{encoding:'utf8'})
   .replaceAll('/media/developer/apps/usr/palm/applications/com.local.nativehome/state',state)
   .replaceAll('/media/developer/apps/usr/palm/applications/com.local.nativehome',root);
  run(5999,stop,5999);
  const blocked=path.join(state,'blocked');
  a.equal(fs.statSync(blocked).gid,5000,'SSH stop latch shares the controller group even with another primary gid');
  run(6575,'var fs=require("fs");if(JSON.parse(fs.readFileSync('+JSON.stringify(control)+')).cmd!=="stop")process.exit(7);fs.writeFileSync('+JSON.stringify(blocked)+',"stopped");',6575);
  a.equal(fs.readFileSync(blocked,'utf8'),'stopped','controller block() retains an orderly stop path');
  console.log('PASS: real installer/developer/helper/service UIDs, shared group, reconfiguration, denied replacement and setgid Home IPC');
 }finally{fs.rmSync(root,{recursive:true,force:true});}
}

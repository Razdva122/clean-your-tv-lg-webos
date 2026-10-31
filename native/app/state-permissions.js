'use strict';
// Keep the shared paths: the controller and inventory service have different UIDs.
module.exports=function(directory,log,initializeControl){
 var fs=require('fs'),c=fs.constants||require('constants'),directoryFd,directoryStat;
 var uid=process.getuid(),groups=process.getgroups();
 if(groups.indexOf(process.getgid())===-1)groups.push(process.getgid());
 function report(target,e,warning){
  if(log)log({event:warning?'state-permissions-warning':'state-permissions-error',target:target,reason:e.code||e.message});
 }
 function same(a,b){return a.dev===b.dev&&a.ino===b.ino;}
 function open(path,isDirectory){
  var fd=fs.openSync(path,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
  var s=fs.fstatSync(fd);
  if(isDirectory?!s.isDirectory():!s.isFile()){fs.closeSync(fd);throw Error('unsafe-type');}
  return fd;
 }
 function checkDirectory(){
  var s=fs.lstatSync(directory);
  if(!s.isDirectory()||!same(s,directoryStat))throw Error('directory-changed');
  // Packaged state is prisoner:jailer (5999:5000); own directories support tests.
  if(s.uid!==uid&&!(s.uid===5999&&s.gid===5000))throw Error('untrusted-directory-owner');
  if(groups.indexOf(s.gid)===-1)throw Error('unshared-directory-group');
  if((s.mode&0o7000)||(s.mode&0o002))throw Error('unsafe-directory-mode');
  return s;
 }
 function replaceKey(path,fd,before){
  var staged,stagedFd,created=false;
  try{
   if(before.gid!==directoryStat.gid||groups.indexOf(before.gid)===-1)throw Error('unshared-key-group');
   if(before.nlink!==1||before.size>65536)throw Error('unsafe-key');
   // Node 0.10 readFileSync accepts paths only. Read the already checked inode;
   // reopening its pathname would reintroduce a symlink/replacement race.
   var bytes=Buffer.alloc(before.size),read=0,key;
   while(read<bytes.length){var count=fs.readSync(fd,bytes,read,bytes.length-read,read);if(count<=0)throw Error('short-read');read+=count;}
   try{key=JSON.parse(bytes.toString('utf8'));}catch(ignore){throw Error('invalid-key');}
   if(!key||typeof key.key!=='string'||!key.key)throw Error('invalid-key');
   checkDirectory();
   staged=directory+'/.ssap-key-'+require('crypto').randomBytes(12).toString('hex');
   stagedFd=fs.openSync(staged,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,0o600);
   created=true;
   var offset=0;
   while(offset<bytes.length){var n=fs.writeSync(stagedFd,bytes,offset,bytes.length-offset);if(n<=0)throw Error('short-write');offset+=n;}
   if(fs.fstatSync(stagedFd).gid!==before.gid)fs.fchownSync(stagedFd,uid,before.gid);
   fs.fchmodSync(stagedFd,0o640);
   var s=fs.fstatSync(stagedFd);
   if(s.uid!==uid||s.gid!==before.gid||(s.mode&0o7777)!==0o640)throw Error('replacement-permissions');
   fs.fsyncSync(stagedFd);
   // Reject changes observed during staging; setup should run with helper stopped.
   var current=fs.lstatSync(path);
   if(!same(current,before)||current.size!==before.size||
      current.mtime.getTime()!==before.mtime.getTime()||current.ctime.getTime()!==before.ctime.getTime())throw Error('key-changed');
   checkDirectory();
   fs.renameSync(staged,path);staged=null;
   if(log)log({event:'state-permissions-replaced',target:'ssap-key.json'});
  }finally{
   if(stagedFd!==undefined)fs.closeSync(stagedFd);
   if(staged&&created)fs.unlinkSync(staged);
  }
 }
 function resetControl(){
  var staged=directory+'/.control-'+require('crypto').randomBytes(12).toString('hex'),fd,created=false;
  try{
   checkDirectory();
   fd=fs.openSync(staged,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,0o600);created=true;
   var bytes=Buffer.from('{}'),offset=0;
   while(offset<bytes.length){var n=fs.writeSync(fd,bytes,offset,bytes.length-offset);if(n<=0)throw Error('short-write');offset+=n;}
   // The SSH installer and service need the shared jailer group even when the
   // controller has a different primary group. Never chmod a foreign inode.
   if(fs.fstatSync(fd).gid!==directoryStat.gid)fs.fchownSync(fd,uid,directoryStat.gid);
   fs.fchmodSync(fd,0o660);
   var s=fs.fstatSync(fd);
   if(s.uid!==uid||s.gid!==directoryStat.gid||(s.mode&0o7777)!==0o660)throw Error('control-permissions');
   fs.fsyncSync(fd);checkDirectory();
   fs.renameSync(staged,directory+'/control.json');staged=null;
  }finally{
   if(fd!==undefined)fs.closeSync(fd);
   if(staged&&created)fs.unlinkSync(staged);
  }
 }
 function repair(name,mode,required){
  var fd,found=false,path=directory+'/'+name;
  try{
   fd=open(path,false);found=true;var before=fs.fstatSync(fd);
   if((before.mode&0o7777)!==mode){
    try{fs.fchmodSync(fd,mode);}catch(e){
     if(!required||(e.code!=='EPERM'&&e.code!=='EACCES'))throw e;
     replaceKey(path,fd,before);
     fs.closeSync(fd);fd=undefined;fd=open(path,false);
    }
   }
   var after=fs.fstatSync(fd);
   if((after.mode&0o7777)!==mode)throw Error('mode-mismatch');
   if(required&&after.gid!==directoryStat.gid)throw Error('unshared-key-group');
   return true;
  }catch(e){
   if(!found&&e.code==='ENOENT')return true; // Consumers report missing pairing separately.
   report(name,e,!required);return !required;
  }finally{if(fd!==undefined)fs.closeSync(fd);}
 }
 try{
  directoryFd=open(directory,true);directoryStat=fs.fstatSync(directoryFd);
  if((directoryStat.mode&0o7777)!==0o770){
   try{fs.fchmodSync(directoryFd,0o770);}catch(e){
    if(e.code!=='EPERM'&&e.code!=='EACCES')throw e;
    checkDirectory();report('directory',e,true);
   }
  }
  checkDirectory();
  if(initializeControl)resetControl();
  var keyOK=repair('ssap-key.json',0o640,true);
  repair('apps.json',0o644,false);
  return initializeControl?true:keyOK;
 }catch(e){report('directory',e,false);return false;}
 finally{if(directoryFd!==undefined)fs.closeSync(directoryFd);}
};

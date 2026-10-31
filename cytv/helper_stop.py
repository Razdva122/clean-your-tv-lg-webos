"""Trusted SSH stop request for firmware that rejects the Helper service call."""

# Stream installer-owned ES5 to the TV Node runtime; never execute retained app code.
# The existing blocked/control protocol preserves explicit stop across boot callbacks.
PROGRAM = r'''
(function(){
'use strict';
var fs=require('fs'),c=require('constants'),crypto=require('crypto');
var app='/media/developer/apps/usr/palm/applications/com.local.nativehome';
var dir='/media/developer/apps/usr/palm/applications/com.local.nativehome/state';
var before=fs.lstatSync(dir),groups=process.getgroups();
if(groups.indexOf(process.getgid())<0)groups.push(process.getgid());
if(!fs.lstatSync(app).isDirectory()||!before.isDirectory()||
   (before.uid!==process.getuid()&&!(before.uid===5999&&before.gid===5000))||
   groups.indexOf(before.gid)<0||(before.mode&3586))throw Error('unsafe-state');
function check(){var s=fs.lstatSync(dir);if(!s.isDirectory()||s.dev!==before.dev||s.ino!==before.ino)throw Error('state-changed');}
function existing(name){
 try{var s=fs.lstatSync(dir+'/'+name);if(!s.isFile()||s.nlink!==1)throw Error('unsafe-stop-file');return true;}
 catch(e){if(e.code==='ENOENT')return false;throw e;}
}
existing('blocked');existing('control.json');
function write(name,text,mode,preserve){
 check();if(preserve&&existing(name))return;
 var path=dir+'/.cytv-stop-'+crypto.randomBytes(12).toString('hex'),fd;
 try{
  fd=fs.openSync(path,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,mode);
  var b=typeof Buffer.from==='function'?Buffer.from(text):new Buffer(text),offset=0;
  while(offset<b.length){var n=fs.writeSync(fd,b,offset,b.length-offset);if(n<=0)throw Error('short-write');offset+=n;}
  if(fs.fstatSync(fd).gid!==before.gid)fs.fchownSync(fd,process.getuid(),before.gid);
  fs.fchmodSync(fd,mode);fs.fsyncSync(fd);check();existing(name);
  if(preserve){
   // link is exclusive: a concurrent emergency latch is never overwritten.
   try{fs.linkSync(path,dir+'/'+name);}catch(e){if(e.code!=='EEXIST')throw e;existing(name);}
  }else{fs.renameSync(path,dir+'/'+name);path=null;}
 }finally{if(fd!==undefined)fs.closeSync(fd);if(path)fs.unlinkSync(path);}
}
write('blocked','stopped',436,true);
write('control.json','{"cmd":"stop"}',420,false);
check();process.stdout.write('CYTV_HELPER_STOP_REQUESTED');
}());
'''

// Real temporary FD/content operations; namespace ownership and old-Mac flags are
// explicit HOST fixtures. No real credential, cross-UID or TV acceptance claim.
'use strict';
var assert=require('assert'),fs=require('fs'),os=require('os'),path=require('path'),crypto=require('crypto');
var modulePath=path.resolve(__dirname,'private-credential.js');
assert(fs.existsSync(modulePath),'private credential check-only module required');
var guard=require(modulePath),constants=fs.constants||require('constants'),tests=0;
function remove(p){var s;try{s=fs.lstatSync(p);}catch(e){if(e.code==='ENOENT')return;throw e;}if(s.isDirectory()&&!s.isSymbolicLink()){fs.readdirSync(p).forEach(function(n){remove(path.join(p,n));});fs.rmdirSync(p);}else fs.unlinkSync(p);}
function fixture(kind){
 var temp=path.join(os.tmpdir(),'cytv-private-reader-'+crypto.randomBytes(10).toString('hex'));
 fs.mkdirSync(temp,448);var root=temp+'/jail',directory=root+'/cytv-helper-state',file=directory+'/ssap-key.json';
 fs.mkdirSync(root,493);fs.mkdirSync(directory,448);fs.writeFileSync(file,'{"key":"SYNTHETIC_ONLY_☃"}');fs.chmodSync(file,384);
 var paths={'/':root,'/cytv-helper-state':directory,'/cytv-helper-state/ssap-key.json':file},fds={},opened=[],reads=0,switched=false;
 var uid=kind==='uid0'?0:6644,gid=5000;
 function target(p){assert(Object.prototype.hasOwnProperty.call(paths,p),'no legacy/arbitrary path: '+p);return paths[p];}
 function mapped(s,p){
  s.uid=uid;s.gid=gid;
  if(kind===p+'-owner')s.uid=9;
  if(kind===p+'-group')s.gid=9;
  return s;
 }
 if(kind==='root-type'){remove(root);fs.writeFileSync(root,'wrong-type');}
 if(kind==='root-mode')fs.chmodSync(root,511);
 if(kind==='directory-mode')fs.chmodSync(directory,504);
 if(kind==='file-mode')fs.chmodSync(file,416);
 if(kind==='special-mode')fs.chmodSync(file,384); // Selected stat field injected below.
 if(kind==='missing')fs.unlinkSync(file);
 if(kind==='oversize')fs.writeFileSync(file,new Buffer(65537));
 if(kind==='empty-file')fs.writeFileSync(file,'');
 if(kind==='invalid-json')fs.writeFileSync(file,'{"key":"DO_NOT_OUTPUT_SECRET"');
 if(kind==='empty-key')fs.writeFileSync(file,'{"key":""}');
 if(kind==='wrong-key-type')fs.writeFileSync(file,'{"key":9}');
 if(kind==='invalid-utf8')fs.writeFileSync(file,new Buffer([123,34,107,101,121,34,58,34,255,34,125]));
 if(kind==='max-size')fs.writeFileSync(file,JSON.stringify({key:new Array(65527).join('x')}));
 if(kind==='whitespace-key')fs.writeFileSync(file,JSON.stringify({key:' '}));
 if(kind==='record-string')fs.writeFileSync(file,JSON.stringify('SYNTHETIC_ONLY'));
 if(kind==='long-key')fs.writeFileSync(file,JSON.stringify({key:new Array(60001).join('x')}));
 if(kind==='file-type'){fs.unlinkSync(file);fs.mkdirSync(file,448);}
 if(kind==='file-symlink'){fs.renameSync(file,temp+'/target');fs.symlinkSync(temp+'/target',file);}
 if(kind==='hardlink')fs.linkSync(file,temp+'/linked-key');
 if(kind==='directory-symlink'){fs.renameSync(directory,root+'/original');fs.symlinkSync(root+'/original',directory);}
 if(kind==='directory-type'){remove(directory);fs.writeFileSync(directory,'wrong-type');}
 if(kind==='root-symlink'){fs.renameSync(root,temp+'/original');fs.symlinkSync(temp+'/original',root);}
 var io={constants:{O_RDONLY:0,O_NOFOLLOW:constants.O_NOFOLLOW,O_NONBLOCK:constants.O_NONBLOCK||4},
  openSync:function(p,flags){assert.equal(flags,io.constants.O_NOFOLLOW|io.constants.O_NONBLOCK);var fd=fs.openSync(target(p),flags);fds[fd]=p;opened.push(p);
   if(kind==='directory-replaced-before-read'&&p==='/cytv-helper-state/ssap-key.json'){
    fs.renameSync(directory,root+'/retired');fs.mkdirSync(directory,448);fs.writeFileSync(file,'{"key":"OTHER_SYNTHETIC"}');fs.chmodSync(file,384);
   }
   if(kind==='directory-replaced-same-file'&&p==='/cytv-helper-state/ssap-key.json'){
    fs.renameSync(directory,root+'/retired');fs.mkdirSync(directory,448);fs.renameSync(root+'/retired/ssap-key.json',file);
   }
   if(kind==='root-replaced-same-file'&&p==='/cytv-helper-state/ssap-key.json'){
    fs.renameSync(root,temp+'/retired-root');fs.mkdirSync(root,493);fs.renameSync(temp+'/retired-root/cytv-helper-state',directory);
   }
   return fd;
  },
  fstatSync:function(fd){var p=fds[fd],s=mapped(fs.fstatSync(fd),p);if(kind==='special-mode'&&p==='/cytv-helper-state/ssap-key.json')s.mode|=2048;if((kind==='fstat-error'&&p==='/')||(kind==='file-fstat-error'&&p==='/cytv-helper-state/ssap-key.json'))throw Error('DO_NOT_OUTPUT_SECRET');return s;},
  lstatSync:function(p){var s=mapped(fs.lstatSync(target(p)),p);return s;},
  readSync:function(fd,b,o,n,pos){assert.equal(fds[fd],'/cytv-helper-state/ssap-key.json');reads++;
   if(kind==='short-read')return 0;
   var got=fs.readSync(fd,b,o,kind==='partial-reads'?Math.min(n,3):n,pos);
   if(kind==='file-replaced-after-read'&&!switched){switched=true;fs.renameSync(file,temp+'/retired-key');fs.writeFileSync(file,'{"key":"SYNTHETIC_ONLY_☃"}');fs.chmodSync(file,384);}
   if(kind==='file-mode-after-read')fs.chmodSync(file,511);
   return got;
  },
  closeSync:function(fd){assert(Object.prototype.hasOwnProperty.call(fds,fd));delete fds[fd];fs.closeSync(fd);if(kind==='close-error')throw Error('DO_NOT_OUTPUT_SECRET');}
 };
 if(kind==='unsupported')delete io.constants.O_NONBLOCK;
 var read=guard._createForTests(io,{getuid:function(){return uid;},getgid:function(){return gid;}});
 return {run:read,opened:opened,reads:function(){return reads;},close:function(){assert.equal(Object.keys(fds).length,0,'no FD leaks');remove(temp);},root:root};
}
function check(kind,expected,noRead){var f=fixture(kind);try{var value=f.run();assert.equal(value.ok,expected,kind);if(expected)assert.equal(typeof value.key,'string');else{assert.equal(value.key,undefined);assert(['missing','unsafe','unavailable','invalid-key'].indexOf(value.reason)>=0,kind);assert.equal(JSON.stringify(value).indexOf('SYNTHETIC'),-1);assert.equal(JSON.stringify(value).indexOf('DO_NOT_OUTPUT_SECRET'),-1);}if(noRead)assert.equal(f.reads(),0,kind);if(kind==='uid0'||kind==='unsupported')assert.equal(f.opened.length,0,kind);tests++;return value;}finally{f.close();}}
// Import is passive: it neither consults kernel metadata nor opens a file.
var vm=require('vm'),passive={module:{exports:{}},process:{getuid:function(){throw Error('import identity I/O');}},require:function(n){assert.equal(n,'fs');return {};}};
vm.runInNewContext(fs.readFileSync(modulePath,'utf8'),passive);assert.equal(typeof passive.module.exports,'function');
assert.equal(check('normal',true).key,'SYNTHETIC_ONLY_☃');check('partial-reads',true);assert.equal(check('max-size',true).key.length,65526);assert.equal(check('whitespace-key',true).key,' ');assert.equal(check('long-key',true).key.length,60000);
['uid0','unsupported','/-owner','/-group','root-mode','root-symlink','root-type','/cytv-helper-state-owner','/cytv-helper-state-group','directory-mode','directory-type','directory-symlink','/cytv-helper-state/ssap-key.json-owner','/cytv-helper-state/ssap-key.json-group','file-mode','special-mode','file-type','file-symlink','hardlink','oversize','empty-file','missing','directory-replaced-before-read','directory-replaced-same-file','root-replaced-same-file','fstat-error','file-fstat-error'].forEach(function(k){check(k,false,true);});
['close-error','record-string','short-read','invalid-json','empty-key','wrong-key-type','invalid-utf8','file-replaced-after-read','file-mode-after-read'].forEach(function(k){check(k,false);});
console.log('PASS private credential check-only: '+tests+' cases, fixed paths, checked real FDs, typed/redacted refusal and no writes/FD leaks ('+process.version+')');

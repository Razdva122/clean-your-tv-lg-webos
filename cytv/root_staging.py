"""Fixed internal Root staging on measurable disk; retained /tmp paths stay valid."""
import hashlib
import json
import re
import shlex
import uuid

from .errors import UserError

ROOT = '/var/lib/clean-your-tv-root-staging'
KINDS = ('product', 'coordinator', 'system-updater', 'c1-root', 'root-tail')

# Node is already verified before Root staging, including the legacy runtime.
# Never chmod/adopt a foreign directory or take executable code from USB.
PROGRAM = r'''
(function(){
'use strict';
var fs=require('fs'),path=require('path'),c=require('constants');
var input=JSON.parse(process.argv[process.argv.length-1]),anchor='/var/lib';
if(process.getuid()!==0||typeof c.O_NOFOLLOW!=='number')throw Error('root-staging-capability');
function directory(name,privateLeaf){
 var s=fs.lstatSync(name);
 if(!s.isDirectory()||s.isSymbolicLink()||s.uid!==0||(s.mode&18)||
    (privateLeaf&&(s.mode&4095)!==448))throw Error('root-staging-directory');
 return s;
}
function present(name){try{fs.lstatSync(name);return true;}catch(e){if(e.code==='ENOENT')return false;throw e;}}
function sync(name){var fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW);try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
for(var parent=anchor;;parent=path.dirname(parent)){
 directory(parent,false);if(parent==='/')break;
}
if(input.root!==anchor+'/clean-your-tv-root-staging')throw Error('root-staging-path');
var exists=present(input.root);
if(exists&&directory(input.root,true).dev!==directory(anchor,false).dev)throw Error('root-staging-filesystem');
if(input.name){
 if(!/^cytv-(product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32}$/.test(input.name))throw Error('root-staging-name');
 process.umask(63);
 if(!exists){fs.mkdirSync(input.root,448);directory(input.root,true);sync(anchor);}
 fs.mkdirSync(input.root+'/'+input.name,448);
 directory(input.root+'/'+input.name,true);sync(input.root);
}
if(input.retire){
 var stage=input.root+'/'+input.retire,crypto=require('crypto'),seen=Object.create(null),dirs=[],expectedDirs=Object.create(null);
 if(!/^cytv-(product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32}$/.test(input.retire))throw Error('root-staging-name');
 directory(stage,true);
 Object.keys(input.files).forEach(function(key){for(var p=path.dirname(key);p!=='.';p=path.dirname(p))expectedDirs[p]=true;});
 var scan=function(folder,prefix){
  fs.readdirSync(folder).forEach(function(name){
   var file=folder+'/'+name,key=prefix+name,s=fs.lstatSync(file);
   if(s.isDirectory()){if(!expectedDirs[key])throw Error('root-staging-unknown-directory');directory(file,true);scan(file,key+'/');dirs.push(file);}
   else{
    if(!s.isFile()||s.isSymbolicLink()||s.uid!==0||s.nlink!==1||((s.mode&4095)!==384&&(s.mode&4095)!==448)||!Object.prototype.hasOwnProperty.call(input.files,key))throw Error('root-staging-file');
    var fd=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK),hash=crypto.createHash('sha256'),buf=new Buffer(65536),size=0;
    try{var checked=fs.fstatSync(fd);if(checked.ino!==s.ino||checked.dev!==s.dev)throw Error('root-staging-changed');
     for(var n;(n=fs.readSync(fd,buf,0,buf.length,null))>0;){size+=n;if(size>s.size)throw Error('root-staging-changed');hash.update(buf.slice(0,n));}
    }finally{fs.closeSync(fd);}
    if(size!==s.size||hash.digest('hex')!==input.files[key])throw Error('root-staging-digest');seen[key]=file;
   }
  });
 };
 scan(stage,'');
 if(Object.keys(seen).length!==Object.keys(input.files).length)throw Error('root-staging-incomplete');
 Object.keys(seen).forEach(function(key){fs.unlinkSync(seen[key]);});
 dirs.forEach(function(dir){fs.rmdirSync(dir);});fs.rmdirSync(stage);sync(input.root);
}
process.stdout.write('CYTV_ROOT_STAGE_READY');
}());
'''


def _run(remote, name=None):
    reply = remote.run(shlex.join(['env', '-u', 'NODE_OPTIONS', '-u', 'NODE_PATH',
        '/usr/bin/node', '-e', PROGRAM, json.dumps(dict(root=ROOT, name=name))]), timeout=10)
    if reply.strip() != 'CYTV_ROOT_STAGE_READY':
        raise UserError('Internal Root staging could not be verified. Installation stopped before package submission.',
                        reason_code='tv-storage-unavailable')


def inspect(remote):
    filesystem = remote.run("LC_ALL=C stat -f -c '%t' /var/lib", timeout=5).strip().lower()
    if not re.fullmatch(r'[0-9a-f]{1,16}', filesystem) or filesystem in ('858458f6', '1021994', '0'):
        raise UserError('Measurable internal disk storage is required for Root staging.',
                        reason_code='tv-storage-unavailable')
    _run(remote)


def create(remote, kind, *, required=0, clean_removal=False):
    if kind not in KINDS or type(required) is not int or required < 0:
        raise ValueError('Invalid Root staging kind')
    from . import storage
    name = 'cytv-'+kind+'-'+uuid.uuid4().hex
    ramfs = remote.__dict__.get('_cytv_root_ramfs')
    if type(ramfs) is not bool:
        ramfs = storage._tmp_is_ramfs(remote, strict=True)
    if ramfs and clean_removal:
        # Cleanup must work even when the installation fills internal storage.
        storage.ramfs_budget(remote, required, lambda _: None, clean_removal=True)
    elif ramfs:
        inspect(remote)
        storage.check(remote, {'/var/lib': required}, lambda _: None)
        _run(remote, name)
        return ROOT+'/'+name
    stage = '/tmp/'+name
    remote.run('umask 077; mkdir '+shlex.quote(stage))
    return stage


def product_path(value):
    return isinstance(value, str) and re.fullmatch(
        r'(?:/tmp|'+re.escape(ROOT)+r')/cytv-product-[a-f0-9]{32}', value) is not None


def retire(remote, stage, files):
    """Terminal proof permits only an exact, host-authenticated source inventory."""
    match = re.fullmatch(re.escape(ROOT)+r'/(cytv-(?:product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32})', stage)
    if not match:
        if re.fullmatch(r'/tmp/cytv-(?:product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32}', stage):
            return
        raise ValueError('Invalid Root staging path')
    from .package import safe_name
    payload = dict(root=ROOT, retire=match[1], files={safe_name(name): hashlib.sha256(raw).hexdigest() for name, raw in files.items()})
    reply = remote.run(shlex.join(['env', '-u', 'NODE_OPTIONS', '-u', 'NODE_PATH', '/usr/bin/node', '-e', PROGRAM, json.dumps(payload)]), timeout=30)
    if reply.strip() != 'CYTV_ROOT_STAGE_READY':
        raise UserError('Root staging retirement could not be verified. Recovery data was kept.', reason_code='pending-operation')

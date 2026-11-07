"""Stage and invoke the independently compiled lifecycle gate, before Helper exists."""
import base64
import hashlib
import gzip
import io
import json
import re
import shlex
import tarfile

from .errors import UserError

FENCE = '/media/developer/.cytv-lifecycle'
PRIVATE = '/media/developer/.cytv-installer'
SUPPORT = 'installer-support/lifecycle-gate'
HELPER_BASE = '/media/developer/apps/usr/palm'
SENDER = '/usr/bin/luna-send-pub'

ROOT_BINDING = r'''
(function(){
'use strict';
var fs=require('fs'),c=require('constants'),path=require('path'),crypto=require('crypto'),a=JSON.parse(process.argv[process.argv.length-1]);
var uid=process.getuid();
function fail(){throw Error('helper-lifecycle-binding-unverified');}
function exists(p){try{return fs.lstatSync(p);}catch(e){if(e.code==='ENOENT')return null;throw e;}}
function ancestry(p,state){var leaf=p;for(;;){var s=fs.lstatSync(p);if(!s.isDirectory()||s.isSymbolicLink()||
 (s.uid!==0&&s.uid!==uid&&!(s.uid===5999&&s.gid===5000))||((s.mode&18)&&!(s.uid===0&&(s.mode&512))&&
 !(state&&p===leaf&&[504,1528].indexOf(s.mode&4095)>=0)))fail();if(path.dirname(p)===p)break;p=path.dirname(p);}}
function marker(p){
 var s=exists(p);if(!s)return null;ancestry(path.dirname(p),true);
 if(!s.isFile()||s.nlink!==1||s.size!==32||(s.mode&4095)!==416||
    (s.uid!==0&&s.uid!==uid&&!(s.uid===5999&&s.gid===5000)))fail();
 var fd=fs.openSync(p,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK),b=new Buffer(32),opened;
 try{opened=fs.fstatSync(fd);if(opened.dev!==s.dev||opened.ino!==s.ino||fs.readSync(fd,b,0,32,0)!==32)fail();}finally{fs.closeSync(fd);}
 var text=b.toString('ascii');if(!/^[a-f0-9]{32}$/.test(text))fail();return text;
}
var app=marker(a.base+'/applications/com.local.nativehome/state/installer-generation');
var service=marker(a.base+'/services/com.local.nativehome.service/state/installer-generation');
if(app!==service)fail();
if(!app){var present=['applications/com.local.nativehome','services/com.local.nativehome.service','packages/com.local.nativehome'].some(function(p){return !!exists(a.base+'/'+p);});process.stdout.write(JSON.stringify({mode:present?'unmanaged':'absent'}));return;}
var matches=Object.keys(a.expected).length>0;
Object.keys(a.expected).forEach(function(name){
 var file=a.base+'/'+name,s=exists(file);if(!s){matches=false;return;}ancestry(path.dirname(file),false);
 if(!s.isFile()||s.nlink!==1||s.size>33554432||(s.mode&18)||(s.uid!==0&&s.uid!==uid&&!(s.uid===5999&&s.gid===5000)))fail();
 var fd=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK),b=new Buffer(65536),h=crypto.createHash('sha256'),n;
 try{var opened=fs.fstatSync(fd);if(opened.dev!==s.dev||opened.ino!==s.ino)fail();while((n=fs.readSync(fd,b,0,b.length,null))>0)h.update(b.slice(0,n));
 var after=fs.lstatSync(file);if(after.dev!==s.dev||after.ino!==s.ino||after.size!==s.size)fail();}finally{fs.closeSync(fd);}
 if(h.digest('hex')!==a.expected[name])matches=false;
});
if(!matches){process.stdout.write(JSON.stringify({mode:'unmanaged',reason:'runtime-not-verified'}));return;}
ancestry(path.dirname(a.fence));
try{fs.mkdirSync(a.fence,488);var made=fs.openSync(a.fence,c.O_RDONLY|c.O_NOFOLLOW);
 try{if(uid===0)fs.fchownSync(made,0,5000);else if(fs.fstatSync(made).gid!==process.getgid())fs.fchownSync(made,uid,process.getgid());fs.fsyncSync(made);}finally{fs.closeSync(made);}
 var parent=fs.openSync(path.dirname(a.fence),c.O_RDONLY|c.O_NOFOLLOW);try{fs.fsyncSync(parent);}finally{fs.closeSync(parent);}
}catch(e){if(e.code!=='EEXIST')throw e;}
var fence=fs.lstatSync(a.fence);if(!fence.isDirectory()||fence.isSymbolicLink()||(fence.mode&4095)!==488||
 (fence.uid!==uid&&!(uid===0&&fence.uid===5999&&fence.gid===5000)))fail();
process.stdout.write(JSON.stringify({mode:'managed',generation:app}));
}());
'''

ROOT_DRAIN = r'''
(function(){
'use strict';
var cp=require('child_process'),a=JSON.parse(process.argv[process.argv.length-1]);
var child=cp.spawn(a.sender,['-n','1','luna://com.local.nativehome.service/prepareRemoval',JSON.stringify({removal:a.removal,generation:a.generation})],{stdio:['ignore','pipe','pipe',3]});
var text='',errors=0,timer=setTimeout(function(){child.kill();},25000);
child.stdout.on('data',function(b){text+=b.toString('utf8');if(text.length>65536)child.kill();});
child.stderr.on('data',function(b){errors+=b.length;if(errors>65536)child.kill();});
child.on('error',function(){clearTimeout(timer);throw Error('helper-service-drain-unverified');});
child.on('close',function(code,signal){clearTimeout(timer);if(code!==0||signal||text.length>65536)throw Error('helper-service-drain-unverified');
 var r=JSON.parse(text.trim());if(r.returnValue!==true||r.quiescent!==true||r.removal!==a.removal||r.generation!==a.generation)throw Error('helper-service-drain-unverified');
 process.stdout.write(JSON.stringify({removal:a.removal,generation:a.generation,quiescent:true}));
});
}());
'''


def _root_command(proof, action, arguments=()):
    parts = [proof['gate_path'], FENCE, proof['removal'], action]
    if action in ('prepare-removal', 'remove'):
        parts.append(proof['generation'])
    return 'env -u NODE_OPTIONS -u NODE_PATH ' + ' '.join(shlex.quote(part) for part in parts + list(arguments))


def _root_pending(installer, pending):
    if installer.store.pending(installer.profile) != pending or not re.fullmatch('[a-f0-9]{32}', pending.get('removal_operation', '')):
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')


def _helper_closure(installer):
    from . import package
    try:
        name = package.safe_name(installer.manifest['helper'])
        raw = (installer.payload / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != installer.manifest['files'][name]:
            raise ValueError('Changed current Helper payload')
        files = package.data_files(raw)
        app = 'usr/palm/applications/com.local.nativehome/'
        service = 'usr/palm/services/com.local.nativehome.service/'
        required = {app + n for n in ('detach','relay','native.js','installer-lifecycle.js')} | {service+n for n in ('service.js','service-removal.js')}
        if not required <= files.keys():
            return {}
        return {name.removeprefix('usr/palm/'):hashlib.sha256(raw).hexdigest() for name,raw in files.items()
                if name.startswith((app,service)) and '/state/' not in name and (name.endswith(('.js','.json')) or name in {app+n for n in ('detach','relay','resume')})}
    except (KeyError, OSError, ValueError, TypeError):
        raise UserError('The original private recovery data is missing or changed. Recovery data was kept.', reason_code='pending-operation') from None


def fence_root_helper(installer, pending, gate_path):
    """Prepare persistent admission revocation and authenticate service drain.

    Root stages/hash-verifies gate_path from the current installer support asset.
    The returned proof is NOT native drain: Root must stop the controller then
    obtain remove/EX (complete_root_helper_fence or its existing locked worker).
    An unmanaged Helper requires the separately recorded cold-boot continuation.
    """
    _root_pending(installer, pending)
    if not isinstance(gate_path, str) or not gate_path.startswith('/') or '/..' in gate_path:
        raise ValueError('Invalid staged lifecycle gate')
    arguments = [ '/usr/bin/node', '-e', ROOT_BINDING, json.dumps({'base':HELPER_BASE, 'fence':FENCE, 'expected':_helper_closure(installer)}) ]
    binding = json.loads(installer.remote.run('env -u NODE_OPTIONS -u NODE_PATH ' + ' '.join(shlex.quote(p) for p in arguments)))
    if binding.get('mode') in ('unmanaged', 'absent'):
        return {'mode':binding['mode'], 'removal':pending['removal_operation'], 'native_drained':False, 'service_drained':False}
    if binding.get('mode') != 'managed' or not re.fullmatch('[a-f0-9]{32}', binding.get('generation','')):
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
    proof = dict(binding, removal=pending['removal_operation'], gate_path=gate_path, native_drained=False, service_drained=False)
    reply = json.loads(installer.remote.run(_root_command(proof, 'prepare-removal', ['/usr/bin/node', '-e', ROOT_DRAIN,
        json.dumps({'sender':SENDER, 'removal':proof['removal'], 'generation':proof['generation']})]), timeout=30))
    if reply != {'removal':proof['removal'], 'generation':proof['generation'], 'quiescent':True}:
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
    proof['service_drained'] = True
    return proof


prepare_root_helper_fence = fence_root_helper


def complete_root_helper_fence(installer, pending, proof):
    _root_pending(installer, pending)
    if proof.get('removal') != pending['removal_operation'] or not proof.get('service_drained'):
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
    installer.remote.run(_root_command(proof, 'remove', ['/bin/true']), timeout=30)
    proof['native_drained'] = True
    return proof


def finish_root_helper(installer, pending, proof, *, verified_absent=False):
    """Caller has proved final current package/private absence under Root lease."""
    _root_pending(installer, pending)
    if not verified_absent or proof.get('removal') != pending['removal_operation'] or not proof.get('native_drained') or not proof.get('service_drained'):
        raise UserError('Removal is not verified. Recovery data was kept.', reason_code='pending-operation')
    installer.remote.run(_root_command(proof, 'finish-removal'), timeout=30)


finish_root_helper_fence = finish_root_helper


def bind_artifacts(artifacts, generation):
    """Add non-secret instance identity before package admission/autostart.

    Preserve all original bytes/modes and control metadata, including Helper's
    real runtime image. No original install is replayed by this transformation.
    """
    from . import package
    if not re.fullmatch('[a-f0-9]{32}', generation):
        raise ValueError('Invalid lifecycle generation')
    targets = {'helper.ipk': ('com.local.nativehome', 'com.local.nativehome.service'),
               'launcher.ipk': ('com.gathin.tvhome', 'com.gathin.tvhome.renewal'),
               'updater.ipk': ('com.cleanyourtv.updater', 'com.cleanyourtv.updater.service')}
    result = {}
    for name, raw in artifacts.items():
        if name not in targets:
            raise ValueError('Unsupported lifecycle package')
        app, service = targets[name]
        paths = ['usr/palm/applications/' + app + '/state/installer-generation',
                 'usr/palm/services/' + service + '/state/installer-generation']
        members = package.read_ar(raw); output = io.BytesIO()
        with tarfile.open(fileobj=io.BytesIO(members['data.tar.gz']), mode='r:gz') as old:
            seen = set()
            with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as new:
                for entry in old:
                    package.safe_name(entry.name)
                    if entry.name in seen or entry.name in paths or not (entry.isfile() or entry.isdir()):
                        raise ValueError('Unsafe or already bound lifecycle package')
                    seen.add(entry.name)
                    new.addfile(entry, old.extractfile(entry) if entry.isfile() else None)
                for path in paths:
                    directory = path.rsplit('/', 1)[0]
                    if directory not in seen:
                        entry = tarfile.TarInfo(directory); entry.type = tarfile.DIRTYPE
                        entry.mode = 0o2770 if service == 'com.gathin.tvhome.renewal' and '/services/' in path else 0o770
                        entry.uid, entry.gid, entry.mtime = 5999, 5000, package.IPK_MTIME
                        new.addfile(entry)
                    entry = tarfile.TarInfo(path)
                    entry.mode, entry.uid, entry.gid, entry.size, entry.mtime = 0o640, 5999, 5000, 32, package.IPK_MTIME
                    new.addfile(entry, io.BytesIO(generation.encode('ascii')))
        compressed = io.BytesIO()
        with gzip.GzipFile(filename='', fileobj=compressed, mode='wb', mtime=0) as stream:
            stream.write(output.getvalue())
        members['data.tar.gz'] = compressed.getvalue()
        result[name] = package.ar(members)
    return result

BOOTSTRAP = r'''
(function(){
'use strict';
var fs=require('fs'),c=require('constants'),path=require('path'),crypto=require('crypto');
var a=JSON.parse(process.argv[process.argv.length-1]),uid=process.getuid(),gid=process.getgid();
function fail(){throw Error('lifecycle-bootstrap-unverified');}
function same(x,y){return x.dev===y.dev&&x.ino===y.ino;}
function sync(name){var fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW);try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function ancestors(name){for(var p=name;;p=path.dirname(p)){var s=fs.lstatSync(p);if(!s.isDirectory()||s.isSymbolicLink()||(s.uid!==uid&&s.uid!==0)||((s.mode&18)&&!(s.uid===0&&(s.mode&512))))fail();if(p===path.dirname(p))break;}}
function directory(name,mode){
 if(typeof name!=='string'||name!==path.resolve(name))fail();ancestors(path.dirname(name));
 try{fs.mkdirSync(name,mode);sync(path.dirname(name));}catch(e){if(e.code!=='EEXIST')throw e;}
 var s=fs.lstatSync(name),fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW);
 try{if(!s.isDirectory()||s.isSymbolicLink()||s.uid!==uid||(s.mode&4095)!==mode||!same(s,fs.fstatSync(fd)))fail();
  // Only a newly-owned private/shared support directory is assigned our group;
  // no application/service directory or ancestor permission is changed.
  if(s.gid!==gid){fs.fchownSync(fd,uid,gid);fs.fsyncSync(fd);s=fs.fstatSync(fd);}
 }finally{fs.closeSync(fd);}return s;
}
if(typeof a.sha256!=='string'||!/^([a-f0-9]{64})$/.test(a.sha256)||typeof a.binary!=='string')fail();
var raw=new Buffer(a.binary,'base64');if(raw.length>262144||crypto.createHash('sha256').update(raw).digest('hex')!==a.sha256)fail();
directory(a.fence,488);var owner=directory(a.private,448);process.chdir(a.private);
if(!same(owner,fs.statSync('.')))fail();
var name='gate-'+a.sha256,fd;
try{fd=fs.openSync(name,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,448);
 try{for(var offset=0;offset<raw.length;){var n=fs.writeSync(fd,raw,offset,raw.length-offset);if(n<=0)fail();offset+=n;}fs.fsyncSync(fd);}
 finally{fs.closeSync(fd);}sync('.');
}catch(e){if(e.code!=='EEXIST')throw e;}
var before=fs.lstatSync(name);fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
try{if(!before.isFile()||before.nlink!==1||before.uid!==uid||(before.mode&4095)!==448||before.size!==raw.length||!same(before,fs.fstatSync(fd)))fail();
 var read=new Buffer(raw.length),position=0;while(position<read.length){var count=fs.readSync(fd,read,position,read.length-position,position);if(count<=0)fail();position+=count;}
 if(crypto.createHash('sha256').update(read).digest('hex')!==a.sha256)fail();
}finally{fs.closeSync(fd);}
if(!same(owner,fs.lstatSync(a.private)))fail();process.stdout.write('CYTV_LIFECYCLE_READY');
}());
'''


def prepare(installer):
    path = installer.payload / SUPPORT
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if path.is_symlink() or installer.manifest['files'][SUPPORT] != digest:
            raise ValueError('changed-support')
    except (OSError, KeyError, TypeError, ValueError):
        raise UserError('The original private recovery data is missing or changed. Recovery data was kept.',
                        reason_code='pending-operation') from None
    args = {'private': PRIVATE, 'fence': FENCE, 'sha256': digest, 'binary': base64.b64encode(raw).decode()}
    command = 'env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node -e ' + shlex.quote(BOOTSTRAP) + ' ' + shlex.quote(json.dumps(args))
    if installer.remote.run(command).strip() != 'CYTV_LIFECYCLE_READY':
        raise UserError('The original private recovery data is missing or changed. Recovery data was kept.',
                        reason_code='pending-operation')
    return digest


def command(digest, generation, arguments, *, action='run', previous=None):
    if not re.fullmatch('[a-f0-9]{64}', digest) or not re.fullmatch('[a-f0-9]{32}', generation):
        raise ValueError('Invalid lifecycle binding')
    if action not in ('run', 'run-shared', 'remove', 'prepare-removal', 'revoke', 'finish-removal'):
        raise ValueError('Invalid lifecycle action')
    args = [PRIVATE + '/gate-' + digest, FENCE, generation, action]
    if action in ('remove', 'prepare-removal'):
        if not isinstance(previous, str) or not re.fullmatch('[a-f0-9]{32}', previous):
            raise ValueError('Missing original lifecycle generation')
        args.append(previous)
    return 'env -u NODE_OPTIONS -u NODE_PATH ' + ' '.join(shlex.quote(part) for part in args + list(arguments))

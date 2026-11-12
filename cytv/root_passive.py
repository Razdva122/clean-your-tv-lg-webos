"""Operation-bound passive Root reads. No retained code, staging or continuation."""
import json
import re


PROGRAM = r'''
(function () {
 'use strict';
 var fs=require('fs'),c=require('constants'),crypto=require('crypto');
 var identifier=OPERATION,base='/var/lib/clean-your-tv-installation';
 var out={schema:1},pin='4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
 function fail(status){var e=Error();e.category=status;throw e;}
 function directory(p){
  var s=fs.lstatSync(p);
  if(!s.isDirectory()||s.uid!==0||(s.mode&18))fail('unsafe');
 }
 function read(p,limit,tail,mask){
  for(var parent=p.slice(0,p.lastIndexOf('/'));parent;parent=parent.slice(0,parent.lastIndexOf('/')))directory(parent);
  directory('/');
  var fd=fs.openSync(p,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
  try{
   var s=fs.fstatSync(fd);
   if(!s.isFile()||s.uid!==0||s.nlink!==1||(s.mode&(mask===undefined?63:mask))||s.size>limit)fail('unsafe');
   // Every allocated byte is read before parsing or hashing, including on legacy Node.
   var size=tail?Math.min(tail,s.size):s.size,b=new Buffer(size),offset=0;
   while(offset<size){
    var n=fs.readSync(fd,b,offset,size-offset,s.size-size+offset);
    if(n<=0)fail('unsafe');offset+=n;
   }
   var after=fs.fstatSync(fd),current=fs.lstatSync(p);
   if(!current.isFile()||current.dev!==s.dev||current.ino!==s.ino||current.nlink!==s.nlink||
      current.uid!==s.uid||current.mode!==s.mode||current.size!==s.size||
      after.size!==s.size||after.mode!==s.mode||after.nlink!==s.nlink||
      after.mtime.getTime()!==s.mtime.getTime()||after.ctime.getTime()!==s.ctime.getTime())fail('unsafe');
   return {bytes:b,mode:s.mode,start:s.size-size};
  }finally{fs.closeSync(fd);}
 }
 function optional(p,limit,mask){try{return read(p,limit,0,mask);}catch(e){if(e.code==='ENOENT')return null;throw e;}}
 function parse(raw){try{return JSON.parse(raw.bytes.toString('utf8'));}catch(_){fail('unsafe');}}
 function sha(raw){return crypto.createHash('sha256').update(raw).digest('hex');}
 function digest(s){return typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);}
 function pythonState(state){
  var runtime='/var/lib/clean-your-tv-python/'+pin;
  var launcher=optional(state+'/python-launcher',4096,18),receipt=optional(state+'/python-runtime.json',65536);
  if(!launcher&&!receipt)return null;
  if(!launcher||!receipt)fail('inconsistent');
  var binding=parse(receipt),executable=runtime+'/bin/python3.13';
  if(Object.keys(binding).sort().join(',')!=='archive_sha256,executable,inventory_sha256,schema'||
     binding.schema!==1||binding.archive_sha256!==pin||binding.executable!==executable||!digest(binding.inventory_sha256))fail('inconsistent');
  var expected='#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+executable+' "$@"\n';
  if((launcher.mode&511)!==448||launcher.bytes.toString('utf8')!==expected)fail('inconsistent');
  var inventoryRaw=read(runtime+'/.cytv-runtime.json',4*1024*1024,0,18),inventory=parse(inventoryRaw);
  if(sha(inventoryRaw.bytes)!==binding.inventory_sha256||inventory.schema!==1||inventory.archive_sha256!==pin||
     !inventory.files||!digest(inventory.files['bin/python3.13']))fail('inconsistent');
  var binary=read(executable,256*1024*1024,0,18);
  if(!(binary.mode&73)||sha(binary.bytes)!==inventory.files['bin/python3.13'])fail('inconsistent');
  return 'private-bytes-match-unexecuted';
 }
 function python(){
  var states=STATES;
  for(var i=0;i<states.length;i++){
   var selected=pythonState(states[i]);if(selected)return selected;
  }
  return 'system-default-unverified';
 }
 function nativeRequest(requestPath, requestRaw, request){
  var leasePath=base+'/operation.json',leaseRaw=read(leasePath,65536),lease=parse(leaseRaw);
  if(request.operation!==identifier||request.action!=='install'||(typeof request.lease!=='string'||!/^[a-f0-9]{32}$/.test(request.lease))||
     lease.schema!==1||lease.id!==request.lease||lease.owner!=='product'||
     lease.journal!=='product-'+identifier+'.json'||lease.stage!==request.stage||lease.terminal!==false)fail('inconsistent');
  if(request.state!=='recovery_required'||request.stage!=='root-deploy'||request.home_changed!==false)fail('unavailable');
  var failure=request.failure||{},detail={};
  var kinds=['CalledProcessError','TimeoutExpired','ValueError','RuntimeError','OSError','PermissionError',
             'FileNotFoundError','TypeError','KeyError','TimeoutError'];
  if(kinds.indexOf(failure.exception_type)!==-1)detail.exception_type=failure.exception_type;
  function integer(value,min,max){return typeof value==='number'&&value%1===0&&value>=min&&value<=max;}
  if(integer(failure.exit_status,-255,255))detail.exit_status=failure.exit_status;
  if(integer(failure.errno,0,4095))detail.errno=failure.errno;
  var child=failure.root_driver;
  if(child&&kinds.concat(['FileExistsError','unknown']).indexOf(child.exception_type)!==-1&&
     Array.isArray(child.frames)&&child.frames.length<=8){
   var files=['deploy.py','installation.py','c1_gate.py','c1_keyfilter.py','package_data.py','python_binding.py',
              'observed_install.py','provision.py','store.py','transport.py','emergency_reader.py'];
   detail.root_driver={exception_type:child.exception_type,frames:child.frames.filter(function(f){
    return f&&files.indexOf(f.file)!==-1&&integer(f.line,1,10000);
   }).map(function(f){return {file:f.file,line:f.line};})};
   if(integer(child.errno,0,4095))detail.root_driver.errno=child.errno;
   if(integer(child.exit_status,-255,255))detail.root_driver.exit_status=child.exit_status;
  }
  if(!read(requestPath,65536).bytes.equals(requestRaw.bytes)||!read(leasePath,65536).bytes.equals(leaseRaw.bytes))fail('inconsistent');
  return {schema:1,status:'read',operation:'consistent-not-admission',worker:'not-applicable',stage:'root-deploy',failure:detail};
 }
 try{
  if(process.getuid()!==0)fail('unsafe');
  var requestPath=base+'/request-'+identifier+'.json',submissionPath=base+'/submission-'+identifier+'.json';
  var requestRaw=read(requestPath,65536),request=parse(requestRaw);
  if(NATIVE_REQUEST){console.log(JSON.stringify(nativeRequest(requestPath,requestRaw,request)));return;}
  var submissionRaw=read(submissionPath,1024*1024),submission=parse(submissionRaw);
  if(request.operation!==identifier||submission.operation!==identifier||request.action!=='install'||submission.action!=='install'||
     !digest(submission.candidate_sha256)||!digest(submission.worker_sha256)||
     (request.candidate_sha256!==undefined&&request.candidate_sha256!==submission.candidate_sha256))fail('inconsistent');
  if(request.stage!=='root-deploy'||request.state!=='recovery_required'||submission.stage!=='submitted')fail('unavailable');
  var worker=base+'/request-'+identifier,hashes={},updater;
  ['root','root-updater'].forEach(function(component){
   var raw=read(worker+'/'+component+'/bundle.json',1024*1024);
   hashes[component]=sha(raw.bytes);
   var manifest=parse(raw);
   if(!manifest.files||typeof manifest.files!=='object')fail('inconsistent');
   if(component==='root-updater')updater=manifest;
  });
  if(hashes['root-updater']!==submission.worker_sha256||sha(JSON.stringify(hashes))!==submission.candidate_sha256||
     !digest(updater.files['install_driver.py'])||
     sha(read(worker+'/root-updater/install_driver.py',1024*1024).bytes)!==updater.files['install_driver.py'])fail('inconsistent');
  var log=read(worker+'/worker.log',16*1024*1024,8192),text=log.bytes.toString('utf8');
  out.worker='unclassified';
  // The tail can start inside a line: classify only complete terminated lines.
  var lines=text.split('\n');if(log.start>0)lines.shift();lines.pop();
  lines.forEach(function(line){
   if(/^(?:(?:subprocess|builtins)[.])?(ValueError|RuntimeError|CalledProcessError|OSError|PermissionError|FileNotFoundError|TypeError|KeyError):/.test(line))out.worker='exception-recorded';
  });
  out.python=python();
  // Detect record replacement during the other reads; this is still no lock or
  // proof of quiescence, code execution, full inventory or cancellation safety.
  if(!read(requestPath,65536).bytes.equals(requestRaw.bytes)||!read(submissionPath,1024*1024).bytes.equals(submissionRaw.bytes))fail('inconsistent');
  out.operation='consistent-not-admission';out.status='read';
 }catch(e){out={schema:1,status:e.category|| (e.code==='ENOENT'?'missing':'unsafe')};}
 console.log(JSON.stringify(out));
}());
'''


def program(operation, pending=None):
    if not isinstance(operation,str) or not re.fullmatch('[a-f0-9]{32}',operation):
        raise ValueError('original_operation_required')
    states=['/var/lib/clean-your-tv-root','/var/lib/clean-your-tv-root-updater','/var/lib/clean-your-tv-system-updater']
    if pending is not None:
        if pending.get('action')!='install' or pending.get('product_operation')!=operation:
            raise ValueError('matching_original_host_pending_required')
        for key,base in zip(('archive','updater_archive','system_updater_archive'),states[:]):
            archived=pending.get(key)
            if archived is not None:
                if not isinstance(archived,str) or not re.fullmatch(re.escape(base)+r'\.archive-[a-f0-9]{32}',archived):
                    raise ValueError('original_archive_path_required')
                states.append(archived)
    return (PROGRAM.replace('OPERATION',json.dumps(operation)).replace('STATES',json.dumps(states))
            .replace('NATIVE_REQUEST',json.dumps(is_native_pending(pending))))


def is_native_pending(pending):
    return (bool(pending) and pending.get('action')=='install' and pending.get('stage')=='setup'
            and pending.get('home_backend')=='c1-native-gate'
            and isinstance(pending.get('product_operation'),str)
            and re.fullmatch('[a-f0-9]{32}',pending['product_operation']) is not None)


def collect(remote, operation, pending=None):
    code=program(operation,pending)
    raw=remote.run('env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node',data=code.encode(),timeout=30)
    # Fixed outputs only, even if the remote shell returns unexpected bytes.
    try:
        value=json.loads(raw)
        if value in [dict(schema=1,status=s) for s in ('missing','unsafe','inconsistent','unavailable')]:return value
        if is_native_pending(pending):
            if (isinstance(value,dict) and value.get('schema')==1 and value.get('status')=='read'
                    and value.get('operation')=='consistent-not-admission' and value.get('worker')=='not-applicable'
                    and value.get('stage')=='root-deploy'):
                from .diagnostic_context import worker_summary
                result=dict(schema=1,status='read',operation='consistent-not-admission',
                            worker='not-applicable',stage='root-deploy')
                if value.get('failure'):result['failure']=worker_summary(value['failure'])
                return result
            return dict(schema=1,status='unsafe')
        if (isinstance(value,dict) and set(value)=={'schema','status','operation','worker','python'}
                and value['schema']==1 and value['status']=='read' and value['operation']=='consistent-not-admission'
                and value['worker'] in ('unclassified','exception-recorded')
                and value['python'] in ('system-default-unverified','private-bytes-match-unexecuted')):return value
    except (TypeError,ValueError):pass
    return dict(schema=1,status='unsafe')


def inspect_saved(store, profile, operation, secret, after_observe=None):
    """Read original records, then optionally enter a separately confirmed review."""
    from .transport import SSH
    program(operation)
    with store.lock(profile):
        matches = [p for p in store.profiles() if p['edition'] == 'root'
                   and (store.pending(p) or {}).get('action') == 'install'
                   and (store.pending(p) or {}).get('product_operation') == operation]
        if len(matches) != 1 or matches[0] != profile or profile['edition'] != 'root':
            raise ValueError('original_saved_root_profile_required')
        pending = store.pending(profile)
        if not pending or pending.get('stage') != 'coordinator-submitted':
            raise ValueError('original_submitted_install_required')
        program(operation, pending)  # Validate the exact local operation before SSH.
        directory = store.device_dir(profile)
        paths = [directory / name for name in ('profile.json', 'known_hosts', 'operation.json')]
        before = [path.read_bytes() for path in paths]
        try:
            remote = SSH.connect(profile, directory, secret, lambda *_: False, persist=False)
        except Exception as error:
            error.observation_phase = 'ssh-connect'
            raise
        try:
            result = collect(remote, operation, pending)
            if store.pending(profile) != pending or [path.read_bytes() for path in paths] != before:
                raise ValueError('original_host_records_changed')
            if after_observe is not None:
                # The passive contract ends here. The shared interactive review
                # requires separate confirmation before trusted support staging.
                return after_observe(remote,result)
            return result
        finally:
            remote.close()

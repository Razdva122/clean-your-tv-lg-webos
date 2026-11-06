'use strict';
// Current verified Node 8 support; runs under the ORIGINAL Ownership flock.
// Python must never rewrite completion after this process starts retirement.
var fs=require('fs'), crypto=require('crypto'), cp=require('child_process');
var C=fs.constants, uid=process.getuid(), mode=process.argv[2], id=process.argv[3], removal=process.argv[9];
var state='/var/lib/clean-your-tv-installation';
var runtime='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
var apps=['com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.system.updater','com.cleanyourtv.updater','com.local.nativehome','com.gathin.tvhome'];
var opened=[], directory, record, lease;
function at(fd,name){return '/proc/self/fd/'+fd+(name?'/'+name:'');}
function identity(a,b){return a.dev===b.dev && a.ino===b.ino;}
function owned(info,dir){if(info.uid!==uid || (info.mode&18) || (dir?!info.isDirectory():!info.isFile() || info.nlink!==1))throw Error('unsafe-cleanup-member');}
function openDir(path){
  var fd=fs.openSync('/',C.O_RDONLY|C.O_DIRECTORY|C.O_NOFOLLOW);opened.push(fd);
  path.split('/').filter(Boolean).forEach(function(name){
    fd=fs.openSync(at(fd,name),C.O_RDONLY|C.O_DIRECTORY|C.O_NOFOLLOW);opened.push(fd);
    var info=fs.fstatSync(fd);
    if(!info.isDirectory() || (info.uid!==0 && info.uid!==uid) || ((info.mode&18) && !(info.mode&512)))throw Error('unsafe-cleanup-directory');
  });
  owned(fs.fstatSync(fd),true);return fd;
}
function read(fd,name){
  var file=fs.openSync(at(fd,name),C.O_RDONLY|C.O_NOFOLLOW|C.O_NONBLOCK);
  try {var info=fs.fstatSync(file);owned(info,false);if(info.size>4194304)throw Error('oversized-cleanup-record');return fs.readFileSync(file);}
  finally{fs.closeSync(file);}
}
function json(fd,name){return JSON.parse(read(fd,name).toString());}
function write(fd,name,value){
  var temp='.clean-tail-'+crypto.randomBytes(16).toString('hex'), file=fs.openSync(at(fd,temp),C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,384);
  try {fs.writeFileSync(file,JSON.stringify(value));fs.fsyncSync(file);}finally{fs.closeSync(file);}
  fs.renameSync(at(fd,temp),at(fd,name));fs.fsyncSync(fd);
}
function exists(path){try{fs.lstatSync(path);return true;}catch(e){if(e.code==='ENOENT')return false;throw e;}}
function inheritedLock(value,path){
  var fd=Number(value);if(!Number.isInteger(fd)||fd<3)throw Error('original-lock-required');
  var info=fs.fstatSync(fd);owned(info,false);
  if(!identity(info,fs.lstatSync(path)))throw Error('original-lock-changed');
}
function object(value){return value!==null && typeof value==='object' && !Array.isArray(value);}
function originalAbsenceSafe(app){
  var original=record.original;
  if(!object(original)||!Object.prototype.hasOwnProperty.call(original,'request')||!object(original.components))return false;
  var components=record.fenced_components===undefined?original.components:record.fenced_components;
  if(!object(components))return false;
  var keys={};keys[apps[0]]='deploy';keys[apps[1]]='root-bootstrap';keys[apps[2]]='system-bootstrap';
  var key=keys[app],journal=key?components[key]:null;
  if(key&&!Object.prototype.hasOwnProperty.call(components,key))return false;
  if(journal===undefined||journal===null){
    var request=original.request;
    if(request===undefined||request===null||!key)return true;
    var before={'deploy':['reserved','blocked'],'root-bootstrap':['reserved','blocked','root-deploy'],'system-bootstrap':['reserved','blocked','root-deploy','root-updater']};
    return object(request)&&before[key].indexOf(request.stage)!==-1;
  }
  return object(journal)&&['prepared','installing-updater','installing-supervisor'].indexOf(journal.stage===undefined?journal.phase:journal.stage)!==-1;
}
function packageReceipts(){
  if(!object(record.packages)||Object.keys(record.packages).sort().join(',')!==apps.slice().sort().join(','))throw Error('incomplete-removal-receipts');
  apps.forEach(function(app){
    var item=record.packages[app];if(!object(item))throw Error('unknown-removal-receipt');
    if(item.state==='absent-before-submission'&&originalAbsenceSafe(app))return;
    var proof=item.terminal,event=object(proof)?proof.event:null,details=object(event)?event.details:null;
    if(item.state==='terminal'&&proof.completed===true&&object(event)&&object(details)
       &&event.returnValue!==false&&!Object.prototype.hasOwnProperty.call(event,'errorCode')&&!Object.prototype.hasOwnProperty.call(details,'errorCode')
       &&(!Object.prototype.hasOwnProperty.call(event,'id')||event.id===app)&&(!Object.prototype.hasOwnProperty.call(details,'packageId')||details.packageId===app)
       &&typeof details.state==='string'&&['removed','success'].indexOf(details.state.toLowerCase())!==-1)return;
    throw Error('removal-terminal-unknown');
  });
}
function rpc(method,payload){
  var result=cp.spawnSync('/usr/bin/luna-send',['-n','1','luna://'+method,JSON.stringify(payload)],{timeout:15000,maxBuffer:2097152});
  if(result.error || result.status!==0)throw Error('cleanup-readback-unavailable');
  var value=JSON.parse(result.stdout.toString());if(value.returnValue!==true)throw Error('cleanup-readback-unavailable');return value;
}
function absent(final){
  var inventory=rpc('com.webos.applicationManager/dev/listApps',{}).apps;
  if(!Array.isArray(inventory) || inventory.some(function(a){return apps.indexOf(a.id)!==-1;}))throw Error('package-remains');
  apps.forEach(function(app){['applications/'+app,'packages/'+app,'services/'+app+(app==='com.gathin.tvhome'?'.renewal':'.service')].forEach(function(name){
    if(exists('/media/developer/apps/usr/palm/'+name))throw Error('package-remains');
  });});
  ['50-clean-your-tv-root','51-clean-your-tv-root-updater','52-clean-your-tv-system-updater'].forEach(function(name){if(exists('/var/lib/webosbrew/init.d/'+name))throw Error('startup-remains');});
  ['/var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json','/var/webos-profile/override/clean-your-tv-root.json','/media/developer/.cytv-installer'].forEach(function(path){if(exists(path))throw Error('owned-private-registration-remains');});
  if(exists('/media/developer/temp'))fs.readdirSync('/media/developer/temp').forEach(function(name){
    if(/^cytv-[a-f0-9]{32}$/.test(name)&&fs.readdirSync('/media/developer/temp/'+name).length)throw Error('no-root-private-cleanup-required');
  });
  if(final)fs.readdirSync('/tmp').forEach(function(name){
    if(/^cytv-(?:product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32}$/.test(name)){
      var fd=openDir('/tmp/'+name);if(fs.readdirSync(at(fd)).length)throw Error('support-stage-remains');
    }
  });
  var settings=rpc('com.webos.settingsservice/getSystemSettings',{category:'general',keys:['defaultApps']});
  var home=settings.settings.defaultApps.home,profiles,never=record.routing_never_applied===true && record.routes && record.routes.mode==='never-applied';
  if(typeof home!=='string'||!home||apps.indexOf(home)!==-1)throw Error('owned-route-remains');
  try{profiles=rpc('com.webos.service.systemprofile/getProfiles',{names:['defaultApps','idleApp'],subscribe:false}).profiles;}
  catch(error){if(!never)throw error;}
  if(profiles){
    var routes=[home,profiles.defaultApps.categories.home,profiles.idleApp.appId];
    if(routes.some(function(route){return typeof route!=='string'||!route||apps.indexOf(route)!==-1;}))throw Error('owned-route-remains');
    if(!never&&JSON.stringify(routes)!==JSON.stringify(record.routes))throw Error('route-changed');
  }
  if(never&&home!==record.routes.home)throw Error('route-changed');
  ['services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d','groups.d'].forEach(function(folder){
    var path='/var/luna-service2-dev/'+folder;if(!exists(path))return;
    var fd=openDir(path);
    if(fs.readdirSync(at(fd)).some(function(name){return apps.some(function(app){return name.indexOf(app+'.')===0;});}))throw Error('owned-registration-remains');
  });
  ['root','root-updater','system-updater'].forEach(function(component,index){
    var path='/var/lib/clean-your-tv-'+component;if(!exists(path))return;
    var fd=openDir(path),keep=index===0?['deploy.json','provision.lock']:['bootstrap.json','daemon.lock','worker.lock'];
    if(fs.readdirSync(at(fd)).some(function(name){return keep.indexOf(name)===-1;}))throw Error('private-member-remains');
  });
  var activities=rpc('com.palm.activitymanager/list',{details:true,subscribers:true,current:false,internal:false}).activities;
  if(!Array.isArray(activities) || activities.some(function(item){return !item || item.name==='com.cleanyourtv.root.preview.service.recovery' || String((item.callback||{}).method||'').indexOf('luna://com.cleanyourtv.')===0;}))throw Error('owned-activity-remains');
  var inputs=rpc('com.webos.service.eim/getAllInputStatus',{}).devices;
  if(!Array.isArray(inputs) || inputs.some(function(item){return item.id==='com.gathin.tvhome'||item.appId==='com.gathin.tvhome';}))throw Error('owned-input-remains');
  fs.readdirSync('/proc').filter(function(n){return /^[0-9]+$/.test(n) && Number(n)!==process.pid && !(process.argv[4]==='-' && record.runtime_cleanup.parent_pid===process.ppid && Number(n)===process.ppid);}).forEach(function(pid){
    var args;try{args=fs.readFileSync('/proc/'+pid+'/cmdline').toString().split('\0');}catch(e){if(e.code==='ENOENT')return;throw e;}
    try{args.push(fs.readlinkSync('/proc/'+pid+'/exe'));}catch(e){if(e.code!=='ENOENT')throw e;}
    var prefixes=[runtime+'/','/var/lib/clean-your-tv-root/','/var/lib/clean-your-tv-root-updater/','/var/lib/clean-your-tv-system-updater/','/tmp/clean-your-tv-root-gate/'];
    apps.forEach(function(app){prefixes.push('/media/developer/apps/usr/palm/applications/'+app+'/');prefixes.push('/media/developer/apps/usr/palm/services/'+app+(app==='com.gathin.tvhome'?'.renewal/':'.service/'));});
    (record.archives||[]).forEach(function(item){prefixes.push(item.path+'/');});
    if(args.some(function(arg){return prefixes.some(function(prefix){return arg===prefix.slice(0,-1)||arg.indexOf(prefix)===0;});}))throw Error('owned-process-still-used');
  });
}
function retire(path,inventory,pin,removeRoot){
  if(!exists(path))return;
  var root=openDir(path), info=fs.fstatSync(root), plan=[];
  if(pin && (info.dev!==pin.dev || info.ino!==pin.ino))throw Error('cleanup-root-changed');
  function scan(fd,prefix){
    fs.readdirSync(at(fd)).sort().forEach(function(name){
      var relative=prefix+name, full=at(fd,name), info=fs.lstatSync(full);owned(info,info.isDirectory());
      if(info.isDirectory()){
        if(inventory && !Object.keys(inventory).some(function(n){return n.indexOf(relative+'/')===0;}))throw Error('unknown-runtime-directory');
        if(!inventory && !prefix && ['root','root-updater'].indexOf(name)===-1)throw Error('unknown-support-directory');
        var child=fs.openSync(full,C.O_RDONLY|C.O_DIRECTORY|C.O_NOFOLLOW);opened.push(child);
        if(!identity(info,fs.fstatSync(child)))throw Error('cleanup-member-changed');
        scan(child,relative+'/');plan.push({fd:fd,name:name,info:info,dir:true});
      }else{
        if(!inventory && !prefix)throw Error('unknown-support-member');
        if(inventory){
          if(!Object.prototype.hasOwnProperty.call(inventory,relative))throw Error('unknown-runtime-member');
          var file=fs.openSync(full,C.O_RDONLY|C.O_NOFOLLOW|C.O_NONBLOCK);
          try{if(!identity(info,fs.fstatSync(file)) || crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==inventory[relative])throw Error('runtime-member-changed');}
          finally{fs.closeSync(file);}
        }
        plan.push({fd:fd,name:name,info:info,dir:false});
      }
    });
  }
  scan(root,'');
  plan.forEach(function(item){if(!identity(item.info,fs.lstatSync(at(item.fd,item.name))))throw Error('cleanup-member-changed');});
  plan.forEach(function(item){
    var path=at(item.fd,item.name);if(!identity(item.info,fs.lstatSync(path)))throw Error('cleanup-member-changed');
    (item.dir?fs.rmdirSync:fs.unlinkSync)(path);fs.fsyncSync(item.fd);
  });
  if(removeRoot){
    var slash=path.lastIndexOf('/'),parent=openDir(path.slice(0,slash)),name=path.slice(slash+1);
    if(!identity(fs.fstatSync(root),fs.lstatSync(at(parent,name))))throw Error('cleanup-root-changed');
    fs.rmdirSync(at(parent,name));fs.fsyncSync(parent);
  }
}
try{
  if(!/^[a-f0-9]{32}$/.test(id))throw Error('invalid-cleanup-selector');
  directory=openDir(state);
  try{record=json(directory,'clean-removal-'+id+'.json');}catch(e){if(e.code!=='ENOENT')throw e;}
  if(typeof removal!=='string'||!/^[a-f0-9]{32}$/.test(removal)||record && record.removal!==removal)throw Error('different-removal-intent');
  if(mode==='inspect'){
    process.stdout.write(JSON.stringify({operation:id,removal:removal,state:record && record.runtime_cleanup?'tail-ready':'not-ready'}));
  }else{
    var lock=Number(process.argv[5]);
    if(!Number.isInteger(lock) || lock<3)throw Error('original-lock-required');
    var info=fs.fstatSync(lock);owned(info,false);
    if(!identity(info,fs.lstatSync(at(directory,'ownership.lock'))))throw Error('original-lock-changed');
    if(exists('/var/lib/clean-your-tv-python'))inheritedLock(process.argv[6],'/var/lib/clean-your-tv-python/.install.lock');
    else if(Number(process.argv[6])!==-1 && Number(process.argv[6])!==4)throw Error('unexpected-promotion-lock');
    inheritedLock(process.argv[7],at(directory,'worker.lock'));
    lease=json(directory,'operation.json');
    if(!lease || Object.keys(lease).sort().join(',')!=='id,journal,owner,schema,stage,terminal' || lease.schema!==1
       || typeof lease.id!=='string' || !/^[a-f0-9]{32}$/.test(lease.id)
       || ['private-cleanup','verified-clean'].indexOf(lease.stage)===-1 || lease.terminal!==false)throw Error('unknown-ownership-receipt');
    if(!record || record.schema!==1 || record.protocol!=='clean-removal-v1' || record.operation!==id || record.lease!==lease.id
       || typeof record.removal!=='string' || !/^[a-f0-9]{32}$/.test(record.removal)
       || lease.owner!=='clean-removal' || lease.journal!=='product-'+id+'.json'
       || ['private-cleanup','verified-clean'].indexOf(record.stage)===-1
       || record.state!==(record.stage==='verified-clean'?'complete':'recovery_required')
       || !Array.isArray(record.done) || ['original-writers-fenced','controls-restored','package-removal','private-cleanup'].some(function(stage){return record.done.indexOf(stage)===-1;})
       || !record.result || record.result.removed!==true || record.result.applications_services_startup_removed!==true
       || typeof record.result.private_cleanup_verified!=='boolean')throw Error('original-removal-required');
    packageReceipts();
    var cleanup=record.runtime_cleanup;
    if(!cleanup || cleanup.root!==runtime || !cleanup.files || typeof cleanup.files!=='object' || Array.isArray(cleanup.files))throw Error('runtime-cleanup-proof-required');
    Object.keys(cleanup.files).forEach(function(name){if(!/^(?:[a-zA-Z0-9_.+-]+\/)*[a-zA-Z0-9_.+-]+$/.test(name) || name.split('/').some(function(p){return p==='.'||p==='..';}) || !/^[a-f0-9]{64}$/.test(cleanup.files[name]))throw Error('invalid-runtime-inventory');});
    if(cleanup.promotion_required===true&&!exists('/var/lib/clean-your-tv-python/.install.lock'))throw Error('original-promotion-lock-missing');
    var helper=record.helper_lifecycle,helperfd;
    if(helper){
      if(helper.service_drained!==true||helper.native_drained!==true||helper.removal!==record.removal||!/^([a-f0-9]{32})$/.test(helper.generation)||!/^([a-f0-9]{64})$/.test(process.argv[8]))throw Error('helper-drain-required');
      var helpergate=process.argv[4]==='-'?record.helper_gate_path:process.argv[4].split(',').pop()+'/gate';
      if(typeof helpergate!=='string'||!/^\/tmp\/(?:cytv-product-[a-f0-9]{32}\/root-updater\/lifecycle-gate|cytv-root-tail-[a-f0-9]{32}\/gate)$/.test(helpergate))throw Error('invalid-helper-gate');
      var parent=openDir(helpergate.slice(0,helpergate.lastIndexOf('/')));
      helperfd=fs.openSync(at(parent,helpergate.slice(helpergate.lastIndexOf('/')+1)),C.O_RDONLY|C.O_NOFOLLOW|C.O_NONBLOCK);opened.push(helperfd);
      var gateinfo=fs.fstatSync(helperfd);owned(gateinfo,false);
      if(!(gateinfo.mode&64)||crypto.createHash('sha256').update(fs.readFileSync(helperfd)).digest('hex')!==process.argv[8])throw Error('helper-gate-changed');
    }
    var gates=record.tail_stages||[];
    if(!Array.isArray(gates))throw Error('invalid-tail-stages');
    (process.argv[4]==='-'?[]:process.argv[4].split(',')).forEach(function(path){
      if(!/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(path))throw Error('invalid-tail-stage');
      if(!exists(path)||gates.some(function(entry){return entry.path===path;}))return;
      var fd=openDir(path),info=fs.fstatSync(fd);gates.push({path:path,dev:info.dev,ino:info.ino});
    });
    record.tail_stages=gates;write(directory,'clean-removal-'+id+'.json',record);
    // The parent is allowed to wait for its own child tail with the same flock.
    // Other users of this private runtime prevent retirement.
    absent(false);
    (record.support_stages||[]).forEach(function(stage){
      if(!/^\/tmp\/cytv-product-[a-f0-9]{32}$/.test(stage.path))throw Error('invalid-support-stage');
      retire(stage.path,null,stage);
    });
    retire(runtime,cleanup.files,null,true);
    gates.forEach(function(entry){
      if(!/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(entry.path))throw Error('invalid-tail-stage');
      if(!exists(entry.path))return;
      var gatefd=openDir(entry.path),info=fs.fstatSync(gatefd),names=fs.readdirSync(at(gatefd));
      if(info.dev!==entry.dev||info.ino!==entry.ino||names.some(function(name){return name!=='gate';}))throw Error('unknown-tail-stage');
      if(names.length){var executable=fs.lstatSync(at(gatefd,'gate'));owned(executable,false);fs.unlinkSync(at(gatefd,'gate'));fs.fsyncSync(gatefd);}
    });
    absent(true);
    if(helper){
      // Static current gate remains executable through this pinned inode after
      // its staged pathname is retired. No executable has to be restaged after
      // clean proof, and the persistent owner is released only at this barrier.
      var finish=cp.spawnSync('/proc/self/fd/3',['/media/developer/.cytv-lifecycle',helper.removal,'finish-removal'],
        {timeout:30000,maxBuffer:65536,stdio:['ignore','pipe','pipe',helperfd]});
      if(finish.error||finish.status!==0)throw Error('helper-fence-release-unverified');
      record.result.helper_lifecycle_released=true;
    }
    record.stage='verified-clean';record.state='complete';record.current=true;record.reason='removal-verified';
    record.result.private_cleanup_verified=true;
    cleanup.files={};delete cleanup.parent_pid;
    write(directory,'clean-removal-'+id+'.json',record);
    lease.stage='verified-clean';write(directory,'operation.json',lease);
    process.stdout.write(JSON.stringify({operation:id,removal:removal,state:'complete',stage:'verified-clean',current:true,reason:'removal-verified',result:record.result}));
  }
}catch(error){
  if(mode==='inspect' && error.code==='ENOENT')process.stdout.write(JSON.stringify({operation:id,removal:removal,state:'not-ready'}));
  else {process.stdout.write(JSON.stringify({operation:id,removal:removal,state:'recovery_required',stage:'private-cleanup',current:false,reason:'private-cleanup-incomplete'}));process.exitCode=1;}
}finally{opened.reverse().forEach(function(fd){try{fs.closeSync(fd);}catch(e){}});}

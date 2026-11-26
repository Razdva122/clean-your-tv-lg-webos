"""Read a bounded, current-controller startup observation; no startup authority."""
import json

PROGRAM = r'''
var fs=require('fs'),c=require('constants');
var root='/media/developer/apps/usr/palm/applications/com.local.nativehome',state=root+'/state';
var expected=process.argv[process.argv.length-1],out={state:'unavailable'};
function read(file,limit){
 var s=fs.lstatSync(file);if(!s.isFile()||s.isSymbolicLink()||s.nlink!==1||s.size>limit)throw Error('invalid');
 var fd=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
 try{var f=fs.fstatSync(fd);if(f.ino!==s.ino||f.dev!==s.dev||f.size!==s.size)throw Error('changed');
  var bytes=new Buffer(s.size),offset=0;
  while(offset<bytes.length){var count=fs.readSync(fd,bytes,offset,bytes.length-offset,offset);if(!count)throw Error('short');offset+=count;}
  return bytes.toString('utf8');}
 finally{fs.closeSync(fd);}
}
try{
 var pid=null;
 try{
  pid=read(state+'/controller.pid',128).trim();
  if(!/^[1-9][0-9]{0,8}$/.test(pid))throw Error('invalid pid');
 }catch(e){if(e.code!=='ENOENT')throw e;}
 var previous='';try{previous=read(state+'/controller.log.previous',524288)+'\n';}catch(e){}
 var lines=(previous+read(state+'/controller.log',524288)).split('\n'),current=false,startPid=null;
 lines.forEach(function(line){var item;try{item=JSON.parse(line);}catch(e){return;}
  if(item.event==='start'){
   startPid=String(item.pid);current=item.startupSchema===1&&/^[1-9][0-9]{0,8}$/.test(startPid)&&(!pid||pid===startPid);
   out.state=current?((!expected||item.generation===expected)?'starting':'generation-changed'):'unavailable';
   delete out.home_enabled;delete out.relay_exit_code;return;
  }
  if(!current||out.state==='generation-changed')return;
  if(item.event==='worker-start'){out.state='starting';delete out.home_enabled;delete out.relay_exit_code;}
  if(item.event==='worker'&&item.message==='INPUT_WAIT'){out.state='starting';delete out.home_enabled;}
  if(item.event==='worker'&&/^EXIT [0-9]+$/.test(item.message)){out.state='stopped';delete out.home_enabled;}
  if(item.event==='worker-ready'){
   out.state='ready';if(typeof item.homeEnabled==='boolean')out.home_enabled=item.homeEnabled;
  }
  if(item.event==='worker-exit'){
   out.state=item.code===0?'stopped':'failed';delete out.home_enabled;
   if(typeof item.code==='number'&&item.code%1===0&&item.code>=0&&item.code<=255)out.relay_exit_code=item.code;
  }
 });
 if(current&&!pid)out.controller_running=false;
 if(current&&pid===startPid){try{
  var args=fs.readFileSync('/proc/'+pid+'/cmdline','utf8').split('\0');
  out.controller_running=args[0]==='com.local.nativehome'||(/(^|\/)(node|nodejs)$/.test(args[0])&&args[1]===root+'/native.js');
 }catch(e){if(e.code==='ENOENT')out.controller_running=false;else throw e;}}
 if(out.controller_running===false&&(out.state==='ready'||out.state==='starting'))out.state='stopped';
 if(out.state==='ready'&&fs.existsSync(state+'/home-control.json')){
  var preference=JSON.parse(read(state+'/home-control.json',65536));
  if(!preference||typeof preference.enabled!=='boolean')out.state='unavailable';else out.home_enabled=preference.enabled;
 }
 if(out.state!=='failed'&&(fs.existsSync(state+'/blocked')||fs.existsSync(state+'/watchdog')))out.state='stopped';
}catch(e){out.state='unavailable';delete out.home_enabled;}
process.stdout.write(JSON.stringify(out));
'''


def summary(value):
    value = value if type(value) is dict else {}
    result = {'state': value.get('state') if value.get('state') in (
        'unavailable', 'starting', 'ready', 'failed', 'stopped', 'generation-changed') else 'unavailable'}
    for key in ('controller_running', 'home_enabled'):
        if type(value.get(key)) is bool:
            result[key] = value[key]
    code = value.get('relay_exit_code')
    if type(code) is int and 0 <= code <= 255:
        result['relay_exit_code'] = code
    return result


def observe_remote(remote, generation='', root='/media/developer/apps/usr/palm/applications/com.local.nativehome'):
    import shlex
    source = PROGRAM.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome', root)
    raw = remote.run('/usr/bin/node -e ' + shlex.quote(source) + ' ' + shlex.quote(generation or ''), timeout=5)
    return summary(json.loads(raw))


def observe(installer, generation):
    from .operations import BASE, HELPER
    return observe_remote(installer.remote, generation, BASE + '/applications/' + HELPER)

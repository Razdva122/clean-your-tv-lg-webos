"""Install only after subscribing to independent backend completion events."""
import os,json,time,select,subprocess,codecs
import shutil,stat,tempfile
from pathlib import Path
from installer_status import Completion
class OutcomeUnknown(RuntimeError):pass
STAGING_ROOT=Path('/var/lib/clean-your-tv-installer')
TRUST_ANCHOR=Path('/')

def stop(p):
 if p is None:return
 if p.poll() is None:p.terminate()
 try:p.communicate(timeout=1)
 except subprocess.TimeoutExpired:p.kill();p.communicate()

def install(app,path,disconnect_at=None,timeout=15,on_accepted=None,on_ready=None):
 # appinstalld on newer webOS cannot see /tmp. Expose only the verified IPK,
 # never the private bundle, runtime or rollback cache containing it.
 # A shared /media/developer/temp parent can allow package substitution by rename.
 # Keep the public IPK outside /tmp, beneath root-owned, non-writable ancestors.
 if STAGING_ROOT==TRUST_ANCHOR or not STAGING_ROOT.is_relative_to(TRUST_ANCHOR):raise ValueError('Unsafe installer staging path')
 for parent in STAGING_ROOT.parents:
  info=parent.lstat()
  if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode & 0o022:raise ValueError('Unsafe installer staging ancestor')
  if parent==TRUST_ANCHOR:break
 STAGING_ROOT.mkdir(mode=0o755,exist_ok=True)
 info=STAGING_ROOT.lstat()
 if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode & 0o022:raise ValueError('Unsafe installer staging directory')
 STAGING_ROOT.chmod(0o755)
 stage=Path(tempfile.mkdtemp(prefix='cytv-root-install-',dir=STAGING_ROOT))
 try:
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  with os.fdopen(fd,'rb') as source:
   info=os.fstat(source.fileno())
   if not stat.S_ISREG(info.st_mode) or not 0<info.st_size<=32*1024*1024:raise ValueError('Invalid installer package')
   raw=source.read(32*1024*1024+1)
   if len(raw)!=info.st_size:raise ValueError('Installer package changed')
  target=stage/'package.ipk'
  with target.open('xb') as output:
   output.write(raw);output.flush();os.fsync(output.fileno());os.fchmod(output.fileno(),0o644)
  stage.chmod(0o755)
 except BaseException:
  shutil.rmtree(stage)
  raise
 result=_install(app,str(target),disconnect_at,timeout,on_accepted,on_ready)
 # An unknown outcome leaves the package available to an installer still running.
 try:shutil.rmtree(stage)
 except OSError:result['staging_retained']=str(stage)
 return result

def _install(app,path,disconnect_at=None,timeout=15,on_accepted=None,on_ready=None):
 def start(uri,payload):
  return subprocess.Popen(['/usr/bin/luna-send','-i',uri,json.dumps(payload)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 monitor=start('luna://com.webos.appInstallService/status',{'subscribe':True})
 client=None;buffers={monitor.stdout:''};utf8={monitor.stdout:codecs.getincrementaldecoder('utf-8')()};decoder=json.JSONDecoder();matcher=None;cut=False;accepted=False;began=time.monotonic()
 try:
  while time.monotonic()-began<timeout:
   if monitor.poll() is not None:raise OutcomeUnknown('Independent monitor exited')
   readable,_,_=select.select(list(buffers),[],[],min(1,max(0,timeout-(time.monotonic()-began))))
   for stream in readable:
    chunk=os.read(stream.fileno(),4096)
    if not chunk:
     del buffers[stream]
     if stream is monitor.stdout:raise OutcomeUnknown('Monitor EOF')
     continue
    buffers[stream]+=utf8[stream].decode(chunk)
    if len(buffers[stream])>65536:raise OutcomeUnknown('Oversized response')
    while buffers[stream].strip():
     buffers[stream]=buffers[stream].lstrip()
     try:event,n=decoder.raw_decode(buffers[stream])
     except ValueError:break
     buffers[stream]=buffers[stream][n:]
     if stream is monitor.stdout:
      if client is None and event.get('returnValue') is True and event.get('subscribed') is True:
       apps=event.get('status',{}).get('apps')
       if apps!=[]:raise OutcomeUnknown('Installer not idle before start')
       if on_ready is not None:on_ready()
       client=start('luna://com.webos.appInstallService/dev/install',{'id':app,'ipkUrl':path,'subscribe':True})
       matcher=Completion(app,path,'com.webos.lunasend-'+str(client.pid));buffers[client.stdout]='';utf8[client.stdout]=codecs.getincrementaldecoder('utf-8')()
      elif matcher:
       details=event.get('details')
       receipt=(isinstance(details,dict) and event.get('id')==app
          and type(event.get('statusValue')) is int and event['statusValue']==37
          and event.get('returnValue') is not False and 'errorCode' not in event and 'errorCode' not in details
          and details.get('packageId')==app and details.get('ipkFile')==path
          and details.get('client')==matcher.client)
       if not accepted and receipt:
        accepted=True
        if on_accepted is not None:on_accepted(event)
       if matcher.feed(event):
        return {'completed':True,'disconnected':cut,'elapsed':round(time.monotonic()-began,3),'event':event}
     elif disconnect_at is not None and event.get('statusValue')==disconnect_at and not cut:
      client.terminate();cut=True
  raise OutcomeUnknown('No matching backend completion; do not start another install')
 finally:
  stop(client);stop(monitor)


def remove(app, timeout=120):
 """Observe the request's terminal removal reply; caller also verifies absence."""
 client=subprocess.Popen(['/usr/bin/luna-send','-i','luna://com.webos.appInstallService/dev/remove',
                          json.dumps({'id':app,'subscribe':True})],stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 began=time.monotonic();buffer='';utf8=codecs.getincrementaldecoder('utf-8')();decoder=json.JSONDecoder()
 try:
  while time.monotonic()-began<timeout:
   readable,_,_=select.select([client.stdout],[],[],min(1,max(0,timeout-(time.monotonic()-began))))
   if not readable:
    if client.poll() is not None:raise OutcomeUnknown('Removal client exited without terminal evidence')
    continue
   chunk=os.read(client.stdout.fileno(),4096)
   if not chunk:raise OutcomeUnknown('Removal EOF without terminal evidence')
   buffer+=utf8.decode(chunk)
   if len(buffer)>65536:raise OutcomeUnknown('Oversized removal response')
   while buffer.strip():
    buffer=buffer.lstrip()
    try:event,n=decoder.raw_decode(buffer)
    except ValueError:break
    buffer=buffer[n:]
    if not isinstance(event,dict):raise OutcomeUnknown('Invalid removal reply')
    details=event.get('details',{})
    if event.get('returnValue') is False or 'errorCode' in event or not isinstance(details,dict) or 'errorCode' in details:
     raise OutcomeUnknown('Removal failed; retain state')
    if event.get('id',app)!=app:continue
    state=details.get('state')
    if isinstance(state,str) and state.lower() in ('removed','success'):
     return {'completed':True,'event':event}
  raise OutcomeUnknown('No terminal removal evidence; retain state')
 finally:stop(client)

"""Independent observer supervision. Caller supplies a verified recovery callback.

No activation or TV APIs. Use a private pipe per trial. Only the observer's input
processing loop may send PING. Recovery callback must be bounded and return True
only after baseline/helper readback. An independent existing profile deadline
must remain armed in the live adapter in case this process itself fails.
"""
import math,os,select,time

def watch(fd,recover,timeout=2.0,on_ready=lambda:None,finished=lambda:False,on_ping=lambda:None,on_lg_home=lambda:None,on_device_gone=lambda at:None):
 if not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or timeout<=0:raise ValueError('Invalid timeout')
 ready=False;buffer=b'';deadline=time.monotonic()+timeout;reason=None
 while reason is None:
  if finished():return 'finished'
  remaining=deadline-time.monotonic()
  if remaining<=0:reason='heartbeat_timeout';break
  try:
   readable,_,_=select.select([fd],[],[],min(.1,remaining))
   if not readable:continue
   chunk=os.read(fd,256)
  except (OSError,ValueError):reason='channel_error';break
  if not chunk:reason='observer_exit';break
  buffer+=chunk
  while b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1)
   if line==b'READY' and not ready:
    ready=True;deadline=time.monotonic()+timeout;on_ready()
   elif line==b'PING' and ready:
    deadline=time.monotonic()+timeout;on_ping()
   elif line==b'LGHOME' and ready:on_lg_home()
   elif line==b'ESCAPE' and ready:reason='escape';break
   elif line.startswith(b'DEVICE_GONE ') and ready and len(line)<=48:
    try: at=float(line[len(b'DEVICE_GONE '):])
    except ValueError: at=-1
    if math.isfinite(at) and 0<=at<=time.monotonic():
     on_device_gone(at);reason='device_removed'
    else: reason='bad_protocol'
    break
   elif line==b'LOST':reason='input_lost';break
   else:reason='bad_protocol';break
  if reason is None and len(buffer)>16 and not (buffer.startswith(b'DEVICE_GONE ') and len(buffer)<=48):reason='bad_protocol'
 if recover(reason) is not True:raise RuntimeError('Recovery not verified: '+reason)
 return reason

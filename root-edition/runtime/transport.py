"""Bounded webOS Luna transport. No settings writes except the fixed Home pair."""
import json, os, select, subprocess, time
try:
 from .profile_plan import CANDIDATE, STOCK
except ImportError:
 from profile_plan import CANDIDATE, STOCK

def call(uri,payload,timeout=5,allow_failure=False):
 # Keep stdin open until a reply. Closing it makes this TV's luna-send exit early.
 p=subprocess.Popen(['/usr/bin/luna-send','-n','1',uri,json.dumps(payload)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  end=time.monotonic()+timeout; data=b''
  while time.monotonic()<end:
   if not select.select([p.stdout],[],[],max(0,end-time.monotonic()))[0]:break
   chunk=os.read(p.stdout.fileno(),4096)
   if not chunk:break
   data+=chunk
   if len(data)>65536:raise ValueError('Oversized reply')
   try:value=json.loads(data)
   except ValueError:continue
   if not isinstance(value,dict):raise ValueError('Invalid Luna reply')
   if value.get('returnValue') is not True and not (allow_failure and value.get('returnValue') is False):raise RuntimeError(str(value))
   return value
  raise TimeoutError(uri)
 finally:
  if p.poll() is None:p.terminate()
  try:p.communicate(timeout=min(1,timeout))
  except subprocess.TimeoutExpired:p.kill();p.communicate()

def read_defaults():
 r=call('luna://com.webos.settingsservice/getSystemSettings',{'category':'general','keys':['defaultApps']})
 d=r['settings']['defaultApps']
 if not isinstance(d,dict) or ('home' in d and (not isinstance(d['home'],str) or not d['home'])):raise ValueError('Invalid Home read')
 return d

def read():
 return read_defaults().get('home')

def write(target):
 if target not in (CANDIDATE,STOCK):raise ValueError('Invalid target')
 # Preserve a freshly read Settings map rather than relying on SAM's cached map.
 # This readback verifies stored values, not consumer-cache application.
 defaults=dict(read_defaults(),home=target)
 result=call('luna://com.webos.settingsservice/setSystemSettings',
             {'category':'general','settings':{'defaultApps':defaults}})
 if read_defaults()!=defaults:raise RuntimeError('Default apps readback mismatch')
 return result


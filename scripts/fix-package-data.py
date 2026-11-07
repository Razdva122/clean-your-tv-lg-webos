import argparse, io, pathlib, tarfile
# Rewrites the ar archive in Python: macOS BSD `ar r` turns the Debian-style ipk into a symbol-table-only archive.
def read_ar(b):
 assert b[:8]==b'!<arch>\n','not an ar archive'
 i,members=8,[]
 while i<len(b):
  h=b[i:i+60];size=int(h[48:58]);members.append([h[:16].decode().strip().rstrip('/'),h,b[i+60:i+60+size]]);i+=60+size+(size&1)
 return members
def write_ar(members):
 out=bytearray(b'!<arch>\n')
 for name,h,data in members:out+=h[:48]+str(len(data)).ljust(10).encode()+h[58:]+data+(b'\n' if len(data)&1 else b'')
 return bytes(out)
parser=argparse.ArgumentParser()
parser.add_argument('package')
parser.add_argument('--home-control',action='store_true')
args=parser.parse_args()
targets=({'usr/palm/services/com.gathin.tvhome.renewal/state':0o2770,
          'usr/palm/services/com.gathin.tvhome.renewal/state/home-control':0o2770} if args.home_control else
         {'usr/palm/applications/com.local.nativehome/state':0o770,
          'usr/palm/services/com.local.nativehome.service/state':0o770})
p=pathlib.Path(args.package).resolve()
members=read_ar(p.read_bytes());data=next(m for m in members if m[0]=='data.tar.gz')
out=io.BytesIO(); changed=[]
with tarfile.open(fileobj=io.BytesIO(data[2]),mode='r:gz') as src,tarfile.open(fileobj=out,mode='w:gz') as dst:
 for entry in src:
  name=entry.name.rstrip('/')
  if name.startswith('./'):name=name[2:]
  if name in targets:
   assert entry.isdir()
   entry.uid=5999;entry.gid=5000;entry.uname='prisoner';entry.gname='jailer';entry.mode=targets[name]
   changed.append(name)
  dst.addfile(entry,src.extractfile(entry) if entry.isfile() else None)
assert set(changed)==set(targets),changed
data[2]=out.getvalue();p.write_bytes(write_ar(members))
print('Set shared data directory ownership and modes:',changed)

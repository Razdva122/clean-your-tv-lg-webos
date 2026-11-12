"""Shared source verification for streamed rollback maintenance."""
SCRIPT = r'''
import copy, fcntl, hashlib, json, math, os, re, stat, sys, time, uuid
from pathlib import Path, PurePosixPath

def encode(value):
    return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'),sort_keys=True).encode()

def digest(raw):return hashlib.sha256(raw).hexdigest()

def read(path,limit=4*1024*1024):
    path=Path(path)
    for parent in (path.parent,*path.parent.parents):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,os.geteuid()) or (info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX):raise ValueError('Unsafe recovery directory')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or info.st_mode&0o022 or info.st_size>limit:raise ValueError('Unsafe recovery file')
        raw=stream.read(limit+1)
        if len(raw)>limit:raise ValueError('Oversized recovery file')
        return raw

def load_sources(code,files,*,standalone=False):
    import importlib.abc, importlib.util
    modules={}
    for name,sha in files.items():
        if name.endswith('.py'):
            package=name.endswith('/__init__.py');module=(name[:-12] if package else name[:-3]).replace('/','.')
            modules[module]=(name,sha,package)
    roots={n.split('.')[0] for n in modules}
    forbidden={'updater'} if 'system_updater' in roots and not standalone else set()
    if any(n in sys.modules for n in set(modules)|roots|forbidden):raise ValueError('Ambient supervisor module already loaded')
    class Sources(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden:raise ModuleNotFoundError('Unpinned legacy helper alias')
            if fullname in modules:return importlib.util.spec_from_loader(fullname,self,is_package=modules[fullname][2])
            if fullname in roots:
                spec=importlib.machinery.ModuleSpec(fullname,loader=None,is_package=True)
                spec.submodule_search_locations=[]
                return spec
            if fullname.split('.')[0] in roots:raise ImportError('Unpinned supervisor module')
        def create_module(self,spec):return None
        def exec_module(self,module):
            name,sha,package=modules[module.__name__];raw=read(code/name)
            if digest(raw)!=sha:raise ValueError('Original supervisor source changed')
            module.__file__=str(code/name)
            if package:module.__path__=[]
            exec(compile(raw,str(code/name),'exec'),module.__dict__)
    finder=Sources();sys.meta_path.insert(0,finder);return finder

'''

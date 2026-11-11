"""Host-owned JS only. Never load support code from an installed TV package."""
from pathlib import Path
import sys

SOURCES = {
    'state-permissions': 'native/app/state-permissions.js',
    'contract-events': 'native/app/contract-events.js',
    'boot-proof': 'native/contracts/boot-proof.js',
}
NAMES = tuple(SOURCES)


def trusted_source(name):
    if type(name) is not str or name not in NAMES:
        raise ValueError('Unknown trusted TV resource')
    package = Path(__file__).resolve().parent
    # A packaged runtime is recognized by its staged directory too (Android).
    if (getattr(sys, 'frozen', False) or hasattr(sys, 'getandroidapilevel')
            or sys.platform == 'android' or (package / 'tv').is_dir()):
        path = package / 'tv' / (name + '.js')
    else:
        path = package.parent / SOURCES[name]
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError('Missing trusted TV resource: ' + name)
    return path.read_text(encoding='utf-8')


def stage_sources(destination):
    """Builders copy canonical repository bytes; no installed-device fallback."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    for name in NAMES:
        source = root / SOURCES[name]
        if source.is_symlink() or not source.is_file():
            raise FileNotFoundError('Missing canonical TV resource: ' + name)
        (destination / (name + '.js')).write_bytes(source.read_bytes())


def node_adapter(name, invocation):
    """Embed a HOST-CODE-ONLY static JS body using `contract` as its export.

    Never pass remote/user text as invocation. Values travel separately via JSON
    or argv. Only fixed bundled dependencies and necessary Node builtins resolve.
    """
    if type(name) is not str or name not in NAMES or type(invocation) is not str:
        raise ValueError('Invalid trusted adapter')
    modules = []
    for resource in NAMES:
        modules.append("factories['./%s']=function(module,exports,require){\n%s\n};" % (resource, trusted_source(resource)))
    return """(function(){
var builtin=require, factories={},cache={};
%s
function load(name){
 if(name==='fs'||name==='crypto'||name==='constants'||name==='path')return builtin(name);
 if(!Object.prototype.hasOwnProperty.call(factories,name))throw Error('unsupported-resource');
 if(!cache[name]){var module={exports:{}};cache[name]=module;factories[name](module,module.exports,load);}
 return cache[name].exports;
}
try { var contract=load('./%s');
%s
} catch(ignore){var safe=[];try{safe=load('./contract-events').safeEvents(ignore.contractEvents || []);}catch(unavailable){}process.stdout.write(JSON.stringify({schema:1,error:'contract-error',events:safe}));process.exitCode=1;if(process.exit)process.exit(1);}
}());""" % ('\n'.join(modules), name, invocation)

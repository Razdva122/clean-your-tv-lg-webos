"""Explicit clean transition from an eligible ordinary No-root installation."""

import shlex

from . import package, prompts
from .errors import UserError
from .operations import require_root_reinstall_cleanup


def select_source(installer, write, ask, *, non_interactive):
    source = installer.single_tile_source()
    if not source:
        return True

    # A's built-in snapshot excludes browser media and service/pairing state.
    # The existing complete-removal path is a separate owner choice. It cannot
    # confer approval to start the new install, even after verified removal.
    write('A clean installation removes your CYTV layout, themes, personal wallpapers, preferences and TV pairing. Returning to the previous version requires uninstalling and installing that version again.')
    if non_interactive or not prompts.confirm('Remove this No-root installation to switch to one tile?', ask, write, default=False):
        return False
    installer.select_graphics()
    installer.preflight(install=True, defer_helper=True)
    if installer.single_tile_source() != source:
        raise UserError('The Clean Your TV installation changed.',
                        reason_code='pending-operation')
    result = installer.uninstall_project()
    require_root_reinstall_cleanup(result)
    installer.require_fresh_single_tile()
    return prompts.confirm('Install Clean Your TV with one tile now?', ask, write, default=False)


def installed_role(installer, *, require_tile_protocol=False):
    """Return the role of the fixed SDK package without exposing device data."""
    from .operations import BASE
    path = BASE + '/applications/' + package.TILE_APP + '/appinfo.json'
    script = r"""
var fs=require('fs'),p=require('path'),c=require('constants');
var file=process.argv[1],id=process.argv[2];
for(var parent=p.dirname(file);;parent=p.dirname(parent)){
  if(!fs.lstatSync(parent).isDirectory())throw Error('indirect directory');
  if(parent===p.dirname(parent))break;
}
var opened=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
try {
  var s=fs.fstatSync(opened);
  if(!s.isFile()||s.nlink!==1||s.size>65536)throw Error('invalid metadata');
  var bytes=new Buffer(s.size),offset=0;
  while(offset<s.size){var n=fs.readSync(opened,bytes,offset,s.size-offset,null);if(!n)throw Error('changed metadata');offset+=n;}
  var info=JSON.parse(bytes.toString('utf8')),now=fs.lstatSync(file);
  if(now.ino!==s.ino||now.dev!==s.dev||now.size!==s.size||info.id!==id||info.type!=='web')throw Error('changed entry');
  if(process.argv[3]==='tile'&&info.cytvTileProtocol!==1)throw Error('unsupported tile');
  var edition=info.cytvTileEdition;
  if(edition===undefined)process.stdout.write('homebrew');
  else if(info.cytvTileProtocol===1&&(edition==='root'||edition==='no-root'))process.stdout.write(edition);
  else throw Error('unrecognized entry');
} finally {fs.closeSync(opened);}
"""
    reply = installer.remote.run('/usr/bin/node -e ' + shlex.quote(script) + ' ' +
                                 shlex.quote(path) + ' ' + shlex.quote(package.TILE_APP) +
                                 (' tile' if require_tile_protocol else '')).strip()
    if reply not in ('root', 'no-root', 'homebrew'):
        raise UserError('The TV package result could not be verified.', reason_code='cleanup-check-failed')
    return reply

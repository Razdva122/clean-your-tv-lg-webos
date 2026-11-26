"""Explicit clean transition from an eligible ordinary No-root installation."""

import json
import shlex

from . import package, prompts
from .errors import UserError
from .operations import require_root_reinstall_cleanup


def select_source(installer, write, ask, *, non_interactive):
    source = installer.single_tile_source()
    if not source:
        return True
    if 'maintenance' in source:
        from .single_tile_maintenance import run
        if non_interactive or not prompts.confirm('Update or repair the installed tile?', ask, write, default=False):
            return False
        run(installer, source)
        write('The Clean Your TV tile is ready to open.')
        return 'maintained'

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


def read_app_file(installer, app, name):
    """Read fixed SDK metadata or just the transport marker from Home's inventory."""
    from .operations import BASE
    from .operations import HOME, HELPER
    marker = (app, name) == (HOME, 'apps.js')
    if not marker and (app not in (HOME, HELPER, package.TILE_APP) or name != 'appinfo.json'):
        raise ValueError('Unexpected application file')
    path = BASE + '/applications/' + app + '/' + name
    script = r"""
var fs=require('fs'),p=require('path'),c=require('constants');
var file=process.argv[1],marker=p.basename(file)==='apps.js',limit=marker?16*1024*1024:65536;
for(var parent=p.dirname(file);;parent=p.dirname(parent)){
  if(!fs.lstatSync(parent).isDirectory())throw Error('indirect directory');
  if(parent===p.dirname(parent))break;
}
var opened=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
try {
  var s=fs.fstatSync(opened);
  if(!s.isFile()||s.nlink!==1||s.size>limit)throw Error('invalid metadata');
  var size=marker?Math.min(128,s.size):s.size,bytes=new Buffer(size),offset=0;
  while(offset<size){var n=fs.readSync(opened,bytes,offset,size-offset,s.size-size+offset);if(!n)throw Error('changed metadata');offset+=n;}
  var now=fs.lstatSync(file);
  if(now.ino!==s.ino||now.dev!==s.dev||now.size!==s.size)throw Error('changed entry');
  if(marker){
    var match=/\nwindow\.CYTVNoRootConnection = "(developer-mode|root-ssh)";\n$/.exec(bytes.toString('utf8'));
    process.stdout.write(match?match[1]:'unknown');
  } else process.stdout.write(bytes);
} finally {fs.closeSync(opened);}
"""
    return installer.remote.run('/usr/bin/node -e ' + shlex.quote(script) + ' ' +
                                shlex.quote(path))


def app_metadata(installer, app):
    from .no_root_cleanup import _exact_developer_app
    if _exact_developer_app(installer, app):
        info = json.loads(read_app_file(installer, app, 'appinfo.json'))
        if isinstance(info, dict) and info.get('id') == app:
            return info
    raise UserError('The TV package result could not be verified.', reason_code='cleanup-check-failed')


def installed_role(installer, *, require_tile_protocol=False):
    info = app_metadata(installer, package.TILE_APP)
    if require_tile_protocol and (type(info.get('cytvTileProtocol')) is not int or info['cytvTileProtocol'] != 1):
        raise UserError('Use the installer for the installed Clean Your TV version.',
                        reason_code='unsupported-operation')
    if info.get('type') == 'web' and 'cytvTileEdition' not in info:
        return 'homebrew'
    if info.get('type') == 'web' and info.get('cytvTileProtocol') == 1 and info.get('cytvTileEdition') in ('root', 'no-root'):
        return info['cytvTileEdition']
    raise UserError('The TV package result could not be verified.', reason_code='cleanup-check-failed')

"""Copy packaged preferences from the user's existing Home into the isolated UI.

Never evaluates JavaScript or reads browser databases. This is explicit migration
from an installed trusted launcher, not an importer for arbitrary downloaded JS.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

APP='com.cleanyourtv.root.preview'

def _read(path, limit):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Indirect source')
    path = path.absolute()
    with ExitStack() as opened:
        directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        opened.callback(os.close, directory)
        for part in path.parts[1:-1]:
            if part == '..':
                raise ValueError('Indirect source')
            directory = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=directory)
            opened.callback(os.close, directory)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        stream = opened.enter_context(os.fdopen(fd, 'rb'))
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('Invalid packaged data file')
        data = stream.read(limit + 1)
        after = path.lstat()
        if (len(data) != before.st_size or before.st_dev != after.st_dev or before.st_ino != after.st_ino
                or before.st_mtime_ns != after.st_mtime_ns or before.st_ctime_ns != after.st_ctime_ns):
            raise ValueError('Source changed')
        return data


def _data_assignment(raw, name):
    import ast
    match = re.fullmatch(rb'\s*window\.' + name + rb'\s*=\s*(\{.*\})\s*;?\s*', raw, re.DOTALL)
    if not match:
        raise ValueError('Unsupported packaged preferences')
    literal = match[1].decode('utf-8')
    try:
        value = json.loads(literal)
    except json.JSONDecodeError:
        # Published launcher defaults also use unquoted property names and single-quoted strings.
        tree = ast.parse(literal, mode='eval')
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                node.keys = [ast.Constant(key.id) if isinstance(key, ast.Name) else key for key in node.keys]
        value = ast.literal_eval(tree)
    if not isinstance(value, dict):
        raise ValueError('Unsupported packaged preferences')
    return value


def prepare(source, *, data_only=False):
    source=Path(source)
    if source.is_symlink() or not source.is_dir():raise ValueError('Invalid source directory')
    apps=_read(source/'apps.js',4*1024*1024);config=_read(source/'config.js',1024*1024)
    if data_only:
        info = json.loads(_read(source/'appinfo.json', 64*1024))
        if not isinstance(info, dict) or info.get('id') != 'com.gathin.tvhome':
            raise ValueError('Unexpected Home package')
        inventory = _data_assignment(apps, b'TV_APPS')
        settings = _data_assignment(config, b'CONFIG')
        if (not isinstance(inventory.get('apps'), list) or not isinstance(inventory.get('inputs'), list)
                or type(settings.get('columns')) is not int or not 1 <= settings['columns'] <= 8):
            raise ValueError('Unsupported packaged preferences')
        apps_list, inputs = inventory['apps'], inventory['inputs']
        if (len(apps_list) > 200 or len(inputs) > 100
                or any(not isinstance(app, dict) or not isinstance(app.get('id'), str) or not app['id']
                       or not isinstance(app.get('title'), str) for app in apps_list)
                or any(not isinstance(entry, dict) for entry in inputs)):
            raise ValueError('Invalid Home inventory')
        for key in ('dockApps', 'hiddenApps'):
            selection = settings.get(key, [])
            if not isinstance(selection, list) or not all(isinstance(value, str) for value in selection):
                raise ValueError('Invalid app selection')
        settings['hiddenApps'] = list(dict.fromkeys(settings.get('hiddenApps', []) + [APP]))
        apps = ('window.TV_APPS=' + json.dumps(inventory) + ';\n').encode()
        files = {'apps.js': apps, 'config.js': ('window.CONFIG=' + json.dumps(settings) + ';\n').encode()}
    else:
        if b'window.TV_APPS' not in apps or b'window.CONFIG' not in config:
            raise ValueError('Unexpected packaged preferences')
        files={'apps.js':apps,'config.js':config+b'\nwindow.CONFIG.hiddenApps=(window.CONFIG.hiddenApps||[]).concat(["'+APP.encode()+b'"]);\n'}
    icons=set(re.findall(r'''["'](icons/[^"']+)["']''',apps.decode('utf-8')))
    if len(icons)>200:raise ValueError('Too many icons')
    for name in sorted(icons):
        p=PurePosixPath(name)
        if len(p.parts)!=2 or '..' in p.parts or '\\' in name or p.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
            raise ValueError('Invalid icon path')
        files[name]=_read(source/name,256*1024)
    if sum(map(len,files.values()))>16*1024*1024:raise ValueError('Profile too large')
    return files


def from_profile(path):
    """Import JSON data only; never execute updater code or modify its backup."""
    value=json.loads(_read(Path(path), 4*1024*1024))
    if not isinstance(value,dict) or value.get('schema')!=1:raise ValueError('Invalid profile schema')
    inventory=value.get('inventory');config=value.get('config')
    if not isinstance(inventory,dict) or not isinstance(config,dict):raise ValueError('Missing profile data')
    apps=inventory.get('apps');inputs=inventory.get('inputs')
    if not isinstance(apps,list) or not isinstance(inputs,list) or len(apps)>200 or len(inputs)>100:raise ValueError('Invalid inventory')
    for app in apps:
        if (not isinstance(app,dict) or not isinstance(app.get('id'),str) or not app['id']
                or not isinstance(app.get('title'),str) or len(app['title'])>256
                or not isinstance(app.get('icon'),str)
                or not re.fullmatch(r'data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+',app['icon'])):
            raise ValueError('Invalid application profile')
    if type(config.get('columns')) is not int or not 1<=config['columns']<=8:raise ValueError('Invalid columns')
    for key in ('dockApps','hiddenApps'):
        if not isinstance(config.get(key),list) or not all(isinstance(x,str) for x in config[key]):raise ValueError('Invalid app selection')
    config=dict(config);config['hiddenApps']=list(dict.fromkeys(config['hiddenApps']+[APP]))
    return {'apps.js':('window.TV_APPS='+json.dumps(inventory)+';\n').encode(),
            'config.js':('window.CONFIG='+json.dumps(config)+';\n').encode()}

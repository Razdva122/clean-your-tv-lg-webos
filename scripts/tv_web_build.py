"""Compile only TV web application assets; never process native/Node services."""
import argparse
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INVENTORY_PREFIX = '.cytv-launcher-inventory-'
INVENTORY_OWNER = '.cytv-source-inventory-v1'


def compile_web(files):
    from scripts.chinese_fonts import with_fonts
    files = with_fonts(files)
    web = {name: raw.decode('utf-8') for name, raw in files.items()
           if name.endswith(('.js', '.css', '.html'))}
    try:
        result = subprocess.run(['node', str(ROOT / 'scripts/compile-tv-web.cjs')],
                                input=json.dumps(web), capture_output=True, text=True, encoding='utf-8',
                                cwd=ROOT, timeout=120, check=True)
    except FileNotFoundError as error:
        raise RuntimeError('TV web compilation requires Node.js 20.19+ and npm ci.') from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError('TV web compilation failed. Run npm ci in the source checkout.\n' + error.stderr) from error
    output = dict(files)
    output.update({name: text.encode('utf-8') for name, text in json.loads(result.stdout).items()})
    return output


def _source_files(source):
    for path in source.iterdir():
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError('Indirect web source: ' + str(path))
        if stat.S_ISDIR(mode):
            yield from _source_files(path)
        elif stat.S_ISREG(mode):
            yield path


def _inventory_icon_paths(apps):
    _, marker, assignment = apps.partition(b'window.TV_APPS')
    if not marker:
        return set()
    value = assignment.lstrip().removeprefix(b'=').strip().removesuffix(b';')
    if b''.join(value.split()) == b'{apps:[],inputs:[]}':  # Older empty build placeholder.
        return set()
    inventory = json.loads(value)
    return {app['icon'] for app in inventory.get('apps', [])
            if isinstance(app, dict) and isinstance(app.get('icon'), str) and app['icon'].startswith('icons/')}


def _recover_inventory(source, draft):
    if draft.is_symlink() or (draft.exists() and not draft.is_dir()):
        raise ValueError('Invalid launcher inventory workspace: ' + str(draft))
    if not draft.exists():
        return
    members = set(draft.iterdir())
    if not members:
        draft.rmdir()
        return
    owner = draft / INVENTORY_OWNER
    if (owner not in members or any(path.is_symlink() for path in members)
            or not owner.is_file() or owner.stat().st_size
            or {path.name for path in members} - {INVENTORY_OWNER, 'apps.js', 'icons', 'previous-icons'}):
        raise ValueError('Unmanaged launcher inventory workspace: ' + str(draft))

    apps, icons, previous = draft / 'apps.js', draft / 'icons', draft / 'previous-icons'
    destination = source / 'icons'
    # The staged apps.js disappears only when publication commits or rollback has restored the artwork.
    if apps.exists():
        if not icons.exists() and destination.exists():
            destination.replace(icons)
        if previous.exists():
            previous.replace(destination)
        apps.unlink()
    for path in (icons, previous):
        if path.exists():
            shutil.rmtree(path)
    owner.unlink()
    draft.rmdir()


@contextmanager
def launcher_inventory(source, *, write=False):
    source = source.resolve()
    draft = source.with_name(INVENTORY_PREFIX + source.name)
    lock = draft.with_name(draft.name + '.lock')
    # An immutable source need not allocate a lock file. A writer must create
    # this persistent lock before changing anything and would invalidate the read.
    def has_state():
        return any(path.exists() or path.is_symlink() for path in (lock, draft))

    if not write and not os.access(source.parent, os.W_OK) and not has_state():
        yield
        if has_state():
            raise RuntimeError('Launcher inventory changed during staging. Try again.')
        return

    with build_lock(lock):
        _recover_inventory(source, draft)
        if write:
            try:
                draft.mkdir(mode=0o700)
                (draft / INVENTORY_OWNER).touch()
                yield draft
            finally:
                _recover_inventory(source, draft)
        else:
            yield


def _read_launcher(source):
    with launcher_inventory(source):
        paths = {path.relative_to(source).as_posix(): path for path in _source_files(source)}
        files = {name: path.read_bytes() for name, path in paths.items() if not name.startswith('icons/')}
        icons = _inventory_icon_paths(files.get('apps.js', b''))
        if not icons <= paths.keys():
            raise ValueError('Launcher inventory artwork is missing. Run sync-apps.py again.')
        # A workspace from an earlier sync can still contain unreferenced artwork.
        files.update({name: paths[name].read_bytes() for name in sorted(icons)})
        return files


def _compile_stage(source, compiler, resolution):
    if not source.is_dir():
        raise ValueError('Web source must be a directory: ' + str(source))
    manifest = source / 'appinfo.json'
    if (not manifest.is_symlink() and manifest.is_file()
            and json.loads(manifest.read_bytes()).get('id') == 'com.gathin.tvhome'):
        files = _read_launcher(source)
    else:
        files = {path.relative_to(source).as_posix(): path.read_bytes()
                 for path in _source_files(source)}
    if resolution is not None:
        if 'appinfo.json' not in files:
            raise ValueError('Graphics resolution requires an app manifest')
        info = json.loads(files['appinfo.json'])
        info['resolution'] = resolution
        files['appinfo.json'] = (json.dumps(info, indent=2) + '\n').encode()
    return compiler(files)


def _inside(path, directory):
    if path.is_relative_to(directory):
        return True
    # Detect aliases on case-insensitive filesystems as well as lexical overlap.
    for candidate in (path, *path.parents):
        try:
            if candidate.samefile(directory):
                return True
        except FileNotFoundError:
            continue
    return False


@contextmanager
def build_lock(lock):
    """Reserve a build path or fail promptly if another process owns it."""
    if lock.is_symlink() or (lock.exists() and not lock.is_file()):
        raise ValueError('Invalid build lock: ' + str(lock))

    # Keep the lock file so every process takes the lock on the same inode.
    # The operating system releases it when the build exits, including on a crash.
    with lock.open('ab') as stream:
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            raise RuntimeError('Another build is using ' + str(lock)) from error
        if os.fstat(stream.fileno()).st_size:
            raise ValueError('Invalid build lock: ' + str(lock))
        yield


@contextmanager
def _stage_lock(workspace):
    workspace.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock = workspace / '.cytv-web-stage-v1.lock'
    if workspace.resolve() != workspace or (any(workspace.iterdir()) and not lock.exists()):
        raise ValueError('Unmanaged web staging directory: ' + str(workspace))
    with build_lock(lock):
        if any(path.name not in (lock.name, 'new', 'previous') for path in workspace.iterdir()):
            raise ValueError('Unmanaged web staging directory: ' + str(workspace))
        yield

def stage(source, output, compiler=compile_web, resolution=None):
    if resolution is not None and resolution not in ('1280x720', '1920x1080'):
        raise ValueError('Unsupported app graphics resolution')
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.name == '..':
        output = output.resolve()
    output = output.parent.resolve() / output.name
    if _inside(output, source) or _inside(source, output):
        raise ValueError('Compile into a separate staging directory, outside the source.')
    workspace = output.with_name('.cytv-web-stage-' + output.name)
    if _inside(workspace, source) or _inside(source, workspace):
        raise ValueError('Compile into a separate staging directory, outside the source.')
    if any(path.name.startswith((INVENTORY_PREFIX, '.cytv-web-stage-'))
           for path in (output, *output.parents)):
        raise ValueError('Output path uses a reserved web staging directory: ' + str(output))

    staged, previous = workspace / 'new', workspace / 'previous'
    with _stage_lock(workspace):
        for path in (output, staged, previous):
            if path.is_symlink() or (path.exists() and (not path.is_dir() or path.resolve() != path)):
                raise ValueError('Invalid web staging directory: ' + str(path))
        # An interruption between the two renames leaves the saved tree here.
        # Restore it before attempting another build.
        if previous.exists():
            if output.exists():
                shutil.rmtree(previous)
            else:
                previous.rename(output)
        if staged.exists():
            shutil.rmtree(staged)

        compiled = _compile_stage(source, compiler, resolution)
        staged.mkdir()
        try:
            for name, raw in compiled.items():
                relative = Path(name)
                if relative.anchor or '..' in relative.parts:
                    raise ValueError('Invalid staged asset: ' + name)
                target = staged / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            if output.exists():
                output.rename(previous)
            staged.rename(output)
        except BaseException:
            if previous.exists() and not output.exists():
                previous.rename(output)
            raise
        finally:
            if staged.exists():
                shutil.rmtree(staged)
        if previous.exists():
            shutil.rmtree(previous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resolution', choices=('1280x720', '1920x1080'), help='Explicit app graphics resolution; source manifest is unchanged')
    args = parser.parse_args()
    stage(args.input, args.output, resolution=args.resolution)

"""Select working copies of public build inputs by their repository paths."""
import os
from pathlib import Path
import stat
import subprocess


def indexed_paths(root, *prefixes):
    marker = root / '.git'
    if not marker.exists() and not marker.is_symlink():
        return None  # A source export can also sit inside another repository.
    raw = subprocess.check_output(
        ['git', 'ls-files', '-z', '--deduplicate', '--', *prefixes], cwd=root)
    return {Path(os.fsdecode(name)) for name in raw.split(b'\0') if name}


def regular_source(root, relative):
    path = root / relative
    if relative.anchor or '..' in relative.parts or path.resolve() != path:
        raise ValueError('Indirect web source: ' + str(path))
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        raise ValueError('Expected a regular web source: ' + str(path))
    return path

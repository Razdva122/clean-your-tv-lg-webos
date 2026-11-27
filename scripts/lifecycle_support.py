"""Build the shared, static ARM cleanup-lock gate."""
import os
from pathlib import Path
import subprocess
import sys


def build_lifecycle_gate(target, work):
    root = Path(__file__).resolve().parents[1]
    target = Path(target).absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ,
        ZIG_GLOBAL_CACHE_DIR=str(Path(work) / 'zig-global-cache'),
        ZIG_LOCAL_CACHE_DIR=str(Path(work) / 'zig-cache'),
    )
    subprocess.run([
        sys.executable, '-m', 'ziglang', 'cc', '-target', 'arm-linux-musleabi',
        '-std=c99', '-Wall', '-Wextra', '-Werror', '-Os', '-static', '-s',
        'native/installer/lifecycle-gate.c', '-o', str(target),
    ], cwd=root, env=environment, check=True)

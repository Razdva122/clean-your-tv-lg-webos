"""Compile Helper app and service JS for the TV's Node 0.10 (not the web engine)."""
import argparse
import json
from pathlib import Path
import subprocess

from scripts.tv_web_build import ROOT, stage


def compile_helper(files):
    scripts = {name: raw.decode('utf-8') for name, raw in files.items() if name.endswith('.js')}
    result = subprocess.run(['node', str(ROOT / 'scripts/compile-helper.cjs')],
                            input=json.dumps(scripts), capture_output=True, text=True,
                            encoding='utf-8', cwd=ROOT, timeout=120)
    if result.returncode:
        raise RuntimeError('Helper compilation failed. Run npm ci in the source checkout.\n' + result.stderr)
    return dict(files, **{name: code.encode('utf-8') for name, code in json.loads(result.stdout).items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    stage(args.input, args.output, compiler=compile_helper)

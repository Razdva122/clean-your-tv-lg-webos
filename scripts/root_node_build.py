"""Opt-in legacy Root prototype; no shipping builder selects this by default."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def compile_root_node(files):
    scripts = {name: raw.decode('utf-8') for name, raw in files.items() if name.endswith('.js')}
    result = subprocess.run(['node', str(ROOT/'scripts/compile-root-node.cjs')],
                            input=json.dumps(scripts), capture_output=True, text=True,
                            encoding='utf-8', cwd=ROOT, timeout=120)
    if result.returncode:
        raise RuntimeError('Root Node prototype compilation failed. Run npm ci.\n'+result.stderr)
    return dict(files, **{name: raw.encode('utf-8') for name, raw in json.loads(result.stdout).items()})

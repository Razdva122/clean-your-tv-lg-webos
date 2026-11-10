"""Copy allowlisted CYTV source and verified public TV payload for Android."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cytv.package import verify_payload
from cytv.tv_sources import stage_sources


def main():
    payload = ROOT / 'build/cytv/payload'
    manifest = verify_payload(payload)
    generated = ROOT / 'android/app/build/generated'
    source = generated / 'python'
    assets = generated / 'assets'
    source.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    (assets / 'cytv-build.json').write_text(json.dumps({
        'schema': 1,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'versions': json.loads((ROOT / 'release-versions.json').read_text()),
    }, indent=2) + '\n')
    for target in (source / 'cytv', assets / 'payload'):
        if target.exists(): shutil.rmtree(target)
        target.mkdir(parents=True)
    for path in (ROOT / 'cytv').glob('*.py'):
        # Never bundle desktop frameworks or executables.
        if path.stem not in ('gui', 'gui_style', 'desktop', 'desktop_entry'):
            shutil.copy2(path, source / 'cytv' / path.name)
    stage_sources(source / 'cytv/tv')
    shutil.copy2(ROOT / 'lgtv.py', source / 'lgtv.py')
    for name in [*manifest['files'], 'payload.json']:
        target = assets / 'payload' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(payload / name, target)
    # UI assets and font are checked in alongside their font license.
    stale_ui = assets / 'ui'
    if stale_ui.exists(): shutil.rmtree(stale_ui)
    print(f"Android sources staged; {len(manifest['files'])} verified public payload files.")


if __name__ == '__main__': main()

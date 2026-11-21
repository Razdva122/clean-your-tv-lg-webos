"""Stage maintained CYTV runtime sources and the verified public TV payload."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cytv.package import verify_payload
from cytv.tv_sources import NAMES, stage_sources

DESKTOP_MODULES = {
    '__main__.py', 'desktop.py', 'desktop_entry.py', 'gui.py', 'gui_style.py',
    'installer_update.py', 'wallpaper.py', 'wallpaper_gui.py',
}


def python_sources():
    # Select names from the index and copy their current checkout contents.
    tracked = subprocess.check_output([
        'git', 'ls-files', '-z', '--deduplicate', '--', ':(top,glob)cytv/*.py', 'lgtv.py',
    ], cwd=ROOT, encoding='utf-8').split('\0')
    sources = []
    for name in filter(None, tracked):
        path = ROOT / name
        if path.name in DESKTOP_MODULES:
            continue
        if path.is_symlink():
            raise ValueError(f'Indirect Android Python source: {name}')
        if path.is_file():
            sources.append(name)
    if 'lgtv.py' not in sources:
        raise FileNotFoundError('Missing tracked Android Python source: lgtv.py')
    return sources


def describe_inputs(generated):
    sources = python_sources()
    payload = json.loads((ROOT / 'build/cytv/payload/payload.json').read_text())
    payload_files = ['payload.json', *payload['files']]
    python_files = {*sources, *(f'cytv/tv/{name}.js' for name in NAMES)}
    asset_files = {'cytv-build.json', *(f'payload/{name}' for name in payload_files)}

    def matches(directory, expected):
        if directory.is_symlink():
            return False
        actual = set()
        for path in directory.rglob('*'):
            if path.is_symlink():
                return False
            if path.is_file():
                actual.add(path.relative_to(directory).as_posix())
        return actual == expected

    # Gradle's output fingerprints do not invalidate the task for extra files.
    return {
        'pythonSources': sources,
        'payloadFiles': [f'build/cytv/payload/{name}' for name in payload_files],
        'outputsMatch': matches(generated / 'python', python_files) and matches(generated / 'assets', asset_files),
    }


def main(generated):
    payload = ROOT / 'build/cytv/payload'
    manifest = verify_payload(payload)
    sources = python_sources()
    build_info = {
        'schema': 1,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'versions': json.loads((ROOT / 'release-versions.json').read_text()),
    }
    if generated.is_symlink():
        raise ValueError('Indirect Android generated directory')
    source = generated / 'python'
    assets = generated / 'assets'
    for target in (source, assets):
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
        target.mkdir(parents=True)
    (assets / 'cytv-build.json').write_text(json.dumps(build_info, indent=2) + '\n')
    (source / 'cytv').mkdir()
    for name in sources:
        shutil.copy2(ROOT / name, source / name)
    stage_sources(source / 'cytv/tv')
    for name in [*manifest['files'], 'payload.json']:
        target = assets / 'payload' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(payload / name, target)
    print(f"Android sources staged; {len(manifest['files'])} verified public payload files.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'android/app/build')
    parser.add_argument('--describe-inputs', action='store_true')
    args = parser.parse_args()
    generated = args.build_dir / 'generated/cytv'
    if args.describe_inputs:
        print(json.dumps(describe_inputs(generated)))
    else:
        main(generated)

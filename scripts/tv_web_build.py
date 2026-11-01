"""Compile only TV web application assets; never process native/Node services."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def compile_web(files):
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


def stage(source, output, compiler=compile_web, resolution=None):
    if resolution is not None and resolution not in ('1280x720', '1920x1080'):
        raise ValueError('Unsupported app graphics resolution')
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('Compile into a separate staging directory, not the source.')
    files = {}
    for path in source.rglob('*'):
        if path.is_symlink():
            raise ValueError('Indirect web source: ' + str(path))
        if path.is_file():
            files[path.relative_to(source).as_posix()] = path.read_bytes()
    if resolution is not None:
        if 'appinfo.json' not in files:
            raise ValueError('Graphics resolution requires an app manifest')
        info = json.loads(files['appinfo.json'])
        info['resolution'] = resolution
        files['appinfo.json'] = (json.dumps(info, indent=2) + '\n').encode()
    compiled = compiler(files)
    if output.exists():
        shutil.rmtree(output)
    for name, raw in compiled.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resolution', choices=('1280x720', '1920x1080'), help='Explicit app graphics resolution; source manifest is unchanged')
    args = parser.parse_args()
    stage(args.input, args.output, resolution=args.resolution)

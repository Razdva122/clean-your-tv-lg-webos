#!/usr/bin/env python3
"""Export a hashed, explicitly unpublished theme-author runtime candidate.

Run npm ci in the main checkout first. This exports the actual compiled renderer
and trusted mock bridge; it never installs dependencies or contacts a TV.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ('theme-api/compile.cjs', 'theme-api/contract.json',
                'launcher/theme-policy.js', 'launcher/theme-data.js', 'scripts/compile-tv-web.cjs',
                'package.json', 'package-lock.json', 'scripts/check-theme-submissions.cjs')


def checked_read(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('unsafe source path')
    cursor = Path(root)
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('source symlink forbidden: ' + name)
    return cursor.read_bytes()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def compile_preview(stage):
    # Same compatibility transform as packaged TV web files, not a renderer fork.
    for edition in ('launcher', 'root-launcher'):
        folder = stage / 'preview' / edition
        sources = {str(p.relative_to(folder)): p.read_text() for p in folder.rglob('*')
                   if p.is_file() and p.suffix in ('.js', '.css', '.html')}
        result = subprocess.run(['node', str(ROOT / 'scripts/compile-tv-web.cjs')],
                                input=json.dumps(sources), text=True,
                                capture_output=True, check=True)
        for name, content in json.loads(result.stdout).items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(content)


def export(destination, allow_dirty=False):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('runtime destination already exists; choose a new empty path')
    dirty = bool(git('status', '--porcelain', '--untracked-files=normal'))
    if dirty and not allow_dirty:
        raise ValueError('source checkout is dirty; commit first or explicitly use --allow-dirty for a local candidate')
    for name in SOURCE_FILES:
        checked_read(ROOT, name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.theme-runtime-', dir=destination.parent))
    try:
        for name in SOURCE_FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(checked_read(ROOT, name))
        preview = runpy.run_path(str(ROOT / 'scripts/preview.py'))
        preview['export_site'](stage / 'preview')
        for edition in ('launcher', 'root-launcher'):
            folder = stage / 'preview' / edition
            (folder / 'theme-policy.js').write_bytes(checked_read(ROOT, 'launcher/theme-policy.js'))
            index = folder / 'index.html'
            content = index.read_text()
            if 'src="theme-policy.js"' not in content:
                content = content.replace('<script src="theme-runtime.js">', '<script src="theme-policy.js"></script>\n<script src="theme-runtime.js">')
            index.write_text(content)
        compile_preview(stage)
        (stage / 'preview/theme-card.css').write_bytes(checked_read(ROOT, 'showcase/src/theme-card.css'))
        for name in ('classic-preview.png', 'classic-preview.json', 'CLASSIC-CREDITS.txt'):
            (stage / 'preview' / name).write_bytes(checked_read(ROOT, 'showcase/assets/' + name))
        files = []
        for file in sorted(stage.rglob('*')):
            if file.is_file():
                content = file.read_bytes()
                files.append({'path': file.relative_to(stage).as_posix(),
                              'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
        package = json.loads((ROOT / 'package.json').read_text())
        manifest = {
            'schemaVersion': 1, 'themeApiVersion': 1, 'status': 'candidate',
            'source': {'repository': 'https://github.com/Razdva122/clean-your-tv-lg-webos',
                       'commit': git('rev-parse', 'HEAD'), 'dirty': dirty},
            'minimumHomeVersion': json.loads((ROOT / 'launcher/appinfo.json').read_text())['version'],
            'compiler': 'theme-api/compile.cjs', 'policy': 'launcher/theme-policy.js',
            'contract': 'theme-api/contract.json',
            'submissionValidator': 'scripts/check-theme-submissions.cjs',
            'preview': {'no-root': 'preview/launcher/index.html', 'root': 'preview/root-launcher/index.html'},
            'dependencies': package['devDependencies'],
            'dependencyPolicy': 'Install exact package-lock.json dependencies in toolkit; dependencies are not copied into the runtime.',
            'files': files,
        }
        (stage / 'runtime.json').write_text(json.dumps(manifest, indent=2) + '\n')
        os.replace(stage, destination)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--allow-dirty', action='store_true')
    args = parser.parse_args()
    manifest = export(args.out, args.allow_dirty)
    print('Exported candidate runtime: ' + str(args.out.resolve()))
    print('Source ' + manifest['source']['commit'] + (' (dirty snapshot)' if manifest['source']['dirty'] else ''))
    print('Not a published or signed release. Files: ' + str(len(manifest['files'])))


if __name__ == '__main__':
    main()

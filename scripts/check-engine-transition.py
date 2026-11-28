#!/usr/bin/env python3
"""Check the candidate installer Engine against the latest signed public Engine."""
import json
from pathlib import Path
import runpy
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
release = runpy.run_path(str(ROOT / 'scripts/prepare-release.py'))
builder = runpy.run_path(str(ROOT / 'system-updater/build.py'))


def published_engine(meta, folder):
    tag = meta['tag_name']
    if meta['draft'] is not False or meta['prerelease'] is not False or not tag.startswith('v'):
        raise ValueError('Expected a published stable release')
    release['version'](tag[1:])
    envelope = release['download'](meta, 'system-bootstrap-v1.json', folder)
    catalog = json.loads(subprocess.check_output(
        ['node', str(ROOT / 'system-updater/engine-policy.js'), 'verify'],
        input=json.dumps({'proof': json.loads(envelope)}).encode()
    ))
    engine = catalog['engine']
    name = 'system-engine_' + engine['version'] + '.tar.gz'
    if engine['url'] != release['URL'] + tag + '/' + name:
        raise ValueError('Signed Engine catalog is for a different release')
    raw = release['download'](meta, name, folder)
    if len(raw) != engine['size'] or release['digest'](raw) != engine['sha256']:
        raise ValueError('Published Engine archive differs from signed catalog')
    return engine


def check_candidate(bundle, prior):
    # The public Engine archive is generated directly from this installer bundle.
    raw = builder['engine_archive'](bundle)
    manifest = json.loads((bundle / 'bundle.json').read_bytes())
    current = {'version': manifest['engine_version'], 'size': len(raw), 'sha256': release['digest'](raw)}
    release['verify_engine_transition'](current, raw, raw, prior)
    return current


def main():
    meta = json.loads(release['gh']('api', 'repos/' + release['REPO'] + '/releases/latest'))
    with tempfile.TemporaryDirectory(prefix='cytv-engine-preflight-') as tmp:
        folder = Path(tmp).resolve()
        prior = published_engine(meta, folder)
        bundle = folder / 'system-updater'
        builder['build'](bundle)
        print(f"Published {meta['tag_name']} Engine {prior['version']} SHA-256 {prior['sha256']}", flush=True)
        current = check_candidate(bundle, prior)
        print(f"Candidate Engine {current['version']} SHA-256 {current['sha256']}")


if __name__ == '__main__':
    main()

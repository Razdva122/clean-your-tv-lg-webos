#!/usr/bin/env python3
"""Verify a signed release APK and record its public release provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def parse_badging(badging):
    """Read release identity from aapt's compiled Android manifest output."""
    if re.search(r'^application-debuggable(?:\s|$)', badging, re.MULTILINE):
        raise ValueError('Release APK must not be debuggable')
    package_line = re.search(r'^package: (.*)$', badging, re.MULTILINE)
    if not package_line:
        raise ValueError('APK package metadata is missing')
    fields = dict(re.findall(r"(\w+)='([^']*)'", package_line.group(1)))
    def sdk(field):
        found = re.search(r"^" + field + r":'(\d+)'$", badging, re.MULTILINE)
        if not found:
            raise ValueError('APK SDK metadata is missing: ' + field)
        return int(found.group(1))
    native = re.search(r'^native-code:(.*)$', badging, re.MULTILINE)
    abis = re.findall(r"'([^']+)'", native.group(1)) if native else []
    if abis != ['arm64-v8a']:
        raise ValueError('APK must contain only arm64-v8a native code')
    try:
        return {'package': fields['name'], 'android_version_name': fields['versionName'],
                'android_version_code': int(fields['versionCode']), 'abi': abis[0],
                'min_sdk': sdk('sdkVersion'), 'target_sdk': sdk('targetSdkVersion'),
                'debuggable': False}
    except KeyError as error:
        raise ValueError('APK version metadata is missing') from error


def normalize_digest(value):
    digest = value.strip().replace(':', '').lower()
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Invalid signing certificate SHA-256 digest')
    return digest


def verify_apk(apk, root=ROOT, *, allow_legacy=False):
    apk, root = Path(apk).resolve(), Path(root).resolve()
    versions = json.loads((root / 'release-versions.json').read_text())
    sdk = os.environ.get('ANDROID_HOME')
    if not sdk:
        raise ValueError('ANDROID_HOME must point to the Android SDK')
    build_tools = Path(sdk) / 'build-tools/35.0.0'
    badging = subprocess.check_output([str(build_tools / 'aapt'), 'dump', 'badging', str(apk)], text=True)
    metadata = parse_badging(badging)
    expected = {'package': 'com.cleanyourtv.android', 'android_version_name': versions['android'],
                'android_version_code': versions['android_version_code'], 'abi': 'arm64-v8a',
                'min_sdk': 24, 'target_sdk': 35, 'debuggable': False}
    if metadata != expected:
        raise ValueError('APK package, version or SDK metadata mismatch')
    certificates = subprocess.check_output(
        [str(build_tools / 'apksigner'), 'verify', '--print-certs', str(apk)], text=True)
    digests = re.findall(r'^Signer #\d+ certificate SHA-256 digest:\s*([^\r\n]+)', certificates, re.MULTILINE)
    expected_digest = normalize_digest((root / 'android/preview-certificate.sha256').read_text())
    if len(digests) != 1 or normalize_digest(digests[0]) != expected_digest:
        raise ValueError('APK signing certificate mismatch')
    verify_embedded = runpy.run_path(str(root / 'scripts/assemble-release.py'))['verify_embedded']
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid source commit')
    with zipfile.ZipFile(apk) as archive:
        try:
            build_info = json.loads(archive.read('assets/cytv-build.json'))
        except (KeyError, ValueError) as error:
            raise ValueError('APK build provenance is missing or invalid') from error
        if build_info != {'schema': 1, 'source_commit': commit, 'versions': versions}:
            raise ValueError('APK build provenance does not match the release source')
        verify_embedded(lambda name: archive.read('assets/payload/' + name), versions, allow_legacy=allow_legacy)
    return {'schema': 1, 'source_commit': commit, 'versions': versions, **metadata,
            'signer_sha256': expected_digest, 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = verify_apk(args.apk)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Verified Android APK:', args.apk)


if __name__ == '__main__':
    main()

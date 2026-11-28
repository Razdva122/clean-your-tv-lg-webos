#!/usr/bin/env python3
"""Generate and verify Homebrew metadata from final IPK bytes, without executing them."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homebrew.build import APP_ID, APP_PREFIX, IDENTITIES, installer_metadata, installer_files, verify_offline
from homebrew.payload import safe_name
from cytv import package

REPOSITORY = 'https://github.com/Razdva122/clean-your-tv-lg-webos'
ASSETS = REPOSITORY + '/releases/download/'
MANIFEST_NAME = 'homebrew-manifest.json'


def digest(raw): return hashlib.sha256(raw).hexdigest()


def https(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Public HTTPS URL required')
    return value


def verify_payload(files):
    # Only repository-owned validators run. Embedded deploy/setup/bundle scripts are data.
    payload = {name[len(APP_PREFIX+'payload/'):]:raw for name,raw in files.items() if name.startswith(APP_PREFIX+'payload/')}
    if not payload: raise ValueError('Missing offline payload')
    with tempfile.TemporaryDirectory(prefix='cytv-homebrew-metadata-') as directory:
        root = Path(directory).resolve()
        for name,raw in payload.items():
            safe_name(name)
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        checked = verify_offline(root)
    if set(checked['versions']) != set(IDENTITIES) or set(checked['packages']) != set(IDENTITIES):
        raise ValueError('Invalid offline component inventory')
    for key, app in IDENTITIES.items():
        name=safe_name(checked['packages'][key])
        info=json.loads(package.data_files(payload[key+'/'+name])['usr/palm/applications/'+app+'/appinfo.json'])
        if info.get('id') != app or info.get('version') != checked['versions'][key]:
            raise ValueError('Offline component version mismatch')
    return checked


def manifest(ipk_bytes, ipk_url, icon_url, source_url):
    info=installer_metadata(ipk_bytes)
    files=installer_files(ipk_bytes)
    verify_payload(files)
    filename=APP_ID+'_'+info['version']+'_all.ipk'
    if not re.fullmatch(re.escape(ASSETS)+r'v\d{1,4}\.\d{1,4}\.\d{1,4}/'+re.escape(filename),https(ipk_url)):
        raise ValueError('Immutable project release IPK URL required')
    return {'id':info['id'],'title':info['title'],'type':info['type'],'version':info['version'],
            'appDescription':'Install Clean Your TV on an already-rooted TV. Setup offers the No-root edition when Root is incompatible and No-root checks pass. Installer updates are separate from product updates.',
            'iconUri':https(icon_url),'sourceUrl':https(source_url),'rootRequired':True,
            'ipkUrl':ipk_url,'ipkHash':{'sha256':digest(ipk_bytes)},'ipkSize':len(ipk_bytes),
            'installedSize':sum(map(len,files.values()))}


def verify_manifest(ipk_bytes, value):
    expected=manifest(ipk_bytes,value['ipkUrl'],value['iconUri'],value['sourceUrl'])
    if value.get('rootRequired') is not True or value != expected:
        raise ValueError('Homebrew manifest differs from actual package')
    return value


def verify_accepted(ipk_bytes, manifest_bytes, approval):
    value=verify_manifest(ipk_bytes,json.loads(manifest_bytes))
    if (approval.get('schema') != 1 or approval.get('release') != value['ipkUrl'][len(ASSETS):].split('/')[0] or value['version']=='0.0.0' or approval.get('version') != value['version']
            or approval.get('ipk_sha256') != digest(ipk_bytes) or approval.get('manifest_sha256') != digest(manifest_bytes)
            or any(not isinstance(approval.get(key),str) or not approval[key].strip() for key in ('hardware_acceptance','human_review'))):
        raise ValueError('Exact Homebrew hardware acceptance and human review required')
    return value


def verify_publication(ipk_bytes, manifest_bytes, approval, sums):
    value=verify_accepted(ipk_bytes,manifest_bytes,approval)
    for name,raw in ((MANIFEST_NAME,manifest_bytes),(value['ipkUrl'].rsplit('/',1)[1],ipk_bytes)):
        if sums.get(name) != digest(raw): raise ValueError('Homebrew publication checksum missing or mismatched: '+name)
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipk',type=Path,required=True)
    parser.add_argument('--ipk-url');parser.add_argument('--icon-url');parser.add_argument('--source-url',default=REPOSITORY)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify',type=Path,help='Existing manifest to verify against IPK')
    parser.add_argument('--build',type=Path,help='BUILD-INFO.json with accepted homebrew record')
    parser.add_argument('--sums',type=Path,help='SHA256SUMS required for publication verification')
    args=parser.parse_args();raw=args.ipk.read_bytes()
    if args.verify:
        metadata=args.verify.read_bytes()
        if args.build:
            if not args.sums:parser.error('--build requires --sums')
            sums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in args.sums.read_text().splitlines()}
            verify_publication(raw,metadata,json.loads(args.build.read_text())['homebrew'],sums)
        else:verify_manifest(raw,json.loads(metadata))
    else:
        if not args.ipk_url or not args.icon_url or not args.output:parser.error('generation requires --ipk-url, --icon-url and --output')
        args.output.write_text(json.dumps(manifest(raw,args.ipk_url,args.icon_url,args.source_url),sort_keys=True,indent=2)+'\n')
    print('Verified Homebrew package '+digest(raw))


if __name__=='__main__': main()

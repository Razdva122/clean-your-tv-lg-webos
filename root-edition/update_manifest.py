#!/usr/bin/env python3
"""Generate unsigned Root metadata for explicit maintainer review and signing."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from deploy import APP, verify_bundle, checked_file


def manifest(bundle,release,notes):
    if not re.fullmatch(r'v\d{1,4}\.\d{1,4}\.\d{1,4}',release):raise ValueError('Expected release tag vX.Y.Z')
    if not isinstance(notes,str) or len(notes)>4000:raise ValueError('Release notes exceed 4000 characters')
    bundle=Path(bundle).resolve();verified=verify_bundle(bundle)
    info=json.loads(checked_file(bundle,'release.json'));raw=checked_file(bundle,verified['package'])
    if not 0<len(raw)<=32*1024*1024:raise ValueError('Root package exceeds updater bound')
    from updater.package import SCREENSAVER_RECIPE, archive, members
    has_companion = SCREENSAVER_RECIPE in archive(members(raw)['data.tar.gz'])
    return {'schema':1,'edition':'root','application':APP,'release':release,'version':info['version'],
            'runtime':1,'updater':2 if has_companion else 1,'profile':1,
            'url':'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/'+release+'/'+verified['package'],
            'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'notes':notes}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--release',required=True)
    parser.add_argument('--notes',default='');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();value=manifest(args.bundle,args.release,args.notes)
    with args.output.open('x') as out:json.dump(value,out,indent=2);out.write('\n')

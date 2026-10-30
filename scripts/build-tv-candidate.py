#!/usr/bin/env python3
"""Build only the three production-format Root TV QA assets. Never contacts a TV."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW='.github/workflows/tv-candidate.yml'
REPO='Razdva122/clean-your-tv-lg-webos'

def build(output,source,run_id,attempt):
    if not re.fullmatch('[a-f0-9]{40}',source) or type(run_id) is not int or run_id<=0 or type(attempt) is not int or attempt<=0:raise ValueError('Exact source/run/attempt required')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=source:raise ValueError('Build source differs from selected commit')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('Clean checkout of the exact source is required')
    output=Path(output).absolute()
    if output.exists() or '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('New direct output required')
    versions=json.loads((ROOT/'release-versions.json').read_text());tag='v'+versions['release']
    runpy.run_path(str(ROOT/'scripts/prepare-release.py'))['validate_versions'](versions)
    if json.loads((ROOT/'release-plan.json').read_text()).get('version')!=versions['release']:raise ValueError('Candidate plan/version mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='root-tv-build-',dir=output.parent) as tmp:
        payload=Path(tmp)
        subprocess.run([sys.executable,'root-edition/build.py','--output',str(payload/'root'),'--version',versions['root']],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'root-edition/build_updater.py','--output',str(payload/'root-updater')],cwd=ROOT,check=True)
        release=runpy.run_path(str(ROOT/'system-updater/build.py'))
        manifest,raws=release['release_set'](payload,'root',tag,local=False,notes='Preliminary direct TV QA; not release acceptance.')
        output.mkdir()
        for c in manifest['components']:(output/c['url'].rsplit('/',1)[1]).write_bytes(raws[c['name']])
    provenance={'schema':1,'repository':REPO,'workflow':WORKFLOW,'source':source,'run_id':run_id,'attempt':attempt,'versions':versions,'public_key_sha256':hashlib.sha256((ROOT/'updater-service/release-public.pem').read_bytes()).hexdigest()}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    # Data-only inspection uses the same bounded trusted parser as signing.
    feeds=runpy.run_path(str(ROOT/'scripts/root-candidate-feeds.py'))
    metadata=dict(provenance,release=tag,artifact={'sha256':'0'*64},preliminary=True,package_job={'id':0})
    feeds['validate_tv_bundle']({p.name:p.read_bytes() for p in output.iterdir()},metadata)
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--run-id',type=int,required=True);p.add_argument('--attempt',type=int,required=True);a=p.parse_args()
    print(build(a.output,a.source,a.run_id,a.attempt))
if __name__=='__main__':main()

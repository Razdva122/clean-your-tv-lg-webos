#!/usr/bin/env python3
"""Review or apply one-time Root Updater setup through explicit root SSH."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--ssh');parser.add_argument('--identity',type=Path);parser.add_argument('--apply',action='store_true')
    parser.add_argument('--component-only',action='store_true',help='Deliberate low-level updater bootstrap recovery only')
    parser.add_argument('--operation',help='Shared product UUID')
    parser.add_argument('--resume',action='store_true',help='Explicitly continue that shared request')
    parser.add_argument('--device',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--python',default='/usr/bin/python3',choices=('/usr/bin/python3','/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'))
    args=parser.parse_args()
    if args.device:
        from updater.bootstrap import apply, preflight, resume
        from installation import device_operation, Ownership, read_journal, JOURNALS
        def eligible():
            if args.resume:
                current=Ownership().status()
                if not current or current['terminal'] or (current['owner'],current['journal'])!=('root-bootstrap','bootstrap.json') or read_journal(JOURNALS['root-bootstrap'][0]) is None:
                    raise ValueError('No matching pending Root bootstrap; inspect retained state')
            else:preflight(args.bundle,args.baseline)
        with device_operation('root-bootstrap', recovery=args.resume, check=eligible):
            print(json.dumps(resume(args.bundle) if args.resume else apply(args.bundle,args.baseline)))
        return
    from updater.bootstrap import verify_bundle,permission_plan
    from deploy import verify_bundle as verify_root
    from setup import bundle_bytes
    updater=verify_bundle(args.bundle,reader=bundle_bytes);baseline=verify_root(args.baseline)
    plan={'operation':'one-time-root-updater-setup' if args.component_only else 'shared-root-product-setup','component_only':args.component_only,'product_components':['root-updater'] if args.component_only else ['root','root-updater'],'replaces_root_runtime':False,'baseline':baseline['package'],
          'permissions':permission_plan(),'requires_root_mode_disabled':True,'hardware_validated':False}
    print(json.dumps(plan,indent=2))
    if not args.apply:return
    if not args.ssh:parser.error('--apply requires --ssh')
    if not args.component_only:
        from setup import execute_product
        execute_product('install',args.ssh,args.baseline,args.bundle,args.identity,operation=args.operation,python=args.python,resume=args.resume)
        return
    from setup import ssh_options
    options=ssh_options(args.ssh,args.identity);remote='/tmp/cytv-root-updater-'+uuid.uuid4().hex
    subprocess.run(['ssh',*options,'umask 077; test "$(id -u)" = 0 && mkdir '+shlex.quote(remote)],check=True,stdin=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='root-updater-') as tmp:
        staging=Path(tmp)
        for kind,folder,manifest in (('updater',args.bundle,updater),('baseline',args.baseline,baseline)):
            target=staging/kind;target.mkdir()
            for name in (*manifest['files'],'bundle.json'):
                output=target/name;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes((folder/name).read_bytes())
        subprocess.run(['scp','-O',*options[:-1],'-r',str(staging/'updater'),str(staging/'baseline'),args.ssh+':'+remote+'/'],check=True,stdin=subprocess.DEVNULL)
    argv=['env','-u','PYTHONHOME','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1',args.python,remote+'/updater/setup-updater.py','--device','--apply','--bundle',remote+'/updater','--baseline',remote+'/baseline']
    if args.resume:argv.append('--resume')
    subprocess.run(['ssh',*options,shlex.join(argv)],check=True,stdin=subprocess.DEVNULL)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Internal reviewed-source native admission observation; never install or recover."""
import argparse
import json
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from cytv import root_native_inspection as inspection, state
from cytv.transport import inspection_secret


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('digest','inspect'))
    parser.add_argument('--operation')
    parser.add_argument('--source-sha256')
    parser.add_argument('--interactive-auth',action='store_true')
    args=parser.parse_args()
    if args.action=='digest':print(inspection.source_pin(PROJECT));return
    inspection.program(PROJECT,args.operation)
    if args.source_sha256!=inspection.source_pin(PROJECT):parser.error('exact reviewed --source-sha256 required')
    store=state.Store()
    profiles=[p for p in store.profiles() if p.get('edition')=='root'
        and (store.pending(p) or {}).get('product_operation')==args.operation]
    if len(profiles)!=1:raise ValueError('exactly_one_matching_saved_root_profile_required')
    def secret(_):raise RuntimeError('saved_automatic_authentication_required')
    result=inspection.inspect_saved(store,profiles[0],args.operation,
        inspection_secret if args.interactive_auth else secret,PROJECT,args.source_sha256)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()

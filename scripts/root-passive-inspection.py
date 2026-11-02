#!/usr/bin/env python3
"""Internal original-operation read. No staging, interpreter execution or recovery."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cytv import root_passive, state
from cytv.transport import SSH, inspection_secret


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation',required=True)
    parser.add_argument('--interactive-auth',action='store_true',help='Allow hidden local SSH secret entry; original saved host pin required')
    args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{32}',args.operation):parser.error('original operation UUID required')
    store=state.Store()
    profiles=[p for p in store.profiles() if p['edition']=='root' and
              (store.pending(p) or {}).get('action')=='install' and
              (store.pending(p) or {}).get('product_operation')==args.operation]
    if len(profiles)!=1:raise ValueError('exactly_one_matching_saved_root_profile_required')
    profile=profiles[0]
    def secret(_):raise RuntimeError('saved_automatic_authentication_required')
    with store.lock(profile):
        pending=store.pending(profile)
        remote=SSH.connect(profile,store.device_dir(profile),inspection_secret if args.interactive_auth else secret,
                           lambda *_:False,persist=False)
        try:
            result=root_passive.collect(remote,args.operation,pending)
            if store.pending(profile)!=pending:raise ValueError('original_host_pending_changed')
            print(json.dumps(result,sort_keys=True))
        finally:remote.close()


if __name__=='__main__':main()

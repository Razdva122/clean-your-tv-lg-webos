"""Detached bounded timer; no activation or profile publication."""
import json
import os
import sys
import tempfile
import time
import device_adapter as d
from profile_guardian import watch


def ready(transaction, deadline):
    try: start_ticks=d.process_start(os.getpid())
    except OSError: start_ticks=None  # Non-Linux fixture; never accepted as live TV guardian.
    fd, name = tempfile.mkstemp(dir=d.STATE, prefix='.profile-ready-')
    try:
        with os.fdopen(fd,'w') as f:
            json.dump({'transaction':transaction,'deadline':deadline,'pid':os.getpid(),'start_ticks':start_ticks},f)
            f.flush(); os.fsync(f.fileno())
        os.replace(name,d.STATE/'profile-guardian-ready.json'); d.sync(d.STATE)
    finally:
        if os.path.exists(name): os.unlink(name)


def restore(transaction):
    for attempt in range(12):
        try:
            from persistent_recovery import bound_exit
            bound = bound_exit(transaction)
            result = 'restored' if bound is True else d.restore_once(expected_transaction=transaction)
        except Exception as exc:
            print(str(exc),flush=True); result='recovering'
        if result not in ('pending','recovering'): return result
        time.sleep(5)
    return 'recovering'


def run(transaction):
    d.trusted_dir(d.STATE)
    def continuation():
        from persistent_recovery import Coordinator
        from persistent_store import Store
        c = Coordinator(Store(d.STATE))
        if not os.path.lexists(c.binding): return None
        if c.read_binding()['transaction'] != transaction: return None
        from persistent_health import authorized, run, guardian_ping
        live=authorized(transaction)
        # First cold identity validation must finish before claiming a pulse.
        guardian_ping(transaction)
        if live: return run(transaction, restore)
        return None
    from shutdown_state import monitor
    shutdown = monitor(transaction)
    try:
        return watch(transaction, lambda:d.safe_json(d.STATE/'profile-trial.json'),
                     ready,restore,time.monotonic,time.sleep,continuation=continuation)
    finally: shutdown.close()


if __name__ == '__main__':
    if os.geteuid()!=0 or len(sys.argv)!=2: raise SystemExit('Root and transaction required')
    print(run(sys.argv[1]),flush=True)

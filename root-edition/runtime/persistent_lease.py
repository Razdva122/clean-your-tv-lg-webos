"""Independent persistent-mode input-loop lease policy.

A device adapter must authenticate the root-owned lease and hold the transaction
lock inside restore. Only successful input-loop heartbeats may advance sequence;
process existence is not health. A separate durable intent is disabled before
recovery, preventing boot from re-enabling a failed mode.
"""
import math


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def watch(transaction, boot, load, restore, clock, sleep):
    previous = None
    previous_clock = None
    def fail(reason):
        restore(reason)  # Adapter verifies restoration or retains recovery state.
        return reason
    while True:
        now = clock()
        if not finite(now) or (previous_clock is not None and now < previous_clock):
            return fail('clock-reset')
        previous_clock = now
        try: lease = load()
        except (OSError, ValueError): return fail('unreadable-lease')
        # A heartbeat can be published while load() is reading. Validate against
        # a time sampled after that read, not a stale pre-read timestamp.
        now = clock()
        if not finite(now) or now < previous_clock: return fail('clock-reset')
        previous_clock = now
        if not isinstance(lease, dict): return fail('invalid-lease')
        if not isinstance(lease.get('transaction'), str): return fail('invalid-lease')
        if lease['transaction'] != transaction: return 'superseded'
        if lease.get('state') in ('restored', 'conflict'): return lease['state']
        if (lease.get('state') not in ('active','waiting-input') or lease.get('boot') != boot
                or type(lease.get('sequence')) is not int or lease['sequence'] <= 0
                or not finite(lease.get('issued')) or not finite(lease.get('expires'))):
            return fail('invalid-lease')
        issued, expires = lease['issued'], lease['expires']
        if not 0 <= issued <= now or not issued < expires <= issued+2:
            return fail('invalid-lease')
        if previous is not None:
            if (lease['sequence'] < previous['sequence']
                    or issued < previous['issued']
                    or (lease['sequence'] == previous['sequence'] and lease != previous)):
                return fail('invalid-lease')
        if now >= expires: return fail('lease-expired')
        previous = dict(lease)
        sleep(min(.25, expires-now))

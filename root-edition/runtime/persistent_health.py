"""Volatile input-loop health. Durable intent alone never authorizes persistence."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import device_adapter as d
from persistent_store import Store
from persistent_recovery import Coordinator

ROOT = Path('/tmp/clean-your-tv-root-health')


class HealthContextError(ValueError):
    """Fixed refusal code; no attempt, boot identity or token in the error."""
    def __init__(self, reason):
        self.reason = reason if reason in ('transaction-mismatch','binding-restored',
            'generation-mismatch','token-mismatch','boot-mismatch','phase-inactive',
            'failsafe-present') else 'unknown'
        super().__init__('Inactive or stale health context: '+self.reason)


def path(transaction):
    return ROOT/(hashlib.sha256(transaction.encode()).hexdigest()+'.json')


def context(transaction):
    d.require_home(purpose='live')
    from intent_runtime import boot_identity
    c = Coordinator(Store(d.STATE)); intent = c.store.read(); binding = c.read_binding()
    if binding['transaction'] != transaction: reason = 'transaction-mismatch'
    elif binding['restored']: reason = 'binding-restored'
    elif binding['generation'] != intent['generation']: reason = 'generation-mismatch'
    elif binding['token'] != intent['token']: reason = 'token-mismatch'
    elif intent['boot'] != boot_identity(): reason = 'boot-mismatch'
    elif intent['phase'] not in ('trial','starting','active'): reason = 'phase-inactive'
    elif d.FAILSAFE.exists(): reason = 'failsafe-present'
    else: return intent
    raise HealthContextError(reason)


def authorized(transaction):
    try:
        intent = context(transaction)
        return intent['phase'] == 'active' and intent['enabled']
    except (OSError,ValueError,KeyError): return False


def publish(transaction, sequence):
    intent = context(transaction)
    if type(sequence) is not int or sequence <= 0: raise ValueError('Invalid sequence')
    try: ROOT.mkdir(mode=0o700)
    except FileExistsError: pass
    d.trusted_dir(ROOT)
    now = time.monotonic()
    value = dict(transaction=transaction,boot=intent['boot'],sequence=sequence,
                 state='active',issued=now,expires=now+2)
    fd, name = tempfile.mkstemp(dir=ROOT,prefix='.health-')
    try:
        with os.fdopen(fd,'w') as out: json.dump(value,out)
        os.replace(name,path(transaction))
    finally:
        if os.path.exists(name):os.unlink(name)


def load(transaction):
    d.trusted_dir(ROOT)
    return d.safe_json(path(transaction))


def require_fresh(transaction):
    intent=context(transaction);value=load(transaction);now=time.monotonic()
    from persistent_lease import finite
    if (value.get('transaction') != transaction or value.get('boot') != intent['boot']
            or value.get('state') != 'active' or type(value.get('sequence')) is not int
            or value['sequence'] <= 0 or not finite(value.get('issued'))
            or not finite(value.get('expires'))
            or not 0 <= value['issued'] <= now < value['expires']
            or not value['issued'] < value['expires'] <= value['issued']+2):
        raise ValueError('Input heartbeat is stale or invalid')
    return value


def run(transaction, restore):
    from persistent_lease import watch
    from intent_runtime import boot_identity
    def read():
        j=d.safe_json(d.STATE/'profile-trial.json')
        if j['transaction'] != transaction:return dict(transaction=j['transaction'])
        if j['state'] in ('restored','conflict'):return dict(transaction=transaction,state=j['state'])
        if not authorized(transaction):raise ValueError('Persistent authority revoked')
        guardian_ping(transaction)
        return load(transaction)
    return watch(transaction,boot_identity(),read,lambda reason:restore(transaction),time.monotonic,time.sleep)


def guardian_ping(transaction):
    try: ROOT.mkdir(mode=0o700)
    except FileExistsError: pass
    d.trusted_dir(ROOT)
    fd,name=tempfile.mkstemp(dir=ROOT,prefix='.guard-')
    try:
        with os.fdopen(fd,'w') as out:json.dump(dict(transaction=transaction,issued=time.monotonic()),out)
        os.replace(name,path(transaction).with_suffix('.guard'))
    finally:
        if os.path.exists(name):os.unlink(name)


def require_guardian(transaction):
    d.trusted_dir(ROOT)
    value=d.safe_json(path(transaction).with_suffix('.guard'))
    from persistent_lease import finite
    if (value.get('transaction') != transaction or not finite(value.get('issued'))
            or not 0 <= time.monotonic()-value['issued'] < 2):
        raise ValueError('Independent guardian heartbeat expired')

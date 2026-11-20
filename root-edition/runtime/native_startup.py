"""Source choices for authenticated native Home startup, without profile writes."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time

try:
    from . import c1_keyfilter as gate
    from .intent_runtime import startup_load, startup_validate, startup_CHANNEL, startup_YOUTUBE
except ImportError:
    import c1_keyfilter as gate
    from intent_runtime import startup_load, startup_validate, startup_CHANNEL, startup_YOUTUBE


def load(root, uid):
    return startup_load(lambda: json.loads(gate.secure(Path(root)/'startup-policy.json', uid, 4096)))


def active(value):
    intent, proof = value['intent'], value['effective']
    return (intent['enabled'] is True and intent['phase'] == 'active'
            and proof['healthy'] is True and proof['stopped'] is False
            and proof['token'] == intent['token']
            and value['recovery'].get('integrity_verified') is True)


def status(root=gate.STATE, uid=0):
    return dict(sources=load(root, uid), active=active(gate.status(root, uid)))


def configure(sources, root=gate.STATE, uid=0):
    sources = startup_validate(sources)
    with gate.operation(root, uid):
        load(root, uid)  # An unreadable old policy remains recovery evidence.
        current = gate.status(root, uid)
        if not active(current):
            raise ValueError('Change Home is off or recovery is unverified')
        gate.atomic(Path(root)/'startup-policy.json', dict(version=2, sources=sources), uid)
        return dict(sources=sources, active=True)


def entry(args, root=gate.STATE, uid=0):
    if args == ['status']:
        return status(root, uid)
    if args == ['configure']:
        raw = sys.stdin.buffer.read(2049)
        if len(raw) > 2048:
            raise ValueError('Oversized startup sources')
        return configure(json.loads(raw), root, uid)
    raise ValueError('Unknown startup operation')


def require_session(value, expected):
    from boot_gate import observation
    intent = value['intent']
    if (not active(value) or intent != expected
            or intent['boot'] != gate.boot_identity()
            or not gate.valid_resume_session(intent, intent.get('session'))
            or intent['session'] != gate.boot_session()
            or observation() != (True, False)):
        raise ValueError('Inactive native startup session')


def source(reply, deadline):
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        return None
    rows = reply.get('foregroundAppInfo')
    if not isinstance(rows, list) or len(rows) != 1:
        return None
    row = rows[0]
    if (not isinstance(row, dict) or row.get('windowType') != gate.CARD
            or type(row.get('displayId', 0)) is not int or row.get('displayId', 0) != 0
            or row.get('visible', True) is not True or row.get('pip', False) is not False
            or row.get('multiview', False) is not False or row.get('viewType', 'normal') != 'normal'):
        return None
    app = row.get('appId')
    if app == gate.LIVE_TV:
        return 'tv'
    if app == startup_YOUTUBE:
        return 'youtube'
    if app == startup_CHANNEL:
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Native startup deadline')
        metadata = gate.luna('luna://com.webos.applicationManager/getAppInfo', {'id':app},
                             timeout=min(.5, remaining))
        if not isinstance(metadata, dict) or metadata.get('returnValue') is not True:
            return None
        info = metadata.get('appInfo')
        store = '/media/cryptofs/apps/usr/palm/applications/'+app
        expected = dict(id=app, type='web', vendor='LifeStream ltd.', folderPath=store,
                        activeFolderPath=store)
        if (isinstance(info, dict) and all(info.get(k) == v for k, v in expected.items())
                and info.get('CPApp') is True and info.get('internalInstallationOnly') is True):
            return 'tv'
    # HDMI, unknown apps, LG Home and current Root are never startup permission.
    return None


def receipt(root, uid):
    path = gate.private_directory(root, uid)/'startup-attempt.json'
    try:
        value = json.loads(gate.secure(path, uid, 4096))
    except FileNotFoundError:
        return path, None
    if (not isinstance(value, dict) or set(value) != {'schema','boot','session','token'}
            or type(value['schema']) is not int or value['schema'] != 1
            or not isinstance(value['boot'], str)
            or re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value['boot']) is None
            or not isinstance(value['token'], str) or not gate.legacy.TOKEN.fullmatch(value['token'])
            or not gate.valid_resume_session(dict(enabled=True,phase='active',boot=value['boot']), value['session'])):
        raise ValueError('Invalid startup launch receipt; retain evidence')
    return path, value


def after_boot(result, root=gate.STATE, uid=0):
    """Call outside the operation lock only after authenticated boot resumption.

    The session is consumed before the native launch barrier. A lost launch
    acknowledgement must never become a second attempt that steals foreground.
    """
    try:
        with gate.operation(root, uid):
            expected = result['intent']
            require_session(result, expected)
            require_session(gate.status(root, uid), expected)
            path, prior = receipt(root, uid)
            attempt = dict(schema=1, boot=expected['boot'], session=expected['session'], token=expected['token'])
            if prior is not None and prior['session'] == attempt['session']:
                return 'already-attempted'
            sources = load(root, uid)
            deadline = time.monotonic()+1.5
            reply = gate.luna('luna://com.webos.surfacemanager/getForegroundAppInfo', {}, timeout=.5)
            selected = source(reply, deadline)
            if time.monotonic() >= deadline or not sources.get(selected, False):
                return 'preserved'
            # Recheck both lifecycle and presentation at the submission boundary.
            require_session(gate.status(root, uid), expected)
            fresh = gate.luna('luna://com.webos.surfacemanager/getForegroundAppInfo', {}, timeout=.5)
            if fresh != reply or time.monotonic() >= deadline:
                return 'preserved'
            require_session(gate.status(root, uid), expected)
            if time.monotonic() >= deadline:
                return 'preserved'
            gate.atomic(path, attempt, uid)
            gate.launch_return(root, uid, expected['token'])
            return 'launched'
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError):
        return 'unavailable'

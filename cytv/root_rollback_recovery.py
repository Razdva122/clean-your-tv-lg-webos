"""Resume an expired readiness check using the installed standalone Root Updater."""
from .rollback_recovery_sources import SCRIPT as SOURCE_CHECKS


SCRIPT = SOURCE_CHECKS + r'''
STATE = Path('/var/lib/clean-your-tv-root-updater')
ERROR = 'restored profile readiness unconfirmed'


def original_code(state):
    binding = json.loads(read(state / 'bootstrap-bundle.json'))
    receipt = json.loads(read(state / 'infrastructure.json'))
    manifest = binding['bundle']
    files = receipt['code']
    required = {
        'installation.py', 'package_identity.py',
        'updater/core.py', 'updater/device.py',
        'updater/store.py', 'updater/luna.py',
    }
    if (binding.get('schema') != 1 or manifest.get('schema') != 1
            or tuple(receipt.get(k) for k in ('schema', 'runtime', 'updater')) != (1, 1, 1)
            or not isinstance(files, dict) or not required <= files.keys()):
        raise ValueError('Original Root Updater inventory required')
    for name, sha in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or str(path) != name or '..' in path.parts
                or not re.fullmatch('[a-f0-9]{64}', sha)
                or manifest['files'].get(name) != sha
                or digest(read(state / 'code' / name)) != sha):
            raise ValueError('Original Root Updater inventory mismatch')
    return files


def verify_rollback(manager, device, tx, app):
    from installation import terminal_install

    if not tx['rollbackAttempted'] or tx.get('error') != ERROR:
        raise ValueError('Completed standalone rollback readiness timeout required')
    for leg, item in (('installEvidence', tx['candidate']), ('rollbackEvidence', tx['prior'])):
        evidence = tx[leg]
        if not manager._success(evidence):
            raise ValueError('Successful installer terminal evidence required')
        path = str(device.cached(item))
        # The original worker records the cache input and the backend returns
        # the terminal event for its separately staged copy of that input.
        terminal = dict(completed=True, event=evidence['terminal'].get('event'))
        if (evidence['submitted'] != dict(package=path, version=item['version'])
                or not terminal_install(terminal, app)):
            raise ValueError('Installer terminal binding mismatch')
        device.descriptor(item)
    manager._profile(tx)


def recover(manager, device, store, ownership, check, app, launch,
            sleep=time.sleep, health_seconds=120):
    from installation import Busy
    from package_identity import TransitionUnknown
    lease = ownership.status()
    if (not lease or (lease['owner'], lease['journal']) != ('root-update', 'transaction.json')
            or lease['stage'] not in ('recovery-required', 'verifying-rollback', 'rolled-back')):
        raise ValueError('Matching Root Updater ownership required')

    def mutation():
        return ownership.operation('root-update', 'transaction.json', resume=lease['id'], check=check)

    with mutation() as record:
        with store.lock():
            tx = manager.status()
            if tx is None or tx['phase'] not in ('recovery-required', 'verifying-rollback', 'rolled-back'):
                raise ValueError('Standalone rollback readiness recovery required')
            verify_rollback(manager, device, tx, app)
            archives = type(store)(Path(store.root) / 'readiness-recovery', uid=store.uid)
            archive = tx.get('readinessRecovery')
            if archive is not None:
                original = archives.read(archive)
                if not original or archive != 'readiness-recovery-' + tx['id'] + '-' + digest(encode(original)):
                    raise ValueError('Recovery archive changed')
                for key in ('id', 'prior', 'candidate', 'profileDigest', 'installEvidence', 'rollbackEvidence'):
                    if tx[key] != original.get(key):
                        raise ValueError('Archived rollback evidence changed')
            elif tx['phase'] != 'recovery-required':
                raise ValueError('No explicit Root Updater recovery attempt')
            if record['terminal']:
                if tx['phase'] == tx.get('homeResumePhase') == record['stage'] == 'rolled-back':
                    return tx
                raise ValueError('Nonterminal Root Updater ownership required')
            if tx['phase'] == 'recovery-required':
                started, deadline = tx.get('launched'), tx.get('deadline')
                if (type(started) not in (int, float) or not math.isfinite(started)
                        or started < 0 or deadline != started + health_seconds or manager._now() < deadline):
                    raise ValueError('Expired rollback readiness window required')
                if store.read('ready-rollback-' + tx['id']) is not None:
                    raise ValueError('Existing rollback readiness evidence requires inspection')
                device.integrity()
                try:
                    device.require_components()
                except TransitionUnknown:
                    # The old journal itself blocks Root identity. All owners
                    # were checked, and the prior payload is verified below.
                    pass
                route = device.routing_status()
                if route.get('active') is not False or route.get('safe') is not True:
                    raise ValueError('Verified LG Home routing required')
                name = 'readiness-recovery-' + tx['id'] + '-' + digest(encode(tx))
                saved = archives.read(name)
                if saved is not None and saved != tx:
                    raise ValueError('Recovery archive changed')
                if saved is None:
                    archives.write(name, tx)
                # The installed-package verifier may repair service registration.
                if not device.verify_installed(tx['prior']):
                    raise ValueError('Restored Root package identity mismatch')
                now = manager._now()
                if now < deadline:
                    raise ValueError('Clock changed before readiness recovery')
                tx.update(launched=now, deadline=now + health_seconds, readinessRecovery=name)
                tx = manager._save(tx, 'verifying-rollback')
            if tx['phase'] == 'verifying-rollback':
                device.require_components()
        ownership.stage(record, tx['phase'], terminal=False)
        if tx['phase'] == 'verifying-rollback':
            now = manager._now()
            if tx['launched'] <= now < tx['deadline'] and manager._receipt(tx, 'ready') is None:
                # Keep removal excluded during close and launch. Release this
                # lock before waiting for the launcher's authenticated ready RPC.
                if manager.status() != tx:
                    raise ValueError('Root Updater journal changed before relaunch')
                launch()

    if tx['phase'] == 'verifying-rollback':
        stop = time.monotonic() + health_seconds
        while (tx['launched'] <= manager._now() < tx['deadline']
               and manager._receipt(tx, 'ready') is None):
            if time.monotonic() >= stop:
                raise ValueError('Root readiness window has not completed')
            sleep(.1)

    stop = time.monotonic() + 10
    while True:
        try:
            with mutation() as record:
                current = manager.status()
                if current != tx:
                    raise ValueError('Root Updater journal changed during readiness recovery')
                if tx['phase'] == 'verifying-rollback':
                    now = manager._now()
                    if tx['launched'] <= now < tx['deadline'] and manager._receipt(tx, 'ready') is None:
                        raise ValueError('Root readiness window has not completed')
                    current = manager.run()
                if current['phase'] == 'rolled-back':
                    device.finish(current)
                    current = manager.status()
                ownership.stage(record, current['phase'],
                                terminal=current['phase'] == current.get('homeResumePhase') == 'rolled-back')
                return current
        except Busy:
            if time.monotonic() >= stop:
                raise
            sleep(.1)


def entry():
    if os.geteuid() != 0:
        raise PermissionError('Root recovery required')
    load_sources(STATE / 'code', original_code(STATE), standalone=True)
    from installation import Ownership, pending_journals
    from updater.core import HEALTH_SECONDS, Manager
    from updater.device import APP, Device
    from updater.luna import call
    from updater.store import Store

    store = Store(STATE)
    device = Device(store)
    device.integrity()

    def launch():
        try:
            call('luna://com.webos.applicationManager/closeByAppId', {'id': APP})
        except Exception as error:
            if getattr(error, 'stopped_launcher', None) != APP:
                raise
        device.launch()

    fd = os.open(STATE / 'daemon.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
            raise ValueError('Unsafe Root Updater worker lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = recover(Manager(store, device), device, store, Ownership(),
                         lambda: pending_journals('root-update'), APP, launch,
                         health_seconds=HEALTH_SECONDS)
        print(json.dumps({'returnValue': True, 'result': result}), flush=True)
    finally:
        os.close(fd)
'''


def program():
    return SCRIPT + '\nentry()\n'

"""Read-only proof for an explicitly reviewed, restored profile activation."""

SCRIPT = '''import fcntl,os,stat,sys
sys.path.insert(0,'/var/lib/clean-your-tv-root/runtime')
import device_adapter as d
from persistent_recovery import Coordinator
from persistent_store import Store
from update_guard import control
c=Coordinator(Store(d.STATE));intent=c.store.read()
with control(d.STATE,d.EXPECTED_UID),c.locked(intent):
    fd=os.open(d.STATE/'profile-trial.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=d.EXPECTED_UID
                or info.st_nlink!=1 or info.st_mode&0o022):raise ValueError('Unsafe trial lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if intent['phase']!='disabled' or intent['enabled']:raise ValueError('Intent is unresolved')
        if any(os.path.lexists(p) for p in (d.FAILSAFE,d.STATE/'update-block.json',d.TARGET,d.STATE/'profile-candidate.stage')):
            raise ValueError('Activation is blocked')
        binding=c.read_binding();journal=c.route(binding['transaction'])
        if (not binding['restored'] or (binding['generation'],binding['token'])!=(intent['generation'],intent['token'])
                or journal['state']!='restored' or d.active_guardian(journal)):
            raise ValueError('Recovery is unresolved')
        current=d.read();profiles=current['profiles']
        if (current!=journal['baseline'] or current['sam_home']!='com.webos.app.home'
                or profiles['defaultApps']['categories']['home']!='com.webos.app.home'
                or profiles['idleApp']['appId']!='com.webos.app.home'):
            raise ValueError('Stock Home is unverified')
        print('CYTV_ACTIVATION_RECOVERABLE')
    finally:os.close(fd)
'''

"""Private boot entry: shared package identity is DATA, never executable input."""
import os
from pathlib import Path
import subprocess
import sys
from package_identity import identity, worker_allowed, TransitionUnknown

OWNERS={'com.cleanyourtv.root.preview':Path('/var/lib/clean-your-tv-root'),
        'com.cleanyourtv.root.updater':Path('/var/lib/clean-your-tv-root-updater'),
        'com.cleanyourtv.system.updater':Path('/var/lib/clean-your-tv-system-updater')}
INSTALLED=Path('/media/developer/apps')


def present(owner):
    try:
        identity(owner,purpose='admission',installed=INSTALLED,full=True)
        return True
    except (OSError,ValueError,TypeError,KeyError):return False


def start(owner):
    if owner not in OWNERS:raise ValueError('Foreign startup owner')
    try:
        if not worker_allowed(owner):return False
    except (OSError,ValueError,TypeError,KeyError):return False
    if not present(owner):
        if owner=='com.cleanyourtv.root.preview':return False
        try:identity(owner,purpose='worker',installed=INSTALLED,full=True)
        except TransitionUnknown:pass
        except (OSError,ValueError,TypeError,KeyError):return False
    state=OWNERS[owner]
    if owner=='com.cleanyourtv.root.preview':
        subprocess.run(['/bin/sh',str(state/'service/boot-recover.sh'),'mark'],check=True)
    else:
        code=state/'code'
        runner='run-system-updater.py' if owner=='com.cleanyourtv.system.updater' else 'run-updater.py'
        subprocess.Popen(['/usr/bin/node',str(code/'python_boot.js'),str(state),str(code/runner),'worker'],
                         stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                         start_new_session=True,close_fds=True)
    return True


if __name__=='__main__':
    if os.geteuid()!=0 or len(sys.argv)!=2:raise SystemExit('Root owner boot required')
    start(sys.argv[1])

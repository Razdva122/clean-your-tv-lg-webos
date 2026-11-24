"""Run only in a disposable Linux container with stock ARM rootfs at /sysroot.

The container must have /tmp mounted as ramfs and a disk-backed /var/lib.
No TV services are run. Filesystem and Node operations are real; package
submission and daemon scratch consumption are outside this fixture.
"""
import os
from pathlib import Path
import shlex
import subprocess
import sys
sys.path.insert(0, '/project')
from cytv import package, root_staging, storage
from cytv.errors import UserError

QEMU = ['/usr/bin/qemu-arm', '-L', '/qemu-libs', '-E', 'LC_ALL=C', '-E', 'LANG=C',
        '-E', 'LD_LIBRARY_PATH=/sysroot/lib:/sysroot/usr/lib']


class StockRemote:
    def run(self, command, **kwargs):
        args = shlex.split(command)
        if args[:2] == ['env', '-u']:
            index = args.index('/usr/bin/node')
            args = QEMU + ['/sysroot/usr/bin/node'] + args[index+1:]
        elif args[:1] == ['LC_ALL=C']:
            args = QEMU + ['/sysroot/bin/busybox.nosuid'] + args[1:]
        else:
            raise AssertionError('Unexpected command boundary')
        result = subprocess.run(args, capture_output=True, timeout=30)
        if result.returncode:
            sys.stderr.write(result.stderr.decode(errors='replace'))
            result.check_returncode()
        return result.stdout.decode()


remote = StockRemote()
print(remote.run("LC_ALL=C stat -f -c '%t' /tmp").strip())
print(remote.run('LC_ALL=C df -Pk /tmp').strip())
try:
    storage.check(remote, {'/tmp': 1024}, lambda _: None)
except UserError as error:
    assert error.reason_code == 'tv-storage-ramfs'
    print('Original ramfs refusal reproduced')
else:
    raise AssertionError('Expected original guard refusal')

payload = {'fixture.ipk': package.ipk('com.example.offline', '1', {'usr/palm/applications/com.example.offline/data': b'x'*1048576}), 'runtime/c1-keyfilter-guard': b'offline guardian fixture'}
assert storage.install(remote, payload, print, root=True) is True
stage = root_staging.create(remote, 'c1-root')
assert stage.startswith(root_staging.ROOT+'/')
assert os.stat(stage).st_mode & 0o777 == 0o700
for name, raw in payload.items():
    file = Path(stage)/name
    file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    file.write_bytes(raw)
    file.chmod(0o700 if name.endswith('guard') else 0o600)
foreign = Path(stage)/'unrecognized'
foreign.write_bytes(b'keep')
foreign.chmod(0o600)
try:
    root_staging.retire(remote, stage, payload)
except subprocess.CalledProcessError:
    assert foreign.read_bytes() == b'keep'
    assert (Path(stage)/'fixture.ipk').read_bytes() == payload['fixture.ipk']
    print('Unknown bytes preserved before any retirement')
else:
    raise AssertionError('Foreign bytes must refuse retirement')
foreign.unlink()
root_staging.retire(remote, stage, payload)
assert not Path(stage).exists()
print('Stock Node created, read back and retired authenticated private disk staging')

root = Path(root_staging.ROOT)
root.rmdir()
root.symlink_to('/tmp', target_is_directory=True)
try:
    root_staging.create(remote, 'product')
except subprocess.CalledProcessError:
    assert root.is_symlink()
    print('Symlink staging parent refused without adoption')
else:
    raise AssertionError('Expected unsafe-parent refusal')
root.unlink()
root.mkdir(mode=0o700)
subprocess.run(['mount','-t','tmpfs','-o','mode=0700','tmpfs',str(root)], check=True)
try:
    try:
        root_staging.create(remote, 'product')
    except subprocess.CalledProcessError:
        assert list(root.iterdir()) == []
        print('Separate memory mount refused before payload staging')
    else:
        raise AssertionError('Expected staging filesystem refusal')
finally:
    subprocess.run(['umount',str(root)], check=True)
    root.rmdir()
print('PASS: capability-selected Root ramfs staging offline')

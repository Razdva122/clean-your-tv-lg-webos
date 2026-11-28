"""Run the browser acceptance test against the exact web payload of a built IPK."""
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
pilot = runpy.run_path(str(ROOT / 'single-home/build.py'))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if len(sys.argv) > 1:
            ipk = Path(sys.argv[1])
        else:
            ipk = work / 'home.ipk'
            pilot['build'](ipk, None)
        raw = ipk.read_bytes()
        info, _, _ = pilot['inspect'](raw)
        prefix = 'usr/palm/applications/' + info['id'] + '/'
        app = work / 'application'
        for name, data in pilot['package'].data_files(raw).items():
            if name.startswith(prefix):
                target = app / pilot['package'].safe_name(name[len(prefix):])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        subprocess.run(['node', 'single-home/tests/product-ui.cjs', str(app)], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()

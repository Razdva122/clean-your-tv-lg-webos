#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ZIG:=zig}"
: "${ARES_PACKAGE:=ares-package}"
graphics_resolution="${CYTV_GRAPHICS_RESOLUTION:-1920x1080}"
case "$graphics_resolution" in 1280x720|1920x1080) ;; *) echo 'Unsupported CYTV_GRAPHICS_RESOLUTION; use 1280x720 or 1920x1080.'; exit 1 ;; esac
command -v "$ZIG" >/dev/null || { echo 'Install Zig 0.14.1 or set ZIG to its executable.'; exit 1; }
python3 - <<'PYBUILD'
from pathlib import Path
import shutil
for p in [Path('build/native-app'),Path('build/native-service')]:
 if p.exists(): shutil.rmtree(p)
p=Path('launcher/apps.js')
if not p.exists(): p.write_text('window.TV_APPS = {apps: [], inputs: []};\n')
PYBUILD
mkdir -p build/native-app/state build/native-service/state dist
baseline=$(python3 - <<'PYPIN'
import json, runpy
from pathlib import Path
info = json.loads(Path('native/app/appinfo.json').read_text())
raw = runpy.run_path('scripts/build-cytv.py')['helper_baseline'](info['version'])
if raw is not None:
    Path('dist', info['id'] + '_' + info['version'] + '_arm.ipk').write_bytes(raw)
    print('published')
PYPIN
)
if [[ "$baseline" != published ]]; then
# Stage from a clean set of public sources; never package local runtime state.
cp native/app/*.js native/app/*.json native/app/*.png build/native-app/
cp -R native/app/vendor build/native-app/
cp native/service/*.js native/service/*.json build/native-service/
cp native/service/app-inventory.js build/native-app/
cp native/app/state-permissions.js build/native-service/
python3 -m scripts.helper_build --input build/native-app --output build/native-app-compat
python3 -m scripts.helper_build --input build/native-service --output build/native-service-compat
rm -rf build/native-app build/native-service
mv build/native-app-compat build/native-app
mv build/native-service-compat build/native-service
mkdir -p build/native-app/state build/native-service/state
touch build/native-app/state/.keep build/native-service/state/.keep
"$ZIG" cc -target arm-linux-musleabi -Os -static -s native/app/detach.c -o build/native-app/detach
"$ZIG" cc -target arm-linux-musleabi -Os -static -s native/prototype/relay.c native/prototype/filter.c -o build/native-app/relay
"$ZIG" cc -target arm-linux-musleabi -Os -static -s native/app/resume.c -o build/native-app/resume
"$ARES_PACKAGE" build/native-app build/native-service -o dist
# Repair the package just built, even when older releases remain in dist/.
helper=$(python3 -c 'import json; a=json.load(open("build/native-app/appinfo.json")); print("dist/"+a["id"]+"_"+a["version"]+"_arm.ipk")')
python3 scripts/fix-package-data.py "$helper"
fi
python3 scripts/tv_web_build.py --input launcher --output build/home-app --resolution "$graphics_resolution"
# Stage only public renewal sources, including the paired theme receiver.
python3 - <<'PYRECEIVER'
import runpy
from pathlib import Path
from scripts.theme_receiver import inject
from scripts.helper_build import compile_helper
import shutil
sources = runpy.run_path('scripts/build-cytv.py')['tracked_files']('renewal-service')
# The service runs on the TV's Node (0.12 on webOS 3.x): compile it like Helper.
files = compile_helper(inject({name: data for name, data in sources.items() if not name.startswith('state/')}))
output = Path('build/home-service')
if output.exists():
    shutil.rmtree(output)
for name, data in files.items():
    target = output / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
channel = output / 'state/home-control'
channel.mkdir(parents=True)
(channel / '.keep').write_bytes(b'')
PYRECEIVER
"$ARES_PACKAGE" build/home-app build/home-service -o dist
home=$(python3 -c 'import json; a=json.load(open("build/home-app/appinfo.json")); print("dist/"+a["id"]+"_"+a["version"]+"_all.ipk")')
python3 scripts/fix-package-data.py "$home" --home-control
python3 - <<'PY'
from pathlib import Path
import hashlib
p=Path('dist');(p/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(p.glob('*.ipk'))))
PY

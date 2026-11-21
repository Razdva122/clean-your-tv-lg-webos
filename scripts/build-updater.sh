#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ARES_PACKAGE:=ares-package}"
: "${PYTHON:=python3}"
"$PYTHON" - <<'PYCLEAN'
from pathlib import Path
import shutil
for p in (Path('build/updater-service'), Path('build/updater-app'), Path('dist/updater-setup')):
    if p.exists(): shutil.rmtree(p)
PYCLEAN
mkdir -p dist
"$PYTHON" - <<'PYASSETS'
from pathlib import Path
from scripts.no_root_assets import updater_sources

root = Path.cwd()
app, service = updater_sources(root)
for destination, files in (('build/updater-app', app), ('build/updater-service', service)):
    for name, data in files.items():
        target = root / destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
PYASSETS
"$PYTHON" scripts/tv_web_build.py --input build/updater-app --output build/updater-app-compat
rm -rf build/updater-app
mv build/updater-app-compat build/updater-app
# The service runs on the TV's Node (0.12 on webOS 3.x): compile it like Helper.
"$PYTHON" -m scripts.helper_build --input build/updater-service --output build/updater-service-compat
rm -rf build/updater-service
mv build/updater-service-compat build/updater-service
# The staged JS has already been compiled for webOS. Keep its bytes in the IPK.
"$ARES_PACKAGE" --no-minify build/updater-app build/updater-service -o dist

mkdir -p dist/updater-setup/scripts/lib dist/updater-setup/updater-service
cp scripts/update-permissions.cjs dist/updater-setup/scripts/
cp scripts/lib/update-permissions.cjs dist/updater-setup/scripts/lib/
cp updater-service/permissions.js dist/updater-setup/updater-service/
cp docs/UPDATES.md dist/updater-setup/README.md

"$PYTHON" - <<'PYSUM'
from pathlib import Path
import hashlib
p=Path('dist')
(p/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(p.glob('*.ipk'))))
PYSUM

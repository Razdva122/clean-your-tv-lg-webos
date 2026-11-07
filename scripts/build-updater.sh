#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ARES_PACKAGE:=ares-package}"
python3 - <<'PYCLEAN'
from pathlib import Path
import shutil
for p in (Path('build/updater-service'), Path('build/updater-app'), Path('dist/updater-setup')):
    if p.exists(): shutil.rmtree(p)
PYCLEAN
mkdir -p build/updater-service dist
cp updater-service/*.js updater-service/*.json build/updater-service/
cp updater-service/release-public.pem build/updater-service/
cp updater-service/ca-bundle.crt updater-service/ca-LICENSE.txt build/updater-service/
cp launcher/user-data.js build/updater-service/user-data.js
cp -R updater-app build/updater-app
cp launcher/system-updates.js launcher/release-notes.js launcher/renewal-panel.css launcher/i18n.js launcher/catalogs.js launcher/i18n.css root-edition/ui/root-locales.js build/updater-app/
mkdir -p build/updater-app/fonts
cp launcher/fonts/NotoSans* build/updater-app/fonts/
python3 scripts/tv_web_build.py --input build/updater-app --output build/updater-app-compat
rm -rf build/updater-app
mv build/updater-app-compat build/updater-app
# The service runs on the TV's Node (0.12 on webOS 3.x): compile it like Helper.
python3 -m scripts.helper_build --input build/updater-service --output build/updater-service-compat
rm -rf build/updater-service
mv build/updater-service-compat build/updater-service
"$ARES_PACKAGE" build/updater-app build/updater-service -o dist

mkdir -p dist/updater-setup/scripts/lib dist/updater-setup/updater-service
cp scripts/update-permissions.cjs dist/updater-setup/scripts/
cp scripts/lib/update-permissions.cjs dist/updater-setup/scripts/lib/
cp updater-service/permissions.js dist/updater-setup/updater-service/
cp docs/UPDATES.md dist/updater-setup/README.md

python3 - <<'PYSUM'
from pathlib import Path
import hashlib
p=Path('dist')
(p/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(p.glob('*.ipk'))))
PYSUM

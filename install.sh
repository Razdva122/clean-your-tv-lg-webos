#!/usr/bin/env bash
# Build and install locally; only pairing approvals require user interaction.
set +x
set -euo pipefail
# Keep redirected logs plain; highlight all installer/tool stderr on a terminal.
if [[ -t 2 && "${TERM:-}" != dumb && -z "${NO_COLOR+x}" ]]; then
  exec 2> >(while IFS= read -r cytv_error_line || [[ -n "$cytv_error_line" ]]; do
    printf '\033[31m%s\033[0m\n' "$cytv_error_line" >&2
  done)
fi
cd "$(dirname "$0")"
if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
  echo 'Usage: ./install.sh [TV IPv4 address]'
  echo 'Requires Node.js 20.19+, npm, Python 3.9+, and LG Developer Mode + Key Server.'
  echo 'Downloads build tools locally; pairs, syncs, builds, installs and starts Home Helper.'
  exit 0
fi
[[ $# -le 1 ]] || { echo 'Usage: ./install.sh [TV IPv4 address]' >&2; exit 1; }
TV_HOST="${1:-${TV_HOST:-}}"
if [[ -z "$TV_HOST" ]]; then read -r -p 'TV IPv4 address (Developer Mode app): ' TV_HOST; fi
export TV_HOST
command -v python3 >/dev/null || { echo 'Install Python 3.9+ first.' >&2; exit 1; }
python3 - <<'PY'
import ipaddress, os, sys
if sys.version_info < (3, 9): raise SystemExit('Python 3.9+ is required.')
try: ipaddress.IPv4Address(os.environ['TV_HOST'])
except ValueError: raise SystemExit('Enter a valid TV IPv4 address, for example 192.168.1.50.')
PY
export DEVICE="${DEVICE:-clean-your-tv-${TV_HOST//./-}}"
[[ "$DEVICE" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'DEVICE must contain only letters, digits, _ and -.' >&2; exit 1; }
for tool in node npm; do
  command -v "$tool" >/dev/null || { echo 'Install Node.js 20.19+ (with npm) first.' >&2; exit 1; }
done
node -e 'const [major,minor]=process.versions.node.split(".").map(Number);if(major<20||(major===20&&minor<19))process.exit(1)' || { echo 'Node.js 20.19+ is required.' >&2; exit 1; }
npm ci --ignore-scripts --no-audit --no-fund
stage='preparing tools'
trap 'echo "Installation stopped while $stage. Fix the reported error and rerun ./install.sh. See docs/RECOVERY.md if packages were already installed." >&2' ERR
umask 077
printf '\nPreparing local build tools (no sudo)...\n'
python3 -m venv .venv
export PATH="$PWD/.venv/bin:$PATH"
# An explicit compiler also works on platforms without a ziglang Python wheel.
if [[ -z "${ZIG:-}" ]] && command -v zig >/dev/null; then
  ZIG="$(command -v zig)"
fi
if [[ -z "${ZIG:-}" ]]; then
  if [[ -n "${TERMUX_VERSION:-}" || "${PREFIX:-}" == */com.termux/* || "${OSTYPE:-}" == linux-android* ]]; then
    echo 'Termux requires a working Zig 0.14.1 compiler. Set ZIG=/absolute/path/to/zig and rerun ./install.sh; the ziglang Python distribution is not available for Android.' >&2
    exit 1
  fi
  python3 -m pip install 'ziglang==0.14.1'
  ZIG="$(python3 -c 'from pathlib import Path; import ziglang; print(Path(ziglang.__file__).parent / "zig")')"
fi
export ZIG
[[ "$("$ZIG" version)" == 0.14.1 ]] || { echo 'ZIG must point to a working Zig 0.14.1 executable.' >&2; exit 1; }
python3 -m pip install -r requirements.txt
# Pin the official CLI locally instead of depending on a global CLI's version.
npm install --prefix build/tools --no-audit --no-fund '@webos-tools/cli@3.2.6'
export PATH="$PWD/build/tools/node_modules/.bin:$PATH"
stage='pairing with the TV'
printf '\nEnable Developer Mode and Key Server on the TV. Keep its screen open.\n'
# Never print --listfull: saved profiles may include passphrases.
profile=$(ares-setup-device --listfull | python3 -c '
import json, os, sys
matches=[d for d in json.load(sys.stdin) if d["name"]==os.environ["DEVICE"]]
if matches and matches[0].get("deviceinfo") != dict(ip=os.environ["TV_HOST"], port="9922", user="prisoner"):
    raise SystemExit("DEVICE has a different address or SSH configuration. Choose a different DEVICE name.")
print("existing" if matches else "new")')
if [[ "$profile" == new ]]; then
  info=$(python3 -c 'import json,os; print(json.dumps(dict(host=os.environ["TV_HOST"],port="9922",username="prisoner")))')
  # CLI 3.2.6 prints every saved profile (including passphrases) after --add.
  if ! ares-setup-device --add "$DEVICE" --info "$info" >/dev/null 2>&1; then
    echo 'Could not create the TV profile. Check webOS CLI configuration and permissions.' >&2
    exit 1
  fi
fi
# The CLI prompts for the passphrase and saves the SSH key and passphrase itself.
ares-novacom -d "$DEVICE" --getkey
reply=$(ares-novacom -d "$DEVICE" --run 'echo CYTV_SSH_OK')
[[ "$reply" == *CYTV_SSH_OK* ]] || { echo 'SSH connection was not confirmed.' >&2; exit 1; }
tv_node=$(ares-novacom -d "$DEVICE" --run '/usr/bin/node -p "process.versions.node"')
python3 - "$tv_node" <<'PY'
import re, sys
# CLI 3.x writes informational banners to stdout alongside the remote result.
version = '\n'.join(line for line in sys.argv[1].splitlines() if not line.startswith('[Info]')).strip()
if not re.fullmatch(r'\d+\.\d+\.\d+', version) or tuple(map(int, version.split('.'))) < (0, 10, 25):
    raise SystemExit('Home Helper requires TV Node.js 0.10.25 or newer. Installation has not started.')
PY
# Generated icons/directories and native executables must be readable/traversable
# by the TV runtime after packaging. Pairing keys enforce their own private modes.
umask 022
stage='reading the TV app list'
printf '\nAccept the remote-control pairing request on the TV if shown.\n'
python3 sync-apps.py "$TV_HOST"
python3 - <<'PY'
import json
from pathlib import Path
s=Path('launcher/apps.js').read_text()
apps=json.loads(s[s.index('{'):].rstrip().rstrip(';'))['apps']
if not apps: raise SystemExit('No apps were synced. Check TV pairing and icon-download errors before retrying.')
PY
stage='building packages'
bash scripts/build.sh
# Use metadata rather than version globs: never install a stale release from dist/.
launcher=$(python3 -c 'import json; a=json.load(open("launcher/appinfo.json")); print("dist/"+a["id"]+"_"+a["version"]+"_all.ipk")')
helper=$(python3 -c 'import json; a=json.load(open("native/app/appinfo.json")); print("dist/"+a["id"]+"_"+a["version"]+"_arm.ipk")')
[[ -s "$launcher" && -s "$helper" ]] || { echo 'Build did not produce both packages.' >&2; exit 1; }
stage='installing packages'
ares-install -d "$DEVICE" "$helper"
ares-install -d "$DEVICE" "$launcher"
stage='configuring Home Helper'
bash scripts/configure-tv.sh
stage='starting Home Helper'
ares-launch -d "$DEVICE" -p '{"nativeHomeStart":true}' com.local.nativehome
printf '\nPackages installed and helper launch requested. Check the TV now:\n'
printf '  Open an app, then press Home to return to your launcher.\n'
printf '  Hold Home for about 2 seconds to stop the helper and return to LG Home.\n'
printf '  Test arrows, OK, volume, standby/wake and cold boot.\n'
printf 'Keep Developer Mode active. Your computer can be switched off during everyday use.\n'

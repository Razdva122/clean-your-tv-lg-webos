#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Keep Python fixtures, builders and Node-spawned checks in the same host environment.
# An explicit interpreter wins; otherwise reuse the active or project virtualenv.
if [[ -z "${PYTHON:-}" ]]; then
  for environment in "${VIRTUAL_ENV:-}" "$PWD/.venv-cytv" "$PWD/.venv"; do
    [[ -n "$environment" ]] || continue
    for candidate in "$environment/bin/python3" "$environment/Scripts/python.exe"; do
      if [[ -x "$candidate" ]]; then PYTHON="$candidate"; break 2; fi
    done
  done
  : "${PYTHON:=python3}"
fi
export PYTHON
export CYTV_PYTHON="${CYTV_PYTHON:-$PYTHON}"
if [[ "$PYTHON" == */* ]]; then export PATH="$(dirname "$PYTHON"):$PATH"; fi
# Consume reporting configuration here; nested profile tests must not inherit it
# or overwrite the outer suite's report in the same directory.
test_timings_directory="${CI_TEST_TIMINGS_DIR:-}"
unset CI_TEST_TIMINGS_DIR
# Shards run in separate CI checkouts; never export this selection to child tests.
shard=""
shard_index=1
shard_count=1
if [[ "${1:-}" == --shard ]]; then
  shard="${2:-}"
  if [[ ! "$shard" =~ ^[1-9][0-9]{0,2}/[1-9][0-9]{0,2}$ ]] || (( ${shard%/*} > ${shard#*/} )); then
    echo "Invalid shard: $shard (expected INDEX/COUNT, 1 <= INDEX <= COUNT <= 999)" >&2
    exit 2
  fi
  shard_index="${shard%/*}"
  shard_count="${shard#*/}"
  shift 2
fi
primary() { [[ "$shard_index" == 1 ]]; }
# Serial blocks run once across the matrix; smaller local matrices fold their
# owners modulo the shard count. Unsharded execution retains every block/order.
on_shard() { [[ -z "$shard" ]] || (( shard_index == ($1 - 1) % shard_count + 1 )); }
python_suite() {
  if [[ "$1" == tests/cytv && -n "$test_timings_directory" ]]; then
    "$PYTHON" scripts/test-shard.py --shard "${shard:-1/1}" -s "$1" --timings "$test_timings_directory/cytv.json"
  elif [[ -n "$shard" ]]; then
    "$PYTHON" scripts/test-shard.py --shard "$shard" -s "$1"
  else
    "$PYTHON" -m unittest discover -s "$1"
  fi
}
# No arguments runs the full suite (local checks and release validation).
selected=" ${*:-ui tv installer android setup preview} "
for component in "$@"; do
  case "$component" in ui|tv|tv-runtime|installer|android|setup|preview) ;; *) echo "Unknown test component: $component" >&2; exit 2 ;; esac
done
has() { [[ "$selected" == *" $1 "* ]]; }

if primary && { has ui || has tv; }; then
  node tests/themes/storage-budget.cjs
  node tests/home-viewport.cjs
  node tests/home-presentation.cjs
  node tests/noroot-presentation-context.cjs
  node tests/themes/presentation.cjs
  npm run test:compat
  npm run lint:compat
  npm run test:themes
  npm run test:weather
  for test in root-edition/ui/test-*.cjs; do
    if [[ "$test" != *"-browser.cjs" ]]; then node "$test"; fi
  done
  for file in root-edition/ui/*.js; do node --check "$file"; done
fi

if has tv || has tv-runtime; then
if on_shard 2; then
node tests/helper-compat.cjs
node tests/tv-service-compat.cjs
node tests/passive-remote-diagnostic.cjs
node tests/helper-panel-diagnostics.cjs
for test in tests/apps/*.cjs; do
  if [[ "$test" != *"/ui.cjs" ]]; then node "$test"; fi
done
for test in tests/i18n/*.cjs; do
  if [[ "$test" != *"/browser.cjs" ]]; then node "$test"; fi
done
node tests/renewal-core.cjs
node tests/renewal-transport.cjs
node tests/tls-ca.cjs
node tests/renewal-manager.cjs
node tests/renewal-storage.cjs
node tests/renewal-diagnostics.cjs
node tests/settings-diagnostics.cjs
node tests/helper-entry.cjs
node tests/helper-service-status.cjs
node tests/helper-published-ui.cjs
node tests/home-control.cjs
node tests/home-control-bridge.cjs
node tests/home-control-jail.cjs
node tests/resume.cjs
node tests/controller-resume.cjs
node --test tests/controller-resume-home.cjs tests/controller-watchdog.cjs
node tests/controller-home.cjs
node tests/controller-ir-home.cjs
for test in native/prototype/test-*.cjs; do node "$test"; done
"$PYTHON" -m unittest discover -s tests -p test_stop_fs.py
"$PYTHON" -m unittest discover -s tests -p 'test_private*.py'
mkdir -p build/tests
cc -std=c99 -Wall -Wextra -Werror native/prototype/filter.c native/prototype/test_filter.c -o build/tests/test-filter
cc -std=c99 -Wall -Wextra -Werror native/prototype/test_startup.c -o build/tests/test-startup
build/tests/test-startup
cc -std=c99 -Wall -Wextra -Werror native/prototype/test_relay_startup.c native/prototype/filter.c -o build/tests/test-relay-startup
build/tests/test-relay-startup > build/tests/relay-startup.log
tail -1 build/tests/relay-startup.log
cc -std=c99 -Wall -Wextra -Werror native/prototype/test_relay_watchdog.c native/prototype/filter.c -o build/tests/test-relay-watchdog
build/tests/test-relay-watchdog > build/tests/relay-watchdog.log
tail -1 build/tests/relay-watchdog.log
cc -std=c99 -Wall -Wextra -Werror native/prototype/test_relay_ir.c native/prototype/filter.c -o build/tests/test-relay-ir
build/tests/test-relay-ir
for scenario in off-on overflow-taps overflow-press overflow-emergency; do
  build/tests/test-relay-ir "$scenario"
done
build/tests/test-filter
for file in launcher/*.js native/app/*.js native/service/*.js renewal-service/*.js; do node --check "$file"; done
fi

if on_shard 3; then
"$PYTHON" tests/root-node-compat.py
"$PYTHON" tests/root-node-compat.py --beta
fi
if on_shard 2; then
node root-edition/service/test-c1-filter.cjs
node root-edition/service/test-c1-lease.cjs
node root-edition/service/test-audio-recovery.cjs
node root-edition/service/test-handlers.js
node root-edition/service/test-startup.cjs
node root-edition/service/test-persistent.js
node root-edition/service/test-presentation.cjs
node root-edition/service/test-python-binding.js
for test in root-edition/tests/test_update_*.cjs; do node "$test"; done
for file in root-edition/updater/*.js; do node --check "$file"; done
fi
python_suite root-edition/tests
if on_shard 4; then

for test in tests/updates/*.cjs; do node "$test"; done
for test in tests/system_updates/*.cjs; do node "$test"; done
"$PYTHON" -m unittest discover -s tests/system_updates
for file in updater-service/*.js updater-app/*.js; do node --check "$file"; done
cmp launcher/user-data.js updater-service/user-data.js
fi
fi

if has setup; then
  python_suite tests/setup
fi
if has installer; then
  if on_shard 2; then
  "$PYTHON" -m unittest discover -s homebrew/tests -p test_payload.py
  node homebrew/tests/runtime.cjs
  node homebrew/tests/bridge.cjs
  node homebrew/tests/ui.cjs
  "$PYTHON" -m unittest discover -s homebrew/tests -p 'test_installer*.py'
  "$PYTHON" -m unittest discover -s homebrew/tests -p test_continuation.py
  fi
  python_suite tests/cytv
fi
if primary && has android; then
  "$PYTHON" -m unittest discover -s android/tests
fi
if on_shard 2 && has preview; then
  node tests/home-presentation-ui.cjs
  node tests/root-decoder-ui.cjs
  node tests/preview-presentation-ui.cjs
  node tests/themes/ribbon-reference-ui.cjs
  node tests/themes/ribbon-edit-ui.cjs
  for test in tests/showcase/{registry,submission-security,remote}.cjs; do node "$test"; done
  node tests/preview-bridge.cjs
  node tests/preview-themes-ui.cjs
  "$PYTHON" -m unittest discover -s tests -p test_preview.py
fi

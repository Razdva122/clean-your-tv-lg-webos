#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# No arguments runs the full suite (local checks and release validation).
selected=" ${*:-ui tv installer android setup preview} "
for component in "$@"; do
  case "$component" in ui|tv|installer|android|setup|preview) ;; *) echo "Unknown test component: $component" >&2; exit 2 ;; esac
done
has() { [[ "$selected" == *" $1 "* ]]; }

if has ui || has tv; then
  npm run test:compat
  npm run lint:compat
  npm run test:themes
  for test in root-edition/ui/test-*.cjs; do
    if [[ "$test" != *"-browser.cjs" ]]; then node "$test"; fi
  done
  for file in root-edition/ui/*.js; do node --check "$file"; done
fi

if has tv; then
node tests/helper-compat.cjs
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
for test in native/prototype/test-*.cjs; do node "$test"; done
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
build/tests/test-filter
for file in launcher/*.js native/app/*.js native/service/*.js renewal-service/*.js; do node --check "$file"; done

python3 tests/root-node-compat.py
node root-edition/service/test-audio-recovery.cjs
node root-edition/service/test-handlers.js
node root-edition/service/test-persistent.js
node root-edition/service/test-python-binding.js
for test in root-edition/tests/test_update_*.cjs; do node "$test"; done
for file in root-edition/updater/*.js; do node --check "$file"; done
python3 -m unittest discover -s root-edition/tests

for test in tests/updates/*.cjs; do node "$test"; done
for test in tests/system_updates/*.cjs; do node "$test"; done
python3 -m unittest discover -s tests/system_updates
for file in updater-service/*.js updater-app/*.js; do node --check "$file"; done
cmp launcher/user-data.js updater-service/user-data.js
fi

if has setup; then
  python3 -m unittest discover -s tests/setup
fi
if has installer; then
  python3 -m unittest discover -s homebrew/tests -p test_payload.py
  node homebrew/tests/runtime.cjs
  node homebrew/tests/bridge.cjs
  node homebrew/tests/ui.cjs
  python3 -m unittest discover -s homebrew/tests -p 'test_installer*.py'
  python3 -m unittest discover -s homebrew/tests -p test_continuation.py
  python3 -m unittest discover -s tests/cytv
fi
if has android; then
  python3 -m unittest discover -s android/tests
fi
if has preview; then
  for test in tests/showcase/{registry,submission-security,site,remote}.cjs; do node "$test"; done
  node tests/preview-bridge.cjs
  node tests/preview-themes-ui.cjs
  python3 -m unittest discover -s tests -p test_preview.py
fi

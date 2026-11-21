#!/bin/sh
# Offline container fixture: /stock is an extracted factory rootfs. Run with
# dbus-run-session -- sh /project/root-edition/tests/embedded-home-upstart.sh.
set -eu
export LC_ALL=C LANG=C
fixture=$(mktemp -d)
mkdir "$fixture/jobs"
cat >"$fixture/jobs/surface-manager.conf" <<EOF
description "Offline launch-environment fixture"
respawn
exec /bin/sh -c 'echo "\${LSM_MAIN_QML-unset}" > $fixture/observed; exec sleep 60'
EOF
stock() {
    qemu-arm -L /stock -E LC_ALL=C -E LANG=C \
        -E LD_LIBRARY_PATH=/stock/lib:/stock/usr/lib "$@"
}
stock /stock/sbin/init.upstart --session --no-startup-event --no-sessions \
    --no-log --confdir="$fixture/jobs" >"$fixture/init.log" 2>&1 &
manager=$!
trap 'kill "$manager" 2>/dev/null || true; rm -rf "$fixture"' EXIT
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if stock /stock/sbin/initctl --session list >/dev/null 2>&1; then break; fi
    sleep .1
done
stock /stock/sbin/initctl --session start surface-manager LSM_MAIN_QML=file:///fixture/wrapper.qml
test "$(cat "$fixture/observed")" = file:///fixture/wrapper.qml
stock /stock/sbin/initctl --session stop surface-manager
stock /stock/sbin/initctl --session start surface-manager
test "$(cat "$fixture/observed")" = unset
stock /stock/sbin/initctl --session stop surface-manager
printf '%s\n' 'Per-launch QML environment was discarded on ordinary restart'

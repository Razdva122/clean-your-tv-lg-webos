#!/bin/sh
# The container provides QEMU/GDB, /stock factory rootfs and /image EPK partitions.
set -eu
ulimit -c 0
printf '%s  %s\n' 3436252e8f41b1a853d71c52105b84cefbb0f8d447aba68fa1af7cd30df10199 /stock/usr/bin/surface-manager-starfish | sha256sum -c
mkdir /tmp/probe-markers
success='controller-sigkill-eof tagged-subscription adapter-attached home-intercepted stock-pair-delivered stock-home-visible'
failure='bridge-failed kill-failed subscription-invalid home-request-invalid attach-failed intercept-failed fallback-failed stock-home-hidden stock-load-failed'
for marker in $success $failure; do
    printf '%s\n' 'import QtQuick 2.4' 'Item {}' >"/tmp/probe-markers/$marker.qml"
done
unsquashfs -no-progress -d /tmp/bsp /image/bsppart.pak bsp/usr/lib >/dev/null
mkdir -m 700 /tmp/qt
export WEBOS_COMPOSITOR_EXTENSIONS=webos-extension LC_ALL=C LANG=C LOCPATH=/stock/usr/lib/locale
mkdir -p /var/run/ls2 /var/log /tmp/var/log /etc/luna-service2
ln -s /var/run/ls2 /var/run/luna-service2
cp /usr/bin/qemu-arm /tmp/w17m-qemu-compositor
cp -R /stock/usr/share/ls2 /tmp/ls2
sed -i 's@/usr/bin/surface-manager-starfish@/tmp/w17m-qemu-compositor@g' /tmp/ls2/roles/pub/com.webos.surfacemanager.json /tmp/ls2/roles/prv/com.webos.surfacemanager.json
sed -e 's@/usr/share/luna-service2@/stock/usr/share/luna-service2@g' -e 's@/usr/share/ls2@/tmp/ls2@g' -e 's@/usr/share/dbus-1@/stock/usr/share/dbus-1@g' /stock/etc/luna-service2/ls-hubd.conf >/tmp/hub.conf
python3 /project/root-edition/tests/embedded-home-controller.py >/tmp/controller.log 2>&1 &
controller=$!
qemu-arm -L /stock -E LD_LIBRARY_PATH=/stock/lib:/stock/usr/lib /stock/usr/sbin/ls-hubd -c /tmp/hub.conf >/tmp/hub.log 2>&1 &
hub=$!
trap 'kill "$controller" "$hub" 2>/dev/null || true' EXIT
for retry in 1 2 3 4 5; do
    [ -S /var/run/ls2/com.palm.hub ] && break
    sleep 0.2
done
/tmp/w17m-qemu-compositor -g 12345 -d strace -D /tmp/arm.log -L /stock -E LD_LIBRARY_PATH=/stock/lib:/stock/usr/lib:/tmp/bsp/bsp/usr/lib -E QT_PLUGIN_PATH=/stock/usr/lib/qt5/plugins -E QML2_IMPORT_PATH=/stock/usr/lib/qt5/qml -E XDG_RUNTIME_DIR=/tmp/qt -E LSM_MAIN_QML=file:///project/root-edition/tests/embedded-home-native.qml /stock/usr/bin/surface-manager-starfish -platform minimal >/tmp/guest 2>&1 &
guest=$!
trap 'kill "$controller" "$guest" "$hub" 2>/dev/null || true' EXIT
# The checked factory instruction is QWindow::show. Skip display creation for
# the parentless stock object test, while keeping native Qt and QML execution.
cat >/tmp/probe.gdb <<'GDB'
set pagination off
set confirm off
set sysroot /stock
set solib-search-path /stock/lib:/stock/usr/lib:/tmp/bsp/bsp/usr/lib
handle SIGILL nostop noprint pass
target remote :12345
set arm force-mode thumb
break *0xc302
commands
silent
set $pc = 0xc306
continue
end
continue
thread apply all bt 10
GDB
timeout 18 gdb-multiarch -nx -batch /stock/usr/bin/surface-manager-starfish -x /tmp/probe.gdb >/tmp/gdb.log 2>&1 || true
failed=0
if ! grep -q 'wait returned -9 and CONTROL pipe reached EOF' /tmp/controller.log; then failed=1; fi
for marker in $success; do
    if grep -F "open(\"/tmp/probe-markers/$marker.qml\"," /tmp/arm.log | grep -Eq ' = [0-9]+$'; then
        printf '%s\n' "$marker"
    else
        printf 'Missing marker %s\n' "$marker" >&2
        failed=1
    fi
done
for marker in $failure; do
    if grep -Fq "open(\"/tmp/probe-markers/$marker.qml\"," /tmp/arm.log; then
        printf 'Unexpected marker %s\n' "$marker" >&2
        failed=1
    fi
done
if grep -q 'received signal SIG' /tmp/gdb.log; then failed=1; fi
if [ "$failed" -ne 0 ]; then
    grep -E 'open\("/tmp/probe-markers/(request|response)' /tmp/arm.log | tail -12 >&2
    tail -35 /tmp/gdb.log >&2
    cat /tmp/controller.log >&2
    tail -35 /tmp/guest >&2
fi
cat /tmp/controller.log
exit "$failed"

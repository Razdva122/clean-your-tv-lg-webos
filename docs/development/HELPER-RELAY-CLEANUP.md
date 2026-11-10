# Helper relay cleanup outcomes

This describes the relay cleanup behavior included in released Helper packages. It does not establish target input, firmware or cold-boot acceptance. Use the matching versioned package; older installed Helpers retain their original behavior.

On leaving its input loop, the relay attempts key-up cleanup, removal of the
physical input grab, and closure of both input/output descriptors. A failure in
one step does not skip the remaining steps. Successful cleanup retains the
original exit reason, including watchdog 20, emergency 27 and source removal 25.

If any cleanup step fails, the relay attempts to report
`CLEANUP_FAILED MASK CAUSE ORIGINAL_REASON`, then `EXIT 31`, and returns 31.
An unavailable output channel can prevent these diagnostic lines; it does not
skip cleanup or change the cleanup-failure exit code.
The mask combines key-up query/write 1, ungrab 2, input close 4 and output close 8.
Source removal 25 normally has no blocked marker; a cleanup failure on that path
also requests the existing blocked marker. Existing watchdog/emergency latches
are retained. The marker writes keep their existing best-effort behavior; this
change does not turn them into durable receipts.

The controller treats 30 and 31 as non-watchdog failures and blocks automatic recovery.
It still runs its existing separate cleanup after the tracked relay closes when
required. The standalone `relay cleanup` command returns 11 for a failed key-up
operation or output close. Neither successful cleanup submission nor exit text
alone proves a process has closed: consumers must await the actual child close
and stdio drain. These I/O results also do not certify a physical remote, the
absence of other input holders, or the future broker/relay lease lifetime.

Controller pipe/socket output is nonblocking. Each bounded control record must
be delivered completely; output setup/write failure returns 30 and requests the
existing blocked latch. After grabbing input, failed delivery goes through all
key-up/ungrab/close attempts. Cleanup failure 31 still takes precedence. A failed
final exit report also blocks watchdog retry. Healthy message text is unchanged.
Terminal and regular-file flags are unchanged; this bounded-output guarantee is
for the pipe/socket used by the controller. Marker writes remain best effort.

Standalone `relay cleanup` attempts key release and output close even if stdout
is closed or its setup fails; its device-cleanup result remains 0 or 11.

The synthetic evdev harness executes the actual relay source. It covers normal
exit reasons, single/combined cleanup faults, standalone cleanup, real full
controller pipes, EPIPE and closed stdout. Controller tests check that 30 and 31
remain blocked. No actual TV input is exercised by these HOST checks. Run:

```sh
mkdir -p build/tests
cc -std=c99 -Wall -Wextra -Werror native/prototype/test_relay_watchdog.c \
  native/prototype/filter.c -o build/tests/test-relay-watchdog
build/tests/test-relay-watchdog
node --test tests/controller-watchdog.cjs
```

The unchanged startup/filter regressions and final packaged-TV controls, sound,
emergency release and recovery checks remain required. No Home authentication,
storage provisioning, protection reset or new input authority is added here.

## Power-transition source removal (#487, unpublished)

The source fix adds a narrow exit 32, distinct from cleanup failure 31. The
controller sends `T` on a recognized power-off/standby/suspend transition and `R`
on Active. The relay retains this hint through its pre-grab startup pump; it
expires after 15 monotonic seconds. It still attempts every cleanup operation.
Only source-removal reason 25, cleanup mask 3, ENODEV/ENXIO from both key release
and ungrab, successful descriptor closes, and a live hint can produce
`POWER_REMOVED RELEASE_ERRNO UNGRAB_ERRNO` followed by `EXIT 32`. Stop/Q or a
handled termination signal wins, including a signal during cleanup. Other
errors remain persistent failures; output/report failure still blocks.

The controller accepts this outcome only for its tracked child, with matching
reported/actual exit 32, no signal, a recent hint and no stop/blocked/watchdog
state. It keeps its power watcher and timer alive without reopening input while
asleep. Fresh settled Active schedules one relay start after 1.5 seconds;
renewed power-off or processing cancels it. Stop and both latches are checked
again before starting. A new relay preserves Home Off, and enabled Home uses the
existing guarded wake presentation. A real reboot uses the normal bootstrap.
No latch is cleared by this path, and ordinary watchdog retry limits are unchanged.
Pre-grab validation failures retain their existing fail-closed behavior.

These are synthetic host checks, including same-boot wake, pre-READY power
hints, renewed shutdown, Stop/HUP races and SIGTERM during cleanup. Actual device
errno values and the final packaged transition remain unverified. The fix needs
a newly selected Helper version built from source with its matching relay and
controller, plus rebuilt embedded installers; published Helper bytes remain
immutable. See the [verification ledger](../history/2026-11-10-issue487-helper-recovery.md).

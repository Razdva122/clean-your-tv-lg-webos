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

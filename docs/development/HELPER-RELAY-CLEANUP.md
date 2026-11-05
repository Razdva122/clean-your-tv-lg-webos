# Helper relay cleanup outcomes

This describes the next unpublished Helper source. It does not establish target
input, firmware or cold-boot acceptance. Helper source changes require a rebuilt,
versioned package; the unchanged published Helper package does not contain them.

On leaving its input loop, the relay attempts key-up cleanup, removal of the
physical input grab, and closure of both input/output descriptors. A failure in
one step does not skip the remaining steps. Successful cleanup retains the
original exit reason, including watchdog 20, emergency 27 and source removal 25.

If any cleanup step fails, the relay prints
`CLEANUP_FAILED MASK CAUSE ORIGINAL_REASON`, then `EXIT 31`, and returns 31.
The mask combines key-up query/write 1, ungrab 2, input close 4 and output close 8.
Source removal 25 normally has no blocked marker; a cleanup failure on that path
also requests the existing blocked marker. Existing watchdog/emergency latches
are retained. The marker writes keep their existing best-effort behavior; this
change does not turn them into durable receipts.

The controller treats 31 as a non-watchdog failure and blocks automatic recovery.
It still runs its existing separate cleanup after the tracked relay closes when
required. The standalone `relay cleanup` command returns 11 for a failed key-up
operation or output close. Neither successful cleanup submission nor exit text
alone proves a process has closed: consumers must await the actual child close
and stdio drain. These I/O results also do not certify a physical remote, the
absence of other input holders, or the future broker/relay lease lifetime.

The existing synthetic evdev harness executes the actual relay source. Its 38
scenarios cover four normal exit paths, each of seven single/combined cleanup
faults on those paths, and six standalone cleanup outcomes. Controller tests
check that 31 remains blocked. Run:

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

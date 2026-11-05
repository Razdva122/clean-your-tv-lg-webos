# Unwired native pipe bridge

This increment is a HOST-only bridge foundation. The fixed C broker owns the
actual controller lease for its process lifetime; Node receives no lease token or
numeric FD authority. Production trusted binding/provisioning is absent and must
fail closed. Only an explicit HOST test build may embed pins from a fixture that
the trusted test harness created. No environment, request, or admitted inode may
supply production trust. No consumers, bootstrap/detach, build wiring or TV change.

Ordinary C operation failure (UNKNOWN/FULL/OVERFLOW/BUSY) rejects that operation
without cancelling a live transaction. After failed APPEND returns, ES5 may issue
a full recovery READ under the same lease. Transport/scope failure (malformed or
unexpected frame, lost pipe, timeout, explicit cancellation) immediately disables
admission and fences late results. It never permits recovery or automatic replay.
EOF lets synchronous C work finish, then closes tx/lease. Outer completion waits
for actual child close including stdio drain; a timer is not proof of release.

One command is outstanding, with no hidden queue. The 16-byte header is CYI1,
opcode/status/reserved-zero bytes, a big-endian uint32 request ID and payload
length. Startup uses ID0; commands use increasing nonzero IDs without wrap.
Correlation IDs reject late duplicate replies, not authenticate callers. Requests
are bounded at16384+64 bytes and responses at1MiB+4096 bytes. Stderr is discarded
with a4096-byte lifetime cap. No unbounded string accumulation or shell execution.

withControllerTransaction invokes its callback after BEGIN_ACK. It waits for the
callback Promise and all submitted native IO, then END_ACK before completion.
Callback completion while its IO remains pending is rejected after drain/END;
no late effect can become a successful callback result. Stale tx methods reject.
The broker retains exclusion between transactions until CLOSE/process exit.

Private READ preserves exact valid UTF-8/no-NUL bytes; JS JSON/schema/hash-chain
validation remains separate. APPEND receipts must match immutable requested raw
bytes, sequence and SHA256 computed from C-verified readback. Shared Stop remains
strictly canonical. Independent publication uses another instance and no private
lease. Its ACK establishes only its own verified publication.

Stage checkpoints: first READY/BEGIN/READ/END/CLOSE plus actual child lease tests;
focused review; then APPEND/SCAN/publisher/cancellation and real blocked-C/cut
cases. No stage supplies Home authority, provisioning, target pipe behavior,
reboot persistence, input/key-up safety or delivery integrity.

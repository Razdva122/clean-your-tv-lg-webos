# Unwired native pipe bridge

This increment is a HOST-only bridge. The fixed C broker owns the
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
length. Startup uses ID 0; commands use increasing nonzero IDs without wrap.
Correlation IDs reject late duplicate replies; they do not authenticate callers.
Requests are bounded at 16384+64 bytes and responses at 1 MiB+4096 bytes. Stderr is
discarded with a 4096-byte lifetime cap. No unbounded string accumulation or shell
execution. Caller raw strings are bounded by character and UTF-8 byte length
before copying. Request properties are captured once; the pending APPEND intent
retains its own raw bytes, sequence and hash. Backpressure must drain before a
reply settles the command. The 10-second deadline disables admission and queues
EOF, but cannot settle the outer transaction before actual child close.

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

Both implementation checkpoints are present: READY/BEGIN/READ/END/CLOSE, followed
by APPEND/SCAN/publisher/cancellation and actual blocked-C/cut cases. Every new
publisher gets a fresh 128-bit cryptographic nonce and its own process; Node
waits for its validated ACK and successful process close. No stage supplies Home
authority, provisioning, target pipe behavior, reboot persistence, input/key-up
safety or delivery integrity. Production bindings remain absent: compiling the
broker does not enable it on a TV.

## Wire operations

All integers below are unsigned 32-bit big-endian. Header bytes 0–3 are the exact
ASCII bytes CYI1, byte 4 is opcode, byte 5 status, bytes 6–7 zero, bytes 8–11
request ID, and bytes 12–15 body length. Requests have status zero. Responses use
the private status enum: OK 0, UNKNOWN 1, BUSY 2, FULL 3, OVERFLOW 4.

| Opcode | Request | Successful response |
| --- | --- | --- |
| READY 0 | Unsolicited startup, ID 0 | Empty, after actual lease acquisition |
| BEGIN 1 | Empty | Empty, after transaction begin |
| READ 2 | Empty | Count, then `(sequence, byte length, exact raw)` per entry |
| SCAN 3 | Empty | Count, then 32 ASCII hex bytes per Stop ID |
| APPEND 4 | Sequence, then raw UTF-8 bytes | Sequence, byte length, verified raw |
| END 5 | Empty | Empty, after transaction end |
| CLOSE 6 | Empty, outside a transaction | Empty, after lease close |
| PUBLISH 7 | Separate process mode and nonce argument; response ID 0 | Its 32 ASCII hex nonce bytes |

Negative operation replies have no body, except SCAN FULL carries the complete
16-record snapshot. READ accepts 1–64 consecutive entries, each 1–16384 bytes;
APPEND permits sequences 1–63 and raw of 1–16384 bytes. SCAN accepts up to 16
distinct lowercase hex IDs. Invalid magic, reserved bytes, ID, opcode, lengths,
UTF-8, NUL, duplicate/trailing replies or mismatched receipts close admission.
No resynchronization or replay is attempted.

## HOST verification

Run `node native/prototype/test-stop-io.cjs` on a host with a C11 compiler and the
repository's compiler dependencies installed. Set `NODE010`, `NODE01025` and
`NODE012` to the three historical runtime executables to repeat the same actual
child-process cases. The harness compiles the fixed broker, frozen C primitives,
and Node adapter; only the generated HOST artifact substitutes the executable
literal. There is no production executable/path/provider option.

The standalone suite has 41 cases. If `native/app/stop-journal.js` exists, or
`CYTV_STOP_JOURNAL_FIXTURE` explicitly names its preserved HOST fixture, two more
cases exercise the unchanged ES5 protocol through the actual C broker. The frozen
fixture used for stage 2 is commit `398630aa6b12a36325e25aad56753839e4917f11`,
source SHA-256 `240187c4ed8515c52c72efea490ce47b9743cb778a956cefb6c04e8a8a7b6833`.
It adopts an actual published Stop and turns an unacknowledged durable prepare
into blocked without commit. Home authorization remains UNIMPLEMENTED and
physical stop remains UNTESTED.

The HOST-only hook pauses actual C APPEND work, injects fsync failure or process
exit before ACK, and corrupts actual pipe responses. Cancellation tests prove
that outer completion stays pending and a second controller remains BUSY while
the native operation is paused, while the independent publisher succeeds. Hook
controls and fixture binding headers are excluded from production builds.

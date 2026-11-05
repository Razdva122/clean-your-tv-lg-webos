# Unwired ES5 Stop journal protocol

This is a protocol foundation, not a working Helper or a native I/O/lease proof.
Frozen HOST reference: V2 scope `5d5aabf29444098053f4c3c8d18a9c29d4682b7b1f0b81f4a56f0cd84cf7d778`,
model SHA256 `a98124b183bea25188d00afa9115638b47468c649845289999ddeb99c07b9517`.
No Python runtime, raw filesystem fallback, process spawning, permissions,
provisioning, migration or consumers are added. The credential guard is unchanged.

`native/prototype/stop-journal.js` exports Promise-based poll, input-gate,
requestHomeStart and independent publishStop operations. The unwired default
has no I/O or Home authority and denies. `requestHomeStart` never interprets
`authorized`, nativeHomeStart, auto or tile flags. Only the internal HOST fixture
factory supplies a trusted authority callback returning a fresh replay intent;
that callback is not real authentication. Prepared intents are never replayed.

## Required future native adapter

No adapter implementing this contract is included. Its function name or a
boolean cannot prove a controller lease. Production integration remains blocked
on a reviewed native capability that owns the checked lease and serializes ALL
private operations across instances/processes. There is no boolean lease option.

- `io.withControllerTransaction(callback)` must invoke callback exactly once only
  under a checked native controller lease, retain it through the returned Promise,
  and release afterward. Synchronous try/finally around callback is insufficient:
  release must await Promise fulfillment/rejection. Its tx methods must reject
  after lease loss. The port also denies overlapping operations on one instance, missing/boolean tx,
  premature completion, and callbacks arriving after completion. Private calls and
  their results are fenced against a closed logical scope, so a late prepare ACK
  cannot continue to commit after transaction loss. This is not OS lease proof.
- `tx.readJournal()` returns `{status:"snapshot",records:[{name,raw}]}` only after
  checked private0700/0600 metadata/FD/path checks and fresh file+directory fsync.
  At most64 exact consecutive entry names, each <=16KiB UTF-8, may be returned.
  Missing, staging, corrupt, unsafe, overflow or unconfirmed durability must fail;
  they may never be represented as a newly initialized or partial snapshot.
  Private serialization follows frozen V2: JSON schema and the hash of the EXACT
  raw bytes are checked, not raw===encode(parsed). Whitespace/key order and
  duplicate-key last-value parsing are accepted by V2/Python and this reader.
  Own writes use encode(). Canonical-only private reads would be a new stricter
  format/scope; they must not be silently assumed from shared Stop validation.
- `tx.scanStops()` returns `{status:"snapshot",ids:[...]}` only for a complete
  checked non-secret Stop set of <=16 distinct32-hex IDs. Native scan must stop
  at the17th name and report overflow before unbounded record reads. Pending,
  corrupt, unsafe or unavailable observations fail closed; no partial success.
  Raw metadata/canonical bytes and external producer UID/GID pins are the native
  adapter's responsibility, including V2's narrow0640/0777 Stop-only rule.
  Shared Stop bytes MUST be canonical and match the filename ID; the private
  serialization compatibility above does not relax this ingress check.
- `tx.appendPrivate({seq,raw,sha256})` derives its fixed entry pathname internally;
  no path is supplied. It must exclusively create an owned0600 entry under the
  same checked private bindings, verify bytes/identity, fsync file then directory,
  and return exactly `{status:"durable",seq,sha256}` for those bytes. Unknown or
  failed outcomes must not be guessed/retried as Start. Recovery only reloads a
  valid synced journal and attempts a blocked decision, never prepare-to-commit.
- Independent `io.publishStop()` needs no controller transaction. Only after its
  own fresh O_EXCL nonce/FD/path/canonical bytes and file+directory durability
  checks may it return `{status:"durable",id}`. No shared publisher lock or global
  channel-health claim. Concurrent publishers may produce overflow, which blocks.

Fixed C command scope, syscall bounds and actual lease confinement remain
mandatory adapter work, not facts established by these JavaScript interfaces.

## Acknowledgments and host evidence

V2 booleans remain separate: blocked is a logical denial; durable_blocked needs
confirmed private durability; private_adopted requires the complete observed set.
Unknown fallback can be durably blocked but never adopted. Added `adopted_ids`
is a bounded copy of that exact durable observed set ONLY when adoption is true;
otherwise it is empty. It is not a global/per-request drain. A future consumer
must correlate its specific fresh published ID. Reusing a consumed ID cannot
create a new Stop. Physical Stop/key-up always remain UNTESTED.

The focused test uses the existing Helper Babel/core-js/safe-buffer compiler and
current plus exact Node0.10.15/0.10.25/0.12.2. Typed asynchronous HOST I/O models
cover private chains, capacity, snapshot mutation, replay, pending/corrupt/missing,
new Stop during prepare/commit, checked-transaction refusal, publication races,
receipt-ID copies and failed/recovered durability. The reference's16 syscall cut
locations map to8 protocol-visible partial-versus-valid-unacknowledged outcomes;
tests leave an operation unresolved and reopen the model. They are not actual
C I/O, process-kill, disk fsync, cross-UID, reboot or TV tests. Native metadata and
filesystem guards are not simulated away as production acceptance.

Verification: npm ci passed;70 cases passed on each of the four runtimes. The
initial missing-module test was RED. Added actual-flow tests then reproduced a
late private commit after premature transaction completion; scoped I/O checks
fixed it. A fixture expectation at capacity was corrected to match V2: a freshly
synced existing blocked state can still confirm durable blocking. Other inherited
characterization cases are not claimed to have failed first.

Run `node native/prototype/test-stop-journal.cjs`; set NODE010/NODE01025/NODE012
to include the exact runtimes. Existing native test glob already includes it.
Real authentication, native journal/lease adapter, all control/Stop/credential
consumers, installer/updater migration and final device acceptance remain pending.

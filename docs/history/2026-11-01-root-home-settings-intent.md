# Root Settings and update intent investigation — 2026-11-01

Scope: #206 and the retained-rollback boundary of #202. Host simulations use
synthetic LS2, package and input/route IO. No TV was contacted; no new installed
package, physical control/audio/power result or public delivery is claimed.
#171 standby remains a separate unresolved scenario.

## Settings (#206)

The actual Settings module cached `active` across an external emergency stop and
visibility/relaunch. Its first subsequent click called Restore rather than Enable.
The regression failed with an extra restore before the change.

Each refresh now owns a generation. Hide, relaunch and close invalidate cached
status immediately; only the latest visible response permits a Home action.
Failed or malformed refresh exposes the existing localized **Check status** action.
It performs a read only request; enabling always needs a separate explicit click.
Audio/Firmware returns and failed one-time LG Home visits also refresh status.
Category navigation and retry retain usable focus.

The module harness covers delayed success, failure, malformed data, stale success
and failure, close/reopen, repeated lifecycle events, child dialogs, delayed failed
launch, explicit Off and a later explicit Enable. Chrome runs the actual launcher,
Settings, category navigation and Root exit with synthetic LS2, checking the first
mutation is Enable and a later Off is Restore. These checks do not establish TV
caller permissions or physical emergency acceptance. Published workaround guidance
is retained until verified delivery and exact-package device acceptance.

## Retained rollback (#202, partial)

The original System supervisor declares `rolling-back` before calling suspension.
Live package selection previously rejected that phase even when the complete
candidate remained installed. The real selector → `home_present(live)` → health
context regression failed before the change. That can revoke intent before the
update guard captures the owner's preference.

Existing live health may now observe only that still-committed candidate when:

- the original transaction records `resumeCycle=rollback`, `homeResumePhase=complete`
  and `rollbackAttempted=false`;
- every original component install has a successful terminal and every rollback
  evidence record is untouched;
- the current descriptor and its System writer match that candidate;
- the private candidate cache and the complete installed Root payload verify.

Normal `current` selection remains blocked; original worker/admission selection
is unchanged. This grants no activation or installer authority. As soon as rollback
suspension/mutation advances, the live exception ends. Unknown/failed terminals,
changed writer, absent/tampered installed payload or cache do not qualify.

The update guard now captures intent and restores LG routing **before** the
rollback anchor retargets package authority. An interrupted restore or anchor
cannot replay activation; retries remain conservative. Explicit cancellation
still wins, including while staging. No cancellation receipt is erased by these
changes; no new persistent schema, permission or endpoint is added.

## Forward upgrade remains unresolved (#202)

The frozen `main` and `execute` callables from published v1.5.2, commit
`142ca6a2eb5528a8d34f36fdd02d1a16c016e1fb`, reproduce both old automatic boot
fallbacks calling explicit Restore and cancelling an update ticket. Their test
fixture records the full original source digest. A delayed old callback can create
a cancellation before new infrastructure replaces it. Replaying the new boot
callback preserves the cancellation, as required.

This proves a causal mechanism, not the exact invocation on the reported C3.
Changing new runtime code cannot retract an old caller's cancellation safely.
The remaining prerequisite is a separately agreed, bounded owner-supervised
exact-package session identifying the callback entry/caller and phase relative to
Root app, updater and infrastructure replacement. Capture only fixed operation
classes, version/build identity and transaction-relative ordering; retain private
raw diagnostics. Then decide an authenticated transition protocol that preserves
owner Off, emergency and real fault authority. Do not clear the receipt, infer
health or force Home on. Forward automatic resume is not claimed fixed.

## Verification limits

The focused and UI/TV/browser results are recorded in the implementation PR.
The immutable-supervisor fixture retains original installer terminals, private
package authority and rollback staging; device route/input activation IO is
synthetic. Delayed health must not enable, and a completed receipt must not replay
activation on restart. Interrupted staging and concurrent Off have separate tests.

Signed forward update, retained rollback, controls/audio and explicit Off/emergency
persistence on exact finalized packages remain untested. No release candidate or
build selection was changed. Existing historical C3 failures remain failures.

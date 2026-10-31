# Root OTA compatibility with the published 1.3.0 supervisor

Issue #115 records the historical C3 failure. The guarded compatibility and
replacement preparation was delivered in 1.5.0; this reference does not change
immutable 1.4.0 or approve an individual retained operation. The C3 was still on
1.3.0 at the initial implementation checkpoint, not at the current release
checkpoint. Later device observations retain their exact artifact scope in
[1.5.0 acceptance](../RELEASE-1.5.0.md) and the
[unattended C3 record](../history/2026-10-30-unattended-c3-ui-proof.md).
New artifacts still require their own affected acceptance.

## Observed boundary

On OLED55C3RLA / firmware 43.21.71, the original System Updater offered signed
1.4.0, then aborted during downloading with `Infrastructure inventory changed;
computer migration required`. No component installation intent, submission or
terminal receipt was created. Root 0.4.0 / Root Updater 0.3.0 and all 24 runtime
hashes were unchanged. The owner confirmed LG Home and normal controls. The
aborted journal is retained; do not delete it or retry the incompatible release.

The independent supervisor pins executable destinations and a registration
contract at computer bootstrap. 1.4.0 added `runtime/audio_recovery.py` and
`service/audio-recovery.js` and extended Root LS2 grants. Valid signatures and a
matching supervisor protocol did not make that archive compatible. The install
rejection is intentional. Availability checking previously inspected only the
old baseline and could therefore offer an incompatible candidate.

## Compatible candidate layout

The candidate retains the exact managed destination inventory captured from the
published 1.3.0 payload. Audio implementation lives in the already managed
`runtime/cli.py` and `service/handlers.js`; workers use `cli.py audio worker`.
All audio policy, locks, cancellation, observer identity, pending-setting recovery
and root-only validation remain in force. Source consolidation adds no executable
destination and never changes an installed supervisor's private pins.

Audio RPC uses strictly validated payloads on the existing `status` and `enable`
methods. `status` can only read audio state; `enable` carries the explicit audio
configuration/recovery requests. No new LS2 grants are needed. The original Root
registration plan remains byte-identical to the public 1.3.0 contract, allowing
old registration repair to authenticate it after package replacement.

Newly provisioned supervisors inspect the signed candidate infrastructure before
returning an installable offer. Unknown files or package hashes disable Update
all; the UI explains that a computer migration is required. Existing independently
pinned supervisors are not replaced by this source change. They can consume the
compatible candidate because its layout and permission plan match their contract.

## Retained recovery and rollback

Original Root bundle/release metadata identifies the computer-provisioned
bootstrap. A completed System update refreshes private recovery hashes and the
Root Updater publication; it does not rewrite that original bundle. Computer
recovery therefore authenticates original metadata separately from current
executables. Changed runtime/support requires a finished, resumed, signed System
publication, verified current packages and exact cached infrastructure/proof bytes.
Pending, forged, missing or changed evidence remains blocked. Historical Root
0.4.0 and published 0.5.0 runtime layouts remain recognized. New immutable bundle
metadata declares the inline audio layout; it is not a new mutable preference.

The old supervisor also needs a narrowly scoped retained-rollback adapter. After
it publishes a completed update, its original package selector can reject the
last committed candidate descriptor while restoring the prior package. During
that active transaction, the original System journal remains the sole selector.

`update_guard.suspend` stages the exact prior Root publication anchor only for
an explicit retained rollback of the same completed update, before any rollback
intent. It requires the matching routing reservation, successful original install
terminals, untouched rollback evidence, the signed candidate, verified prior
caches, current SDK bytes and the original current writer. The parent System
worker must hold both its journal lock and product ownership lease; the child
probes those existing locks without waiting or acquiring them again.

The exact prior IPK is verified in the Root updater cache before an atomic anchor
write. A new private mode-0600 `system-rollback-anchor-<transaction>.json` receipt
binds the System transaction, active product lease, exact completed candidate
anchor and prior anchor. Receipt publication precedes the anchor change; retries
accept only that exact receipt and original/prior state. Separate transaction
names retain historical recovery evidence without colliding with a later update.
The adapter never writes the System journal, installer terminals or Home intent.
Unknown outcomes and mismatched receipts stay blocked. During staging, candidate
SDK bytes still have to match the original journal's selected package; the prior
becomes selected only after an actual rollback terminal. Old supervisor finish
then publishes the completed rollback normally.

The adapter reads private supervisor sources as data, checks their pinned hashes,
and executes only those captured source bytes in an isolated import context.
Adjacent bytecode and unrelated modules already imported in the process cannot
supply executable authority. The receipt is recovery evidence, not permission
to edit current pointers or synthesize installer completion on a live TV.

## Supported scope and release gates

- Original 1.3.0 Root supervisor: the target of this compatibility fix.
- Fresh 1.4.0 Root setups have a different path/grant inventory. A single archive
  cannot equal both original inventories. They require a reviewed computer
  migration; this change does not silently expand or shrink those installed pins.
- No-root package/update contracts remain separate. The unchanged Helper archive
  must stay byte-identical to published 0.6.19.
- Source versions remain the last published values until candidate freeze. Root,
  Root Updater, affected Home/UI packages, desktop/console and Android payloads
  need their normal independent version decisions and exact rebuilt validation.
  Changed independent-supervisor code requires fresh computer provisioning; an
  app-only update cannot replace its private trust boundary.
- Public 1.4.0 assets must never be overwritten. The correction ships in a new
  release only after frozen-head checks and coordinated hardware acceptance.

Offline evidence includes public 1.3.0 path/registration vectors, actual legacy
supervisor code, real signed package/cache inspection and filesystem replacement,
registration repair, recovery receipts, publication identity, and installation /
rollback state transitions. Synthetic SDK packages and adapted TV bus/process
boundaries are not physical-TV, audible-eARC or live remote-input acceptance.
Before publication, test actual signed 1.3.0 upgrade, profile preservation,
Home/emergency behavior and retained rollback on the C3 with its owner present.

# Issue 152: saved profiles after confirmed removal — 2026-11-18

Source base: `d980690e41b51f96689cccc7d8383bf80b15fd6c` (`release/next`).
Related report: [issue 152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-6987422168).
No TV connection or mutation, release selection or physical acceptance was made.

## Cause and correction

The fresh-install admission gate scans all saved profiles at the same address.
A completed No-root removal cleared only its own active receipt. An older
install/removal goal in a different saved connection therefore still caused
`pending-operation`, even though the selected connection had no pending operation.
The export establishes that cross-profile gate but does not identify the exact
blocking profile or its action. The regression uses an older Root install goal
as a representative conflicting connection, not a claim about the owner's store.

The shared store now archives older install/removal goals after verified full
removal, and before checking fresh-install admission. The latter handles existing
completed removals from cytv 0.21.3, including choosing a third saved connection.
The original receipt bytes and a copy of completion evidence remain in the target
profile. No successful installation result is fabricated for an abandoned goal.
Archive/proof writes finish before the active slot is removed, and a concurrently
changed receipt is retained. Failures remain retryable without deleting evidence.

Newer/equal-time goals, other hosts/actions, incomplete removals, corrupt receipts
and profiles awaiting SSH identity review stay blocking. The legacy format has
no cross-profile operation snapshot; local file modification times provide the
ordering. System clock rollback or external rewriting/restoration of evidence
can defeat this heuristic. This is an intentional scope limit of using the
already completed local proof without asking for another TV removal. Independent
review found the dangling identity-review symlink case; it was corrected and
covered by a regression. No further practical blocker was found.

## Offline verification

The new profile regressions failed against the original gate and passed after
reconciliation. The full backend integration executes No-root removal, verifies
that the old other-profile receipt was archived byte-for-byte, passes the shared
install gate, and completes a separate fresh package installation using the
existing local vendor/observer fixture.

A network-disabled Linux container also replayed the retained-directory case
with Developer Mode UID 5755/GID 5000, supplemental groups 44/505/509/777,
root-owned Helper and parent directories at 0775, and an empty state directory
owned by 5999:5000 at 0775. Actual cleanup retained the empty directories,
completed removal, reconciled the older other-profile goal and admitted a fresh
install reservation. This replay used native Linux Node 22; complete package
installation is covered separately by the backend integration fixture.

An additional attempt with EF950V 04.26.35 stock ARM Node 0.10.25 under QEMU
stopped at the pre-existing cleanup directory-descriptor identity guard before
reconciliation. It is not a successful firmware cleanup/installation result.
This patch changes host-side Python receipt handling only, not TV runtime code.

Focused checks and their final totals are recorded in the PR. An initial broad
run lacked the preverified Chinese-font cache and was stopped; the corrected
run reuses that cache. No Home routing, post-reboot launch, sound, standby, OTA,
rollback or overall EF950V compatibility is established by these local tests.

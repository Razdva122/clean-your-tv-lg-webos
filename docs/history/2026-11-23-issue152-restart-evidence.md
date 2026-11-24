# Issue 152: remaining restart causes and observations — 2026-11-23

Base: `1ce36925` (`release/next`). Report: [three repeated restarts](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-7109226077).
No TV connection/mutation or extra reporter operation; no release selected.

## Evidence boundary

All three new exports use cytv 0.24.1 on Windows AMD64. Helper and Home have
terminal removals but cleanup remains at `restart-required` with
`process-idle-unverified`. The exports contain no boot comparison, current target
or process observations. They do not prove that the owner has the synthetic
history/process cases below. The owner reports three power cycles; no physical
result or successful EF950V completion is inferred from the local reproductions.

Two attachments subsequently added to the same comment localize the last
refusal to the pre-package process check (`continue_removal` line 1387 in the
reported source), followed by `require_restart` and `restart-unverified`. This
is evidence that the resumed cleanup entered its process gate, not that the UI
never launched it. It still does not reveal why that process observation failed.
The top-level reason had been exported as `unknown`; `restart-unverified` is now
allowlisted too. These additions were read before finalizing the correction.

## Remaining reproduced causes

1. A completed package removal with an inherited install journal was excluded
   from the opaque-process rule even after a verified changed kernel. The same
   exclusion applied to historical resident-installer directories or a nonempty
   but settled cancellation object. Each case returned another restart prompt.
2. Missing process enumeration after a verified restart caused the code to
   release its old proof and create a new baseline. No number of further reboots
   can fix persistent process visibility that way. Missing volatile markers
   without changed kernel identity and persisted verified restart retries could
   take similar repeat-baseline branches.

Three new tests first failed on the original implementation. Terminal cleanup
now uses the actual unresolved package/configuration/older-work predicates,
instead of rejecting the mere presence of history. Observed current installer,
Homebrew and project processes still block; original pending configuration and
package requests retain their separate settlement rules. After an accepted
restart, incomplete process observation returns a recoverable cleanup-check
failure and keeps the original proof. Same-boot retries remain waiting. We do
not declare inaccessible processes stopped just to avoid a prompt.

Two older tests explicitly expected rearming after lost process visibility or a
saved verified restart. Their expectations were changed to preserved-baseline
blocking; targeted runs confirmed the new contract and later completion once
visibility is restored. The independent review found two unrecorded last-readback
failure decisions; both were fixed and covered by a late visibility-loss/retry test.

## Diagnostic contract

`cleanup_restart_evidence` in the private operation journal stores only a bounded
allowlist. `removal.restart_evidence` projects it into standard reports, including
reports exported after restarting the desktop app. Status report projection uses
the same sanitizer. Values are strict booleans plus fixed `phase`, `decision` and
`proof_kind` enums:

- Boot: proof presence/kind, whether probe returned, accepted restart, changed
  kernel and reuse of durable proof. Raw proof/boot identifiers are excluded.
- Process: idle, enumeration, observed project/installer/Homebrew, unreadable
  command line or links, opaque interpreter and exceeded process-list limit.
  No PID, command line, filename or other process content is exported.
- Decision: cleanup phase, terminal eligibility, project-catalog absence,
  history presence, unsettled configuration/package flags, older work, opaque
  allowance and retained directory-only residue. The latest phase/decision
  distinguishes waiting for a boot from blocked visibility after a boot.

Observations are freshly initialized each cleanup attempt and checkpointed before
an exit. Invalid diagnostic fields are stripped and cannot authorize effects.
A malformed/failed boot probe leaves `boot_probe_returned=false`, not a claim
that it succeeded. Pending `restart-required` is no longer exported as `unknown`.
No endpoint, credential, permission, package, dependency or control is added.

## Offline validation model

The unprivileged host fixture runs production cleanup JS and actual boot-proof
code with simulated `/proc`, vendor replies, kernel IDs and volatile markers.
Cases include previous install, settled cancellation/resident history, same boot,
missing marker with unchanged kernel, inaccessible `/proc`, unreadable command
line/links, visible project process, late visibility loss and verified-clean
retry. Privacy tests inject arbitrary strings, integer booleans and invalid enums
into saved/status evidence and verify the fixed report projection. A forged
positive diagnostic snapshot cannot cover an unchanged boot.

The network-disabled Linux fixture uses SDK UID 5755/GID 5000, supplemental groups
44/505/509/777, root-owned 0775 containers, Helper state 5999:5000/0775 and services
0:0/0775 followed by 5999:5000/0775 after a simulated fresh installation. It runs
both install/remove cycles, including inherited install history and opaque
processes, checks preboot uncertainty and postboot completion diagnostics, and
passes with native Linux Node 22. Vendor filesystem operations and intermediate
install receipts are simulated by the privileged fixture parent. It does not
boot LG firmware or prove post-reboot Home on the physical TV. The retained
stock ARM/QEMU investigation's descriptor-guard limit remains; no fresh stock
Node 0.10.25 run is claimed. Firmware-specific runtime defaults are not changed.

The final affected simple-removal/diagnostics/recovery selection passed 190 tests
in 117 seconds. The additional top-level reason-export regression passed separately;
all three exact Linux ownership cases passed. An exploratory 266-case run had only
the two superseded rearm expectations described above; remaining integration and
cleanup modules passed. Matching unaffected scenarios were not needlessly repeated.
`npm ci --offline`, formatting and diff checks passed. Detailed commands and CI
state are recorded in the PR. No repeat
power-cycle request is made to the owner. Actual device state remains open until
an updated standard report or explicit owner result establishes it.

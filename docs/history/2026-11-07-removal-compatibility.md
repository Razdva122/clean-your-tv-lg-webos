# Removal compatibility corrections — 2026-11-07

This records source and host verification for the unpublished 1.10.0 candidate.
It is not a device installation/removal report. Final changed-removal acceptance
is deferred; unrelated manual feature checks are not repeated in this task.

## Corrected boundaries

- Strict stdin execution on Node 20+ exposes a getter-only global WebCrypto
  property. `cleanup_tail.js` used top-level `var crypto`, so it could fail before
  its guards. A local Node 23 stdin run reproduced the exception, while `-e` and
  the VM fixture did not. Two binding references now use `nodeCrypto`; a real
  stdin regression reaches the exact selector guard on both current Node and
  Node 8 with the getter-only binding.
- The shared cleaner recognizes UID0 and exact `0777` only on fixed SDK
  containers and known project app/service roots. Existing UID501/1001 shared
  services/packages handling remains. Unknown writable ancestry, UUID staging,
  foreign owners, symlinks and inode replacement are still refused.
- A failed or unconfirmed disable response from the two optional legacy
  Helper/Renewal services moves the existing full-boot checkpoint before package
  removal. The marker and boot baseline survive interruptions. After the boot
  changes, cleanup does not relaunch the recorded broken service. Root routing
  restoration, exact owned-activity cancellation and final absence proofs remain
  mandatory. Unexpected bus failures still stop cleanup.
- Known Root completed-profile and rollback-anchor data, plus finite System
  current-descriptor/installer-acceptance records, are classified by their exact
  component and bounded filename formats. Live roots and already authenticated
  archives use the same classification. Genuine inverse backups remain separate;
  unknown names, unsafe ownership/mode, hardlinks and changed inodes still block.
- Five existing removal reason codes survive diagnostic projection. The existing
  removal plan supplies Retry advice without a contradictory generic unfinished
  installation warning. Specific trust/authentication/storage advice keeps its
  priority. No private error text is exported and no new user copy is introduced.

## Verification

Independent scoped reviews approved the changes. The relevant regressions failed
before the fixes and passed afterward:

- Root cleanup/tail: 74/74 passed on Linux, exact Node 8.12.0 and strict GCC 12.2,
  with real UID1001/shared-directory, directory-replacement and original-lock
  handoff checks. Read-only source hashes matched before and after the run.
- Shared cleaner: 32/32 passed on current Node; six focused cases passed on each
  exact Node 0.10.15, 0.10.25, 0.12.2 and 8.12.0. These model the reported SDK
  ownership explicitly; modeled UID metadata is not a device acceptance claim.
- Diagnostic and retry guidance: 48 passed, including private-message exclusion,
  first-failure retention and specific authentication/trust guidance priority.
- Known private receipts: five new cases passed; affected host groups ran 51
  cases with 50 passed and one Linux-only skip. Near-prefix/wrong-component,
  foreign-owner and hardlink refusal cases remain covered.

The normal focused payload builder passed. Compared with build 42276916934's
actual Android payload, only `root-updater/install_device.py`,
`root-updater/cleanup_tail.js`, `root-updater/cleanup_no_root_private.js` and their
bundle manifest changed. All TV IPKs, published Helper 0.7.4 and the native
installer-support utility are byte-identical. This does not establish that the
changed installer execution has completed successfully on a TV.

## Candidate and acceptance boundary

Build 42276916934 remains successful evidence for its original source. Its pin
is removed from the corrected branch because installer inputs changed. A new
complete candidate must pass and be selected before final acceptance; the release
PR remains draft. No Helper lifecycle, supervisor migration or new cleanup
framework is introduced. Versions remain the unpublished 1.10.0 component set.

The intended remaining device sequence is the same removal intent, interrupted
connection/retry, a verified full kernel boot, final absence readback and repeated
Remove. An AC power-disconnect result is not available. Fresh interrupted setup,
pristine unrooted Developer Mode and other hardware remain untested unless
separately recorded. No public release or shipping notice is announced.

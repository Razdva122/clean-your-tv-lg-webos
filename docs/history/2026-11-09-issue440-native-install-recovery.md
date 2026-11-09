# Native admission and fresh setup recovery (#440)

This is source investigation and synthetic verification, not an installation
report. No TV was contacted or changed. Original reporter acceptance remains
open; no additional diagnostic probes are requested.

## Change and authority

The compositor admission rejected every non-root mount covering Home, including
a separate immutable `/usr` image. Admit only whole, read-only internal-MMC
squashfs `/usr` with matching Home device identities. Keep subtree, stacked,
writable, overlay and unknown covering mounts blocked. The
[public original probe](https://gist.github.com/metaljay/8a1e63060c7fe7cc1d90fe34fe97e386#11-device-probe-record-2026-11-04)
supports the separate read-only system-image layout; the exact reporter mount
shape is not established by a boolean covering-mount result.

An early driver refusal can retain a host pending operation without device
journals. Absence does not authorize clearing or resubmission. Explicit full
removal keeps the unknown original result and uses the existing ownership,
writer fences, package receipts, restart and private-cleanup protocol.
Empty preserved/live routing evidence plus a fresh current compositor probe
can prove stock Home independently of unavailable settings/profile APIs.
Python and the final Node cleaner recheck their respective current proof before
destructive cleanup; Node also repeats it before final acknowledgement and
later read-only stock inspection. New foreign Home state or key773 binding
refuses that proof. Existing owned restoration remains unchanged.

Fresh setup after verified cleanup goes through a new shared-coordinator
request. Under its original mutex, the coordinator revalidates cleanup and moves
only pinned component fences before isolated compositor deployment. The child
inherits the mutex FD. The old request cannot replay; a native request has no
normal-product submission authority. No updater is installed by this path.
Installer preflight recognizes the cleanup lease even without any Root
directory. Completed cleanup invalidates retired host support/Python caches.

## Verification checkpoint

- The new system-image regression failed on the old mount guard, then passed
  with the narrow exception and negative covering-mount matrix.
- Focused host routing/removal/reinstallation, current Node tail, exact Node
  8.12.0 tail, component cleanup and native lifecycle tests passed. The native
  lifecycle run needed ordinary local subprocess permissions outside sandbox.
- Real isolated child tests exercise the stock-proof JSON envelope and inherited
  ownership FD/inode, flock exclusion and exact parent-lease admission.
- Independent review found two gaps (foreign Home state appearing after the
  Python probe; absent Root directory hiding the cleanup lease). Both gained
  failing regressions and corrections. Final review has no remaining findings;
  normal resume of a native request was checked to fail closed without replay.
- Broader affected installer/setup/Android/TV-runtime verification is in progress
  at this checkpoint; its final result belongs in the implementation PR.

The normal removal/setup controls and localized steps are unchanged. Developer
admission/recovery documentation was updated. No new permission, dependency,
network endpoint or file is introduced. The existing clean-removal receipt gains
the bounded `stock-compositor` observation (native device/inode/size/hash), and
the new native install uses the existing request/ownership records.

This does not prove the reporter's installation, Home routing, sound, emergency
controls, standby, cold boot, update or rollback. A checked draft installer and
device acceptance are still required. The existing release coordinator owns
version selection, candidate scope and public delivery.

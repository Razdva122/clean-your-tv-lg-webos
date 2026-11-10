# v1.17.0 — Helper recovery, diagnostics and website

## Changes

- Preserve the original No-root operation while authenticating and reclaiming
  its retained pairing key after Helper ownership handoff (#488, #487).
- Recognize narrowly confirmed input disappearance during power-off without
  turning ordinary sleep into an emergency stop. Preserve explicit Stop,
  triple Home, Home Off, watchdog and cleanup-failure protection (#488).
- Share checked storage, lifecycle/power and recovery advice contracts. Retain
  bounded typed first-cause context in the standard diagnostic report (#493).
- Admit stock Home up to 16 MiB across installer, compositor runtime and guardian;
  vendor UID 1001 requires immutable SquashFS and read-only device evidence.
  Other file-integrity, recovery and input checks remain (#492, #494, #454).
- Redesign the multilingual website with recorded animated previews, a separate
  interactive demo and 52 practical articles across 13 languages (#470).

## Versions and packaging

| Component | v1.16.0 | Prepared target | Reason |
| --- | --- | --- | --- |
| Release | 1.16.0 | 1.17.0 | Website and shared-contract integration |
| Home FHD/HD | 1.15.0 | 1.15.1 | Renewal uses the changed shared storage contract; new Helper rollback baseline |
| Helper | 0.8.0 | 0.8.1 | Rebuild controller, relay, storage and power behavior together |
| cytv | 0.17.0 | 0.17.1 | Authenticated continuation, recovery advice, reports and Root preflight |
| Android / versionCode | 0.16.0 / 31 | 0.16.1 / 32 | Changed shared installer sources and TV payload |
| Root / infrastructure | 0.16.0 | 0.16.1 | Changed compositor admission and guardian/support |
| Both edition Updaters | 0.5.7 | 0.5.7 | Actual packages and Root Updater bundle are byte-identical |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.8 / 1 | Actual 29-file bundle unchanged; retained supervisors stay pinned |

Both-resolution Home/Root, ordinary/Beta support and embedding computer/Android
installers need coherent packaging. Preserve Android package ID and original
signer. No Homebrew Installer promotion is selected. No new permission grant,
network endpoint or persistent state format is introduced by this inventory.

## Validation and limits

The [canonical candidate ledger](history/2026-11-11-release-1.17.0-candidate.md)
records reused source/browser/platform checks, local package preflight and the
selected remaining cases. Prepared metadata and local payloads are not a trusted
full candidate or final artifact acceptance.

Full dispatch is blocked by the mandatory published-Home/new-Helper compatibility
probe: the existing approval covers an earlier transition, not Helper 0.8.1.
Complete that probe and commit its exact archive/hash/device evidence before
dispatching the complete platform matrix. No final build or hardware acceptance
is selected yet; no publication or main merge is authorized by preparation.

The original #487 service-status discrepancy and reporter-device continuation/
standby result remain unverified. The corrected #454 C1 prerequisite, original
catalog step and completed installation still need reporter confirmation with
the published installer. Host and synthetic tests do not establish either
reporter's recovery, actual firmware events, physical remote/audio/power
behavior, public-feed operation or universal compatibility.

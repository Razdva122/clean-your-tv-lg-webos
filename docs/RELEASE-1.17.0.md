# v1.17.0 — Helper recovery, diagnostics and website

## Changes

- Preserve the original No-root operation while authenticating and reclaiming
  its retained pairing key after Helper ownership handoff (#488, #487).
- Recognize narrowly confirmed input disappearance during power-off without
  turning ordinary sleep into an emergency stop. Preserve explicit Stop,
  triple Home, Home Off, watchdog and cleanup-failure protection (#488).
- Restore private Helper state when firmware expands the mode of known boot
  records. Load the verified installer payload for saved No-root recovery and
  complete Root activation when there is no Helper process to stop (#510,
  #509, #487).
- Fix fresh System updater setup on TVs where reading a small cached file
  with the maximum buffer size exhausted memory. The installer reads the
  verified file size and still detects size changes (#508, #507).
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
| cytv | 0.17.0 | 0.17.1 | Authenticated continuation, recovery advice, reports and corrected System setup |
| Android / versionCode | 0.16.0 / 31 | 0.16.1 / 32 | Changed shared installer sources and TV payload |
| Root / infrastructure | 0.16.0 | 0.16.1 | Changed compositor admission and guardian/support |
| Both edition Updaters | 0.5.7 | 0.5.7 | Actual packages and Root Updater bundle are byte-identical |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.8 / 1 | Fresh setup script and bundle manifest change; the installed supervisor package stays byte-identical |

Both-resolution Home/Root, ordinary/Beta support and embedding computer/Android
installers need coherent packaging. Preserve Android package ID and original
signer. No Homebrew Installer promotion is selected. No new permission grant,
network endpoint or persistent state format is introduced by this inventory.

## Validation and limits

The [canonical candidate ledger](history/2026-11-11-release-1.17.0-candidate.md)
records reused source/browser/platform checks, local package preflight and the
selected remaining cases. Prepared metadata and local payloads are not a trusted
full candidate or final artifact acceptance.

The original published-Home/new-Helper compatibility probe passed on the
maintainer C3 (43.21.71/SDK11.2.0) with the exact Helper0.8.1 and published
Home1.15.0. Owner-observed Home/triple-Home/retained Stop and arrows/volume agree
with readback; all232 installed public files match. The new exact compatibility
approval passes verify_helper_transition. This pre-dispatch probe does not
replace final candidate package delivery or selected physical acceptance. The
complete replacement build42969073353:1 passed all23 jobs after the reviewed
Windows fixture-only correction #504. Exact601-file CLI/APK payload, original
APK signer and code31→32 emulator retention/native checks pass. Protected
Root-only signing42974007477 passed production-key signature, exact package
closure and live provenance checks without publication.

The owner-present final-artifact pass found CLI recovery missing the manifest
needed by Root-SSH handoff, and Helper unavailable after remote-power and
separate AC-off/on with its key expanded to0777. Navigation and audible sound
passed, but Home-control and dependent active-Stop acceptance remain gaps.
The authorized return restored Root0.16.0 with matching configuration/preferences,
verified recovery, Home Off and no pending operation. Fresh unchanged
System1.2.8 setup raised MemoryError before bootstrap, blocking signed final
Root transition and rollback/forward. The original12-ID ledger records eight
scoped passes, two observed failures and two concrete blockers, with no safe
independent untested case remaining in that pass. This completes the failure
inventory, not candidate acceptance. No final acceptance token, main merge or
publication is granted.

The replacement Helper 0.8.1 also passed the compatibility probe with published
Home 1.15.0 on the same C3. The owner verified explicit Start, short Home,
remote-button sleep/wake in the same boot, and triple Home with LG controls.
Readback confirmed the key remained at mode 0640. The maintainer deferred the
active cold-boot check. The release ledger links both exact Helper archive hashes
and the remaining final artifact checks.

The original #487 service-status discrepancy and reporter-device continuation/
standby result remain unverified. The corrected #454 C1 prerequisite, original
catalog step and completed installation still need reporter confirmation with
the published installer. Host and synthetic tests do not establish either
reporter's recovery, actual firmware events, physical remote/audio/power
behavior, public-feed operation or universal compatibility.

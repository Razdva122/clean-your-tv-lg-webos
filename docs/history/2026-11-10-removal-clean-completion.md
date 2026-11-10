# Verified removal completion without a mandatory restart

Date: 2026-11-10. Source/host verification only. No TV was contacted or changed.

## Change and preconditions

Root and No-root can finish explicit removal on the current boot after restoring
controls/startup, verifying package/file absence and confirming process absence.
Unresolved original setup, broken startup services and live or unverifiable
processes retain the restart path. Root's independent Node tail repeats current
routing, registrations, packages, private-file and process checks before retiring
its runtime. Pending verification stays actionable without a generic failure
presentation; connection interruption and package refusal remain distinct.

Root stores `cleanup_without_restart` only after current cleanup; the flag never
substitutes for the independent final proof. No-root stores
`cleanup_boot_release_started` before its own marker release, so a lost release
reply cannot fabricate a restart. `cleanup_boot_verified` retains an observed
restart across a failed host completion; reuse requires fresh process checks and
reappeared processes capture a new baseline. No permission grant, network endpoint
or automatic TV reboot is added.

## Verification scope and reuse

The release candidate is the existing unfrozen draft. No version, inventory,
selected build or acceptance was changed. This dated observation can be linked
from its existing release ledger; it is not another release tracking system.

Earlier development checks were consulted rather than repeated wholesale. The
specific missing evidence was the extracted patch without parallel installer
customization edits, applied to `release/next` base `89fc8bda`. That base also adds
weather permission state to Root cleanup. Focused checks below verify this
composition and preserve that state classification. A new PR/branch alone was
not the reason for these checks.

Product/test content manifest SHA-256: `9da1ae07848d38a3e9c71b2ae342cf45e203869a617f6d5cfd39e90fc40ec258`.
The manifest sorts changed paths under android, cytv, root-edition and tests
relative to base `89fc8bda`, hashing each file and recording
`path + NUL + file_sha256 + LF` before hashing the complete manifest.
Commit-hook formatting preserved every verified product/test byte.

| Scope | Environment and result | Remaining gap |
| --- | --- | --- |
| No-root removal/fences, Root host adapter, desktop recovery/presentation, CLI recovery and Android bridge | macOS ARM64, maintained project Python environment; 149 tests passed | Other host OS/device acceptance not claimed |
| Root removal coordinator, quiescent removal, final Node tail and child handling | Exact Node 8.12.0 and 0.12.2 available; 164 tests, two declared platform/container skips, no failures | Linux descriptor-race/container-only cases remain for CI |
| Android removal result and retry flows | Local headless Chrome; 18 completion-proof combinations, both editions and all 13 UI languages passed | Physical Android device/WebView not exercised |
| Formatting and patch | `npm run format:check` and `git diff --check` passed | Not a frozen-candidate full suite |

Regressions cover lost marker-release replies, saved restart proofs with a
reappeared process, host completion retries without another power cycle,
renamed Helper processes, delayed shell launches, final-tail live-process
refusal, pending cleanup presentation and distinct connection instructions.
Independent reviews found no remaining blocker after the reproduced failures
were fixed and rechecked.

## Physical acceptance and publication limits

TV model, firmware/webOS and remote: unselected/untested. Root and No-root here
use filesystem/process/RPC fixtures, not a physical television. Physical removal,
Home/remote behavior, sound, standby, cold boot, OTA and rollback remain untested
for these changes. No installer was published or installed. Final trusted build
selection, required candidate checks and affected physical acceptance remain with
the release coordinator.

## Integration preflight — 2026-11-10

The successful original-head CI is retained: [Linux/macOS and browser](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42760633178),
[Windows/Intel Mac runtime](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42760633360).
The later release-base inputs changed in two relevant areas: #478 changes retained
native Home readback in the same cleanup/final-proof path; #482 adds the desktop
personalization stage and translation rows. The translation conflict keeps both
sets of rows. Focused Root proof and shared desktop/translation checks are needed
to decide whether this composition can merge. Unchanged standalone No-root and
Android browser cases reuse the earlier results; no full local suite, build or
device operation is repeated merely for integration.

Integration release-base input: `514e0b5e0aba32a186e77f598d066b611ae02acf`.
Results: 96 shared desktop/recovery/translation/Android-bridge tests passed;
170 Root cleanup/final-tail tests passed with two declared platform/container
skips, using the exact Node 8.12.0/0.12.2 tools already available. `git diff
--check` passed. Both sets of translated messages and the earlier Root native
readback correction are preserved. These checks resolve the changed-input
composition gap; they do not establish physical TV or final-package acceptance.

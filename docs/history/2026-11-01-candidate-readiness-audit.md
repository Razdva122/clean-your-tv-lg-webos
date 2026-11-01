# Candidate readiness and policy repair — 2026-11-01

PR #223 merged as `6e83eb29` after final selected CI passed on `2968d857`.
PR #224 merged as `ac9a35ce` after final selected CI passed on `503d26d6`.
The actual combined merge tree exactly matches locally checked `3b562daf`.
The coordinator recollected #223/#224 in the committed candidate inventory.

Candidate #210 remains an unfrozen `release/next` → `main` draft. This audit
is source/host/browser evidence, not a frozen build or physical acceptance.

## Why Integration policy remained pending

The privileged `release-policy.yml` preflight posts a commit status before its
trusted `main` checkout. A post-merge description edit triggers that preflight,
but `refresh_policy` intentionally skips closed PRs. The run succeeds while the
new pending status remains. This reproduced for #215, #221 and #222.

PR #223 adds a closed-event guard to the actual preflight. Closed refresh stays
read-only because statuses belong to a SHA/context, not a PR: writing a synthetic
success for a closed PR could overwrite an open candidate at the same SHA.
Independent review rejected that alternative before merge. The final guard
preserves every open-PR failure/provenance/build gate. The actual workflow JS
regression failed on closed events before the guard and passed afterward;
13 release-reuse plus 16 release-flow cases passed.

GitHub sources `pull_request_target` workflows from the default branch
([GitHub change notice](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/));
the trusted script also explicitly checks out `main`. This prevention becomes
live only after the normal finalized release integrates it there. Until then avoid editing merged
PR descriptions. No privileged candidate code is executed to accelerate rollout.

Existing pending statuses for #215, #221 and #222 were restored to their
pre-edit successful policy results after verifying: merged/closed PR, unchanged
head SHA, original `github-actions[bot]` terminal status, successful original
validation run, and no open integration PR sharing the SHA/context. The new
status explicitly says it restores the prior result and links that original run.
The open release candidate's failure was not changed.

- #215 original validation: [41273355335](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41273355335)
- #221 original validation: [41274818218](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41274818218)
- #222 original validation: [41274696129](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41274696129)

## Czech TV interface (#211 / #224)

The shared TV picker adds Čeština (`cs`), system `cs-CZ` normalization and saved
manual selection. Home, Root Settings, themes, HDMI audio and independent
updater/recovery have 377 unique source translations plus Appearance/Advanced.
All four current profile validation boundaries preserve Czech; unknown values
remain rejected. Installer locales remain the existing twelve; no `--language
cs` is advertised. The Czech guide is explicitly candidate-only TV guidance.

Local evidence on final product source `eb81c14e` and test-only `503d26d6`:

- Catalog coverage/interpolation: 360 combined Home/Root/theme sources and 201
  Root/audio sources, all thirteen TV locales. Locale persistence/system
  fallback, Root JS/Python profile and independent updater cases passed.
- Actual Chrome language/navigation/persistence/automatic-reset matrix passed
  thirteen locales across both editions. Firmware browser passed thirteen
  locales at 1080p/720p; category geometry passed 52 edition/locale/resolution
  combinations. No physical-TV or native-speaker acceptance is claimed.
- `scripts/test.sh tv` passed 967 Root and 128 System cases, compatibility,
  theme, JS/native and other selected checks. macOS skips real Linux multi-UID
  coverage; exact Node 0.12.2 was not configured locally. CI supplies its own
  recorded runtime/platform evidence.
- Compiled Home passed all four legacy browser modes (modern, no-inset,
  no-inset/no-ES2015 and prefixed WebKit). A raw-source run without the required
  compilation is not legacy-prefix evidence; only the compiled rerun is cited.
- The initial CI browser run correctly rejected an obsolete count of thirteen
  picker entries; Automatic plus thirteen languages requires fourteen. The
  final test revision fixes that expectation. The separate firmware harness
  was updated to enter its existing Updates category and test all Back steps.

Independent source and scoped test-delta reviews approved. Original #211 remains
open awaiting normal public release. New bytes require rebuilt Home/Root,
updater/infrastructure and embedding installers; historical package acceptance
is not reused.

Final selected CI:
[#223 / 41276513027](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41276513027),
[#224 / 41276975518](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41276975518).
The combined tree also passed 13 release-reuse, 16 release-flow and three README
cases. These checks do not select or accept a frozen candidate build.

## Remaining gates before readiness

1. **Freeze scope and versions.** `release-plan.json` still has `version: null`,
   no selected build and empty acceptance. Choose final release/component values,
   Android versionCode and consistent manifests, inventories, pins and notes.
   Published baselines remain release 1.5.4, Home 1.6.1, Helper 0.6.21,
   cytv 0.6.1, Android 0.5.1/code16, Root 0.6.2 and updaters 0.3.4.
   System's committed source baseline is 1.1.2.
   Changed Home/Root/updater/System and embedded payloads need coherent rebuilds;
   unchanged Helper retention still needs authenticated baseline/transition checks.
2. **Finish the candidate documentation pass.** Reconcile the #222 Settings
   retry/resume controls and affected localized guidance, the new Czech TV-only
   boundary, final versions/downloads/notes and recovery/rollback instructions.
   Keep published workarounds and historical failed device evidence honest.
   Reconcile the stale unpublished-1.5.3 status in `android/STABLE-READINESS.md`
   against current published versions and linked historical results.
3. **Dispatch one full frozen candidate.** Use `cytv.yml` on `release/next` with
   `full_candidate=true`; verify complete Linux/macOS suites, browser, ARM Python,
   Android and all four desktop builds. Focused implementation runs are not a
   substitute. Then `release-flow.py pin-build --run-id RUN_ID` and commit the
   verified run/attempt/source and artifact hashes.
4. **Complete affected exact-package acceptance.** `acceptance-report` selects
   controls, startup, ui-controls and update-recovery. Establish device/model,
   firmware/webOS, remote, preconditions, packages and expected/actual outcomes;
   observe Home/Back/key-up/triple-Home emergency and Off persistence, startup,
   cold boot separately from standby/wake, update and retained rollback, and
   affected sound behavior. Group needed observations in an agreed owner session.
   Forward #202 cancellation and separate #171 standby/control evidence remain
   unresolved; successful host tests do not resolve their reported TV callers.
   Control/data/audio loss or broken update/recovery blocks delivery.
5. **Final Android artifact and upgrade.** Verify the protected-CI release APK
   source, SHA-256, versionCode, SDK/ABI, non-debuggable flag, embedded payload
   and original pinned signer. Verify an in-place upgrade from the published
   baseline with the original certificate, retaining profiles, keys and durable
   recovery receipts without uninstalling. Historical emulation or a local
   replacement signer cannot substitute for these final-artifact checks; preserve
   the established device/emulator acceptance limits in the record.
6. **Final gate and delivery.** Bind acceptance to the exact build token, keep
   candidate input bytes unchanged, verify Release policy and final package/feed
   signatures/hashes, then normal publication and shipping notices. Reconcile
   every included issue after verified publication; do not close partial reports.

The current Release policy failure, “Finalize the release version and bump
release-versions.json”, is expected for this unfrozen draft, unlike the repaired
closed-PR pending bug. It must remain blocked until the release requirements are
actually met. No TV was contacted or modified by this audit.

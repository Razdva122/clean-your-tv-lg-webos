# Combined installer regression audit — 2026-11-02

Review scope: all five maintainer-requested installer improvements, integrated as
#232–#235. Pre-change base `b03b121d`; tested candidate
`9c50d0a4f5e7ea50aba9b94d57ff53e592787e26`. No product change, version selection,
freeze, build pin or device operation is part of this audit.

## Cross-stage results

| Improvement | Combined evidence and boundary |
| --- | --- |
| Primary failure and diagnostics | Initiating error survives later status/recovery errors; cached exports are revalidated. Legacy missing causes remain unknown. |
| Interrupted-install recovery | Separate default-No inspection/change confirmation; pending, idle, identity and backend proof guards remain authoritative. No implicit reinstall. |
| Packages, startup and Home | Package/launch/startup results remain separate from the owner's optional physical Home observation. Failed/skipped Home cannot undo packages or trigger reinstall. |
| Early Root admission | Existing Settings/Profile contract precedes private Python/packages. New reads do not expand pending recovery admission or prove firmware compatibility. |
| Connection guidance | Typed, phase/edition-specific advice retains pending/trust priority. Reports contain fixed advice categories, not raw replies or exception text. |

Independent read-only review of the complete range found no actionable integrated
regression; 62 focused tests passed across diagnostic context, recovery, outcomes,
Root capabilities and guidance. Qt/Android and Root worker retention were reviewed.

Three additional chained host fixtures passed using real shared modules with
synthetic device responses:

1. Early Root interface refusal → retained original capability evidence → later
   connection failure with distinct advice. Original categories remain intact.
2. Initial package failure → busy-service recovery refusal → pending guidance.
   The first error and receipt bytes remain unchanged; no uninstall/install runs.
3. Separately confirmed Root continuation → owner reports Home failure. Packages
   remain verified, the Home row fails, original diagnostic history remains and
   no reinstall/removal is submitted.

`npm ci` completed. Combined `scripts/test.sh tv installer android setup` exited
zero: 969 Root tests, 132 System tests, 220 setup tests, 640 installer tests (two
expected platform skips) and 26 Android tests, plus JS/native/compatibility and
Homebrew payload/runtime/bridge/continuation checks. Actual Qt was exercised in
the local installer run. Real Chrome maintenance/result/recovery/guidance tests
and locale-selection/persistence/native-message checks pass in all twelve
installer languages. This is scoped host/transport/UI regression evidence,
not final frozen-candidate or physical acceptance.

The ordinary `android/tests/ui.cjs` browser smoke initially failed because it
still required the generic Status shortcut intentionally removed by #235. This
was a stale expectation, not a product regression: the documented error flow
retains Done/manual connection review and excludes blind Status/Restore. The
narrow test correction verifies both forbidden shortcuts are absent, Done is
available, no native request is triggered by the error screen, and manual review
preserves the target and port 9922. Error visibility, escaping, credential/trust,
edition navigation and responsive checks remain. The corrected real Chrome run
passes; independent review confirmed the diagnosis and test change. Product
source is unchanged. This failure was investigated and corrected rather than
excluded from the result.

Current-head [Linux/macOS CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41338690398)
and [frozen Windows/macOS Intel entrypoints](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41338690418)
passed. Their focused scope skips full-release/browser jobs; local Chrome evidence
does not replace the complete candidate matrix. Optional exact Node 0.12.2 was
not run locally; the separate opt-in prototype is not new baseline compatibility.

No TV was contacted, staged or changed. Model, firmware/webOS and remote are not
applicable to these fixtures. Physical Home, other controls, sound, standby, cold
boot, OTA and rollback are untested by this audit. No private installation result
or diagnostic content is published.

## Remaining release work

Candidate #210 is still an unfrozen draft. `release-plan.json` has no version,
acceptance or selected build; component metadata remains at published v1.5.4.
The current Release policy failure explicitly says **Finalize the release version
and bump release-versions.json**. Green implementation CI does not satisfy it.

1. Freeze one coherent inventory; choose release/component versions and Android
   versionCode, update manifests/pins/inventories and release notes. New worker
   diagnostic fields require rebuilt Root coordinators as well as embedding
   desktop/Android payloads; older installed packages cannot provide that evidence.
2. Complete the documentation pass against those final versions/artifacts. The
   five-stage CLI/diagnostic/recovery contracts and twelve guides are updated;
   remaining candidate Settings guidance, published/candidate boundaries and stale
   `android/STABLE-READINESS.md` baseline text still need reconciliation.
3. Dispatch the explicit full frozen candidate with `full_candidate=true`; require
   all desktop, Android, Linux/macOS, browser and ARM/runtime gates. Pin the final
   successful run/attempt/source and artifact hashes before physical acceptance.
4. Verify the final protected-CI Android APK signer, metadata and payload, and an
   original-certificate in-place upgrade from the published baseline preserving
   profiles, keys and unfinished receipts without uninstall. Run the native
   operation/process-death fixtures; browser bridge tests do not replace this.
5. Record exact-package Root/No-root acceptance: actual Home routing, Back and
   unrelated controls, emergency Off, sound, startup, standby and true cold boot
   separately, installation/update/recovery and retained rollback. The acceptance
   scope tool currently selects controls, startup, UI controls and update/recovery.
   Carry old results only for identical scenario artifacts and preconditions.
6. Resolve release-blocking control/data/audio/update/recovery regressions and
   record explicit decisions for other known limitations. #202 forward Home
   cancellation remains unresolved; retained-rollback source improvements still
   need exact-package acceptance. #171's earlier wake failure and #207's standard
   IR Home routing/physical HD delivery remain separate unresolved reports.
   Earlier deferrals and one-device passes do not establish new-byte acceptance.
   Preserve explicit Off/emergency cancellation; do not force-enable to pass QA.
7. Verify signed HD/FHD feeds, authentic rollback baselines and supported migration
   for independently provisioned updaters. First legacy Home HD publication cannot
   invent a compatible published HD rollback. Then pass final policy, publish and
   verify packages/feeds, verify shipping notices and reconcile included issues.

Open included issue labels were checked against the inventory: partial original
reports retain their unresolved statuses; no issue is closed or relabelled as
fixed by this audit. #133/#216 retained recovery and #201 uncertain No-root
transactions remain unresolved; #217/#229/#230 retain existing information
requests. Their existence is not evidence that these five changes regressed.
No new reporter test or unsafe device operation is requested here.

The release is not ready for publication. No new source regression was identified
by this review; outstanding frozen-build and device gates remain mandatory.


## Integration and record checks

The narrow test correction entered `release/next` through
[PR #236](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/236), source
`2e490d4fb153052c221014327f0c179b4df2b4c1`, merge
`11938db2a8730f8d0fd1cb1e279835c3d64cd9c9`, after selected
[CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41339694540)
and [integration policy](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41339694611)
passed. Product files match the tested `9c50d0a4` exactly. Inventory/record tests
pass all 16 cases; changed relative Markdown links and `git diff --check` pass.
All 17 open included issues have one status label; unresolved-original labels
were preserved. Candidate #210 retains an explicit blocked release checklist and
links this audit. No additional reporter comment or duplicate request is needed.

# Next candidate: physical acceptance plan

This is a plan, not a test result. Its integrated scope is #415/#419/#421/#423/
#424/#426/#427/#428/#429/#430/#431/#432/#433 at source merge `2e22c62b`.
Reconcile it with `release-plan.json` and final artifact selection before freeze. Selected version: v1.13.0 (Home 1.13.2, Helper 0.8.0, Root 0.13.2, both Updaters 0.5.4, cytv 0.14.0, Android 0.13.0/code28, fresh System 1.2.7). Final build42491346675:1, signed hashes, selected C3 cases and their actual results are recorded below and in the artifact-bound acceptance. Preliminary hashes and host results are in the [preparation record](2026-11-08-release-1.13.0-preparation.md). Every physical case starts **UNTESTED**. Source CI,
package installation and historical observations do not accept these new bytes.

## Admission and record

1. Finish product/build inputs, versions/manifests, embedded payloads, release
   notes and affected guides. For the new Helper from #415/#419/#428, prepare
   genuine published-Home/new-Helper transition and rollback evidence covering
   actual canonical package hashes **before** full candidate dispatch. The old
   Helper approval cannot cover new bytes. Complete independent host/package
   checks while a physical prerequisite is blocked; do not bypass the gate.
2. Build one complete frozen candidate, pin its final successful run/attempt,
   retain artifacts/digests, and record matching signing provenance. A later
   guarded input or rerun requires re-evaluation; evidence-only equivalent edits
   retain the verified build. Preliminary TV builds are not final acceptance.
3. For each selected device record model, firmware/webOS/TV runtime, remote(s),
   edition/resolution, installer platform, before/after component versions,
   artifact hashes and existing routing/update/recovery state. Do not publish
   addresses, keys, profiles, inventories, screenshots or raw backups.
4. Use a bounded owner-supervised session. Finish the planned safe independent
   cases and consolidated failure inventory before a subsequent product-fix
   batch. Stop dependent cases when recovery is unresolved; do not perform extra
   TV changes merely to fill this table. Reuse earlier evidence only for identical
   scenario artifacts and device/state preconditions.

## Changed behavior: physical cases

| Case / source PRs | Preconditions and bounded action | Expected result / what must be recorded |
| --- | --- | --- |
| P01 — No-root passive IR, #419/#428 | Eligible ordinary Developer Mode installation and available standard IR remote; verify actual optional LGE RCU access without changing permissions. From an app use short Home, then held Home. | Short Home opens project Home after about 700 ms; a possible LG Home flash is documented. Held Home remains with webOS. Rooted/manual-install evidence does not prove stock access. Missing hardware/access is BLOCKED/UNTESTED. |
| P02 — delayed action and explicit stop, #428 | With working IR, queue short Home then use Home-control Off/Stop before completion. Re-enable only explicitly and use a fresh press. | No stale queued launch crosses Off/On or Stop. Three fresh qualifying Home taps release controls; LG remains usable and no automatic emergency reset occurs. Native overflow/relay-death/watchdog race injections are host tests, not requests to corrupt a TV. |
| P03 — existing remote regression, #419/#428 | Where available, use Magic Remote as well as IR on the same installed artifacts. Exercise Home, Back, arrows/OK, key release, pointer/wheel, volume and one unrelated button. | Existing M-RCU behavior and unrelated keys remain usable. Observe actual duplicate-source behavior; do not infer it from fixtures. Mark absent remote types untested. |
| P04 — stopped Helper and heartbeat/power, #415/#428 | Preserve an existing explicit stopped state. Start only via documented Start Helper confirmation, then perform a recorded bounded repeated remote off/on set with Home from an app after wake. | Package update alone does not silently clear the stop. Explicit restart restores interception. No heartbeat crash/blocked state; resume and physical Home work. Record cycle count and actual intervals; a clean short cycle does not establish race elimination. |
| P05 — Root retained-route startup, #427 | Confirm enabled intent and exactly owned retained project Home before an ordinary remote off/on. Launch an app early, then use physical short Home in the previously problematic early-start interval; repeat outside the triple-Home window. | Project Home stays the destination without a forced loading screen/foreground restriction or profile rewrite. Record actual startup timing and native-vs-software input evidence. Existing #422 failures remain failures until matching changed artifacts are tested. |
| P06 — Root emergency during startup, #427 | In the same healthy prepared startup session, exercise fresh triple-Home emergency; check LG controls and observe a later normal startup without explicit re-enable. | Recovery baseline is preserved; LG is usable; Off/emergency remains Off. Do not manually edit continuation records, receipts, failsafes or deadlines to make this pass. |
| P07 — distinct power states, #415/#427/#428 | Record a separately timed agreed longer standby/wake. Separately perform an owner-approved AC cold boot where safe. Do not interrupt an update or unresolved recovery. | Affected edition routing, remote responsiveness and explicit stopped-state persistence behave as documented. Record whether uptime reset. Remote off/on, standby and AC cold boot are different cases; none substitutes for another. |
| P08 — signed Root update / genuine startup health, #421/#427 | Use the selected signed complete candidate, exact retained rollback baseline and legitimate updater. Observe early launcher startup and the normal restored-profile/presented-frame health path. | No premature fabricated health or refused profile acceptance. Valid final profile/tiles/frames complete the update and preserve settings/Home behavior. Verify exact rollback and forward transition using supported operations. Permanent refusal, transaction mismatch and service-loss injections remain synthetic. An unpublished QA offer is not public-feed verification; mark the actual public-feed case pending until it exists. |
| P09 — Root visible/new icon budget, #423 | Existing suitable catalog that exhausts the fixed budget; record the condition privately. Check visible tiles, then add a previously omitted-icon app via the picker. | Visible apps receive icons first; newly pinned icon refreshes without restarting Home or breaking focus. Fixed limits/fallback remain usable. Do not install unrelated apps merely to fill a catalog; if exhaustion cannot be exercised physically, retain packaged synthetic coverage and mark that condition UNTESTED. |
| P10 — legacy and modern clock, #429 | Available legacy WebKit device, plus representative modern 12-hour/24-hour locale settings. | Legacy clock is compact HH:MM without seconds/GMT overflow; modern locales retain appropriate hour/minute presentation. Missing legacy hardware is a limitation; browser missing-Intl simulation is supporting evidence. |
| P11 — applicable removal/reinstall path, #424/#431 | Only an existing safely prepared lab state or separately approved owner recovery. Select applicable never-activated Root/Home-API-unavailable removal, interrupted removal continuation, running-Helper stop/recheck or legacy-Updater-remnant removal. Do not manufacture corrupted state or replay a reporter recovery for coverage. | Same approved target/host pin/goal and original evidence survive retries. Unknown processes/shortcut/terminal results cannot become verified-clean. Full restart is required when warranted; only proven initially empty No-root can skip it. Root removal is separately confirmed; cleanup precedes explicit new setup; no automatic reinstall. Record unselected branches, restart state and final verified-clean versus incomplete result. |
| P12 — bounded usability sentinel | During the same successful changed-control/update session, launch the chosen app, check audible playback, responsive input and stock Home recovery. | No loss of audio/control/recovery. This is a regression sentinel, not universal device compatibility or acceptance of every untouched subsystem. |

## Validate automatically or synthetically; do not create extra TV failures

| Source PRs | Exact packaged-path evidence to produce |
| --- | --- |
| #426 | Required catalog failure still blocks; optional input failure still warns. Actual packaged Node reader → installer → report preserves only fixed categories/bounded Luna codes and clears stale details. |
| #430 | Recovery refusal projection retains fixed stage/reason, not-run versus pending and original first/latest failure. Eligibility, remote calls/order and success markers remain unchanged; it creates no wholly passive diagnostic command. |
| #432 | Synthetic restoration failures retain original receipts/inverse/fences and exact exception identity; package removal never starts after failed control restoration. Producer/host/history/export retain only allowed cleanup_step values. |
| #433 | Controlled host/loopback/synthetic Windows socket causes become fixed sorted unique categories. Reports/history contain no addresses, exception prose or credentials. No new retry, auth/trust bypass or device probe. Native Windows ARM64 evidence remains separately identified. |
| #429 | Compiled clock missing/broken-Intl fallback and both 720p editions/13 locales; aggregate icon counters/history/privacy, including coexistence with Root recovery/inventory diagnostic fields. No icon admission/download-policy change. |
| #431 | Desktop/Android connection-help and selected-key retry preserve target/trust; Back cannot abandon running work. Controlled process/EIM fixtures keep uncertainty and pending cleanup. Use browser/emulator/packaged host tests where available; no physical failure is required solely to export a category. |

## Bounded owner session and current disposition

Current session establishes maintainer ownership and full authorized QA on C3
OLED55C3RLA, firmware43.21.71/SDK11.2.0/Node20.12.2, Magic Remote exact model unknown,
macOS ARM64. The owner delegated autonomous publication after the selected checks.
The original prospective case library above is retained; final selected cases and
limits are in the [artifact-bound acceptance](2026-11-08-release-1.13.0-artifacts.md).
Final build is42491346675:1 from21fe6718. Other devices need their own admission.

**Phase A — pre-dispatch P00 (15 minutes plus normal package operations):** only
on an explicitly selected maintainer/project test device with a healthy existing
recovery path and no competing active Root/No-root control, verify the published Home 1.13.1 FHD (or separately selected HD)
with source-built Helper 0.8.0. Use normal same-app package installation and the
published Home's Start Helper confirmation; observe actual Home-control status,
short physical Home and fresh triple-Home escape with usable LG controls. Restore
the agreed Home/profile through supported operations. Do not launch a controller
directly, clear emergency markers, edit roles/receipts or add permissions. Capture
actual installed public-file hashes, terminal operations and device/runtime/UID
context privately; publish only the redacted result within authorized QA scope.
Commit a truthful `native/helper-rollback-compatibility.json` naming the exact
canonical candidate archive and published package hashes, then run
`verify_helper_transition` against those same retained packages. Failed/unknown
operations stop dependent work. This is compatibility evidence, not complete OTA
or fresh stock Developer Mode acceptance.

**Phase B — after the final successful complete build:** select applicable
P01–P12 in advance. Budget one 25-minute Root session for P05/P06/P08/P09/P12,
one 20-minute No-root session for P01–P04/P10/P12, and a separately agreed
standby/cold-boot interval for P07. Select P11 only for an existing suitable lab
state or separately authorized recovery; do not manufacture a failure. Defer
unavailable remote, legacy hardware or exhausted-catalog conditions explicitly.
An unpublished signed QA update can support the selected update path but cannot
pass the future public-feed check. Finish safe independent rows and consolidate
all failures before any new product-fix batch.

| Case | Current result | Blocking prerequisite / actual result |
| --- | --- | --- |
| P00 — published Home/new Helper | PASS | Exact Helper0.8.0 canonical archive, published Home1.13.1 UI/confirmation, non-root controller,203 public files, physical short/triple Home and LG controls; committed before full dispatch. |
| P01–P02 — stock IR/queued IR | NOT SELECTED | No eligible stock Developer Mode/standard IR test setup selected; compiled/native safety coverage and explicit reporter follow-up remain. |
| P03 — Magic Remote regression | PASS, observed scope | P00 short Home/escape and arrows/volume; other remotes untested. |
| P04 — repeated Helper wake | NOT SELECTED | Final Helper closing-socket/Stop fixtures plus actual P00 stop path; Root power results do not accept Helper standby. Original-device confirmation remains requested after release. |
| P05 — Root startup/Home | PASS, observed scope | Final Root remote off/10s/on, repeated app-to-short Home; AC30s cold start then app-to-short Home returned Root. LG initially appeared as reported. No exact kernel-event timing claim. |
| P06 — Root emergency | PASS, observed scope | Fresh triple Home during use after cold start opened LG; later Home stayed LG, disabled intent read back. A further Off-state cold boot was not repeated in this final session. |
| P07 — power | PASS, selected intervals | Final Root remote10s wake and AC30s cold start (uptime1885.04→114.43); extended standby/Helper power and universal power compatibility not claimed. |
| P08 — signed Root update/rollback | PASS | Exact full-build signed components, original retained System1.2.5, genuine forward/rollback/forward, normal health/terminal/readback and original profile/theme. Public downloads/feeds verified only after publication. |
| P09 — exhausted icon budget | NOT SELECTED | No suitable existing exhausted catalog; no apps installed to manufacture it. Packaged synthetic cases pass; C4 reporter acceptance remains separate. |
| P10 — legacy clock | NOT SELECTED physically | Full compiled/browser/exact legacy runtime checks; current modern C3 preliminary clock result only, no unsupported legacy-device claim. |
| P11 — removal/reinstall | PASS, selected C3 goals | Root/No-root ordinary full removal, requested software restarts and same-goal continuation with current shared source; The special missing-Home-API/pre-activation reporter branch was not physically selected; reporter-specific recovery and other branches were not manufactured. |
| P12 — usability sentinel | PASS | Final C3 audible video and Home/emergency after cold boot; Magic arrows/volume observed in P00; original profile/theme and actual renderer verified through signed roundtrip. |

For each selected case retain a single result row with date, model,
firmware/webOS/runtime, remote, edition, host, versions, final run:attempt,
package hashes, preconditions, expected/actual result, PASS/FAIL/BLOCKED/
NOT SELECTED/UNTESTED, problems, attempted resolutions and observed outcomes.
Do not copy private connection or diagnostic data into this table.

## Result sheet

For every selected row record **PASS / FAIL / BLOCKED / NOT SELECTED / UNTESTED**,
expected versus actual result, exact artifacts and device/state preconditions,
problems, attempted resolution and observed outcome. Link dated observations;
do not replace failures with a pass from another device or different packages.
One TV and a successful package install do not establish the remaining cases.

# C3 preliminary case pass before the next fix batch

This is authorized maintainer QA on the owner's C3, dated 2026-11-08. The owner
selected the complete available case pass before fixes, then authorized unattended
checks, the consolidated fix batch and preparation of a replacement candidate.
It is not acceptance of a frozen full candidate or permission to publish a release.

## Device, artifacts and retained state

| Field | Actual value |
| --- | --- |
| TV | OLED55C3RLA |
| Firmware / SDK-webOS | 43.21.71 / 11.2.0 |
| TV Node / installation access | 20.12.2 / saved pinned Root SSH, UID 0 |
| Remote | LG Magic Remote; exact model unknown. Xiaomi Mi Box remote available but untested |
| Installer host | macOS ARM64; source cytv 0.14.0 |
| Source | `f79154cdfdad970a84af3ce00fe030723b1c61f1`, including implementation PRs #435 and #436 |
| Original components | Root 0.13.1, Root Updater 0.5.3, retained System 1.2.5 |
| Tested new components | Preliminary Root 0.13.2, Root Updater 0.5.4, fresh System 1.2.7 |
| P00 targets | Published Home 1.13.1 FHD and preliminary Helper 0.8.0; installation stopped before either package submission |

The prepared Home IPK SHA256 is
`c97ef89997bff27836a060c8c62ff85412bb08ec727d17414368601b6ff5fc2e`;
Helper IPK SHA256 is
`6116d99281d2f5c21ff192ddb07ce6cbdae4223573999ac0d310d86ace87e0c2`.
Authenticated original restoration bundles, the original profile, appearance
preferences and binary theme cache are retained privately. They are not attached
to this report. The owner clarified that new-version testing comes first; the
original-version return is deferred until the testing/recovery work is finished.

## Complete preliminary case inventory

| Case | Observed result and scope |
| --- | --- |
| P00 published Home / new Helper | **FAIL** at observer preparation after verified Root cleanup. `ENOENT` for the Root SSH public staging ancestor. Original-operation continuation failed at the same boundary. Both slots remained prepared with no package submitted; no physical Helper acceptance or compatibility approval exists |
| P01-P04 No-root input, remote and power | **BLOCKED** by P00 installation. No stock Developer Mode, passive IR, held Home, Helper stop/resume, repeated wake or Mi Box remote result |
| P05 Root startup | **PARTIAL**: two physical app-to-Home short presses returned to the new Root. Actual early-start enabled-intent off/on window was not exercised |
| P06 Root emergency | **PASS for observed scope**: owner made a fresh triple Home gesture; LG Home appeared and subsequent Home presses stayed there. Readback confirmed disabled intent, LG route and intact recovery. Emergency during the early startup interval remains **UNTESTED** |
| P07 power | **PASS for disabled-state cold boot**: owner unplugged/reconnected power; LG Home appeared, Root stayed Off. Uptime reset from 612.14 to 63.89 seconds; the kernel boot UUID was reused. This is not an enabled Root or Helper standby result. Separate longer standby/wake remains **UNTESTED** |
| P08 signed OTA / rollback | **BLOCKED**: no final signed full candidate selected; fresh installation is not OTA, rollback or public-feed acceptance |
| P09 icon budget | **UNTESTED** on an exhausted real catalog. Existing visible icons/navigation were usable; no unrelated apps were installed to manufacture exhaustion |
| P10 clock | **PASS for current modern locale only**: actual new Root UI displayed compact `17:19`; legacy hardware and a second 12-hour locale were not exercised |
| P11 removal / reinstall | **PASS** for ordinary Root full removal, required owner restart, same-goal continuation and final application/service/startup/private absence. Cleanup of the interrupted No-root goal also completed after its requested restart. **FAIL** for subsequent No-root setup as above. New Root fresh install/activation and fresh System bootstrap reached their normal terminal readbacks. Other recovery branches were not manufactured |
| P12 controls/audio | **PASS for observed scope**: owner confirmed arrows/OK/Back, volume and video sound in LG; new Root theme/arrows/OK/pointer/wheel worked; sound worked with both physical Home returns. One C3 is not universal compatibility evidence |

The new Root's real renderer, exact restored original profile and selected theme
were verified after the cold boot. Read-only installation inspection classified
the installed Root as installed. A generic SSH Luna client's protected System
status refusal is a diagnostic caller limitation, not proof that the launcher
is refused. Subsequent live launcher RPC probes did not finish in their bounded
observation window and are **UNVERIFIED**; no roles or client identity were changed.

## Consolidated failure inventory before product changes

1. **Root-to-No-root staging:** the ownership wrapper removes empty capability
   probe leaves. The immutable Root observer creates the public ancestor only
   during `storage-check`, then assumes it exists during `prepare`. The later
   exact successor therefore cannot prepare after genuinely clean removal.
   Do not solve this by retaining obsolete Root data, clearing journals or
   changing the byte-bound observer capsule.
2. **Fresh Root profile capture:** `RootProfile.capture({system:true})` rejected
   `Invalid icon color`. The captured fresh inventory has one empty optional
   color; the strict profile format permits an omitted color but not an empty
   string. This was observed before restoring the original valid user profile.
   It is not established as a regression against the same fresh old-version
   inventory.
3. **Immediate post-bootstrap startup:** after normal fresh System bootstrap and
   an ordinary page reload, Root showed `Denied method call "restoreProfile"
   for category "/"`. The new Root's control was Off with LG routes and intact
   recovery. A full owner cold boot restored usable Root UI. Keep the initial
   failure and restart workaround; the exact registration/client-cache cause
   is not yet established.

QA harness issues are separate: a native async diagnostic timed out while Root
was backgrounded, but the original theme/preference operation later completed
after foreground launch; every saved preference string was read back equal.
The inspector endpoint being absent after boot is not a product failure.
No health, ready/confirm, transaction, permission, role, emergency marker or
destructive-lease record was edited to turn a failure into a pass.

## State at the start of the fix batch

The owner's last physical action was triple Home. Root remains disabled, LG Home
is the destination, recovery integrity is verified and no Root setup/update is
pending. Autonomous UI checks return to LG Home and do not clear emergency Off.
The full-candidate Helper compatibility gate is still unsatisfied. Remaining
physical cases require the owner; preliminary observations cannot replace them.

## Fix-batch verification in progress

The first two findings now have focused regressions and minimal source fixes.
The staging regression executes the original byte-unchanged Root observer and
first failed with the same missing public ancestor as the C3. The capture
regression first failed with `Invalid icon color`; the fix omits invalid optional
colors from the captured copy while retaining strict stored-profile rejection.

Current host evidence: 21 handoff cases pass with one Linux-only native-guard
skip on macOS, including safe repeated prepare and refusal of changed inner
plans/paths/sender/source before any staging creation. Exact Node 0.12.2 passes;
the prior 20-case run also passed exact Node 8.12.0. The profile suite passes.
Installer ran 1,153 cases with six skips; Android ran 44 with no skips. Public
normal/C1/Beta payloads rebuilt and verified. Independent read-only review found
no blocking defect in these two fixes. Broader checks and live follow-up remain
in progress; this is not a frozen candidate claim.

The owner's unattended scope allowed one ordinary software reboot when full
cleanup requested a restart. Uptime reset and the unchanged pinned SSH identity
were verified; the same cleanup goal then reached verified-clean. This is not
an additional physical AC cold boot. The saved old No-root capsule was preserved
inside an explicit cleanup goal, then that goal completed through the related
Root cleanup instead of deleting host recovery history manually.

The corrected Root-to-No-root transition subsequently installed published
Home 1.13.1 and Helper 0.8.0 normally, reaching package, public-file and
configuration readback with no pending operation. One preceding attempt stopped
in Helper preflight before a durable operation or package submission; three
read-only probes then reported stopped and the new normal attempt succeeded.
That initial refusal remains in private evidence. Published UI/controller and
physical Home compatibility are separate; no new compatibility approval was
written on the strength of package installation alone.


## Autonomous follow-up and consolidated fixes

The published Home UI's actual Start Helper action and confirmation were exercised
with Helper stopped through the ordinary installer first. The controller reached
running with four observed UIDs of 5431 (non-root). All 203 installed Home/Helper
public files matched their exact prepared package hashes above; the canonical
Helper archive digest was also checked. This is UI/package/controller evidence,
not physical short-Home, triple-Home, standby or legacy compatibility acceptance.

The newly reachable No-root full removal exposed another failure: minimal inert
Root ownership fences were classified as a live Root installation, even with the
saved Root SSH connection. The same pending No-root removal goal was retained.
The fix permits the existing Root cleaner only after a read-only, native-locked
proof of the exact closed observer, completed predecessor clean fence, matching
current No-root lease, absent Root packages/hooks and inert private directory
inventory. Changed leases, another goal, live/unverified Root and unsafe entries
still refuse. No edition/connection or recovery history is silently replaced.
Node 0.12.2 selects the authenticated Beta cleaner and restores the host payload
selection afterwards. The immutable observer programs remain byte-identical.

On C3 the original No-root goal then completed normally: one requested software
reboot, same-goal continuation and verified application/service/startup/private
absence. A new Root 0.13.2 / Root Updater 0.5.4 package-only installation succeeded
without activating Home control. Before restoring any saved profile, actual fresh
capture omitted the one invalid optional color, preserved the live inventory and
rendered the launcher. Afterwards the owner's original profile and binary theme
were restored through the normal UI APIs and read back equal.

Fresh System 1.2.7 setup first stopped before state creation or package submission.
The snapshot-only diagnostic succeeded, and ordinary installer status confirmed
`system-updater-not-started`; only then was a new normal attempt made. It installed
successfully. The initial pre-install refusal remains unexplained and recorded;
it was not converted into a pass or bypassed by deleting recovery state.

The post-bootstrap `restoreProfile` failure reproduced after ordinary page reload.
Closing Root with applicationManager `closeByAppId` and launching it again restored
the real renderer immediately. This isolates the existing process's LS2 client
grants: registering the new permissions does not refresh that client on page
reload. Setup now closes/relaunches the exact edition launcher after service scan,
without enabling Home, changing emergency state or relaxing permissions. An exact owned-app already-stopped reply permits relaunch, including continuation
after a failed launch. Other refused close/launch operations cannot report
completed bootstrap. The normal resume path retains
its original package terminal and registration proof. The new restart helper also passed on C3 with the actual applicationManager
boundary. The automatic final setup sequence still needs exact rebuilt-bundle
device confirmation.

Final host evidence for the cleanup follow-up: installer 1,160 cases (six skips),
Android 44, handoff 23 (one Linux-only skip on macOS), five No-root dispatch cases,
and exact Node 0.12.2 / 8.12.0 handoff runs pass. Root runtime 1,173 (four skips),
setup 280 and System 132 passed before the final registration fix; System 136
then passed with that fix; seven shared Luna cases also pass. Independent review checked the No-root fence cleaner,
including a caught-and-fixed strict-mode block-function incompatibility on exact
Node 0.12.2. Current-head CI and final bundle observations are recorded in PR #439.

The 13 localized installation guides were reviewed: no new user action or control
sequence is introduced by the guarded cleanup delegation or automatic launcher
restart. Technical cleanup and System setup references describe the changes.
The full-candidate compatibility gate remains unsatisfied; no previous Root
physical Home result is reused as Helper evidence, and no approval JSON is changed.

### Additional fresh-System removal finding

A repeat of full cleanup after fresh System setup stopped at
`unclassified_support_stage`. The first refusal also included two diagnostic
artifacts created by the QA snapshot probe inside installer staging. Those
QA-owned artifacts were preserved separately, without changing product journals;
the same removal goal still refused afterwards. Readback isolated a product
failure: native Python bootstrap had generated top-level `__pycache__` entries
for the staged manifest's installation/package/binding modules. Managed Python
and standalone SSH setup already suppress bytecode; the computer installer's
native path did not.

The installer now passes `-B`. Historical System staging caches can be retired
only when each safe regular cache leaf has a canonical CPython cache filename
matching a top-level Python source in the independently verified bundle manifest.
Unknown cache members still refuse before deletion; bytecode is never imported
or used as cleanup authority. Existing pinned unlink, owner, mode, link and
whole-inventory checks remain. Real native subprocess and `py_compile` regressions
first reproduced both failures and now pass, alongside 73 cleanup regressions and
nine installer System cases. Independent review found no remaining defect.

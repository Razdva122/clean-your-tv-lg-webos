# Root removal, subsequent setup and bounded C3 preparation

## Maintainer requirement and source finding

The maintainer requested a new implementation PR into the current candidate:
successful full removal must permit either edition to be installed again and
leave no active component, pairing key, startup or obsolete installation block.
This is distinct from merely disabling Root Home control.

Source inspection found that No-root over retained Root SSH used a shell probe
which rejected the deliberately retained minimal Root removal journals/locks,
even after verified full cleanup. Root reinstall already had a checked cleanup
handoff. Removing journals by pathname would lose the original exclusion and
old-worker protections. Completed cleanup also needed its destructive lease
retired so an old Remove could not sweep a later Developer Mode installation.

The [implementation contract](../development/CLEAN-REMOVAL-REINSTALLATION.md)
describes final UUID publication, read-only completed retries, explicit new
removal goals and a canonically bound No-root successor. It preserves the
immutable observer source, emergency state, restart, package-terminal and live
absence checks. No storage-capacity workaround or privilege change is included.
The separate Developer Mode permission fix #435 is already integrated; its
capacity and restart-proof limits still apply.

## Actual device observations before implementation

This is authorized maintainer QA on the owner's test TV, with temporary changes
and restoration permitted. No Root uninstall or No-root package submission took
place in this bounded pass. Private recovery material is not published here.

| Field | Observed value |
| --- | --- |
| TV | LG OLED55C3RLA |
| Firmware / webOS SDK | 43.21.71 / 11.2.0 |
| TV Node | 20.12.2 |
| Remote | LG Magic Remote; exact model unknown. Earlier MR23 assumption withdrawn |
| Additional remote | Xiaomi Mi Box remote available; model and behavior untested |
| Initial edition/components | Root 0.13.1, Root Updater 0.5.3, retained System 1.2.5 |
| Installer host | macOS arm64; candidate source cytv 0.14.0 |
| Intended P00 packages | Published Home 1.13.1 with preliminary Helper 0.8.0 |

| Test | Expected / actual result |
| --- | --- |
| Trusted read-only preflight | Saved pinned Root SSH identity; initial Root enabled and existing project operations terminal. No local unfinished operation |
| Ordinary installed Root restore/disable | Root intent disabled, owned override absent, all three checked Home routes LG Home: observed |
| Ordinary No-root preflight | Refused retained Root state before pairing, observer or package work. This refusal is correct while Root is only disabled, not uninstalled |
| Restore original state | Ordinary Root enable; initial enabled intent, owned override, exact original routes and captured Root UI profile equality verified. Initial foreground restored |

One initial diagnostic query used an incorrect Settings category and was rejected;
the corrected exact runtime requests supplied the route readback. This was a QA
harness correction, not a product failure. The full-removal admission defect above
was confirmed from source, not by claiming that this TV had already been removed.

P00 compatibility remains **blocked/unverified**. No Helper/Home install, physical
Home, emergency gesture, sound, standby, cold boot, OTA or rollback result is
claimed by this pass. A project-scoped private recovery backup and authenticated
published restoration bundles were prepared, not restored or publicly attached.

## Host verification and limits

Focused tests exercise current absence, changed support, exact predecessor and
successor bindings, distinct UUIDs, old coordinators/workers, completed readback,
publication-write interruptions, pre-submission continuation, old-capsule
revocation, new explicit removal goals and Root-owned staging cleanup. The real
native gate test delays a detached Node worker and verifies inherited locks and
one subsequent observation without a repeated package worker. Exact Node 0.12.2
executes the ownership wrapper and compiled cleanup/admission fixture.

Filesystem/RPC adapters model fixed TV paths and unavailable ownership metadata;
the worker-spawn/cleanup-proof unit adapters are separate from the real native
flock and existing real detached-observer/vendor-process integration tests.
Host success is not physical compatibility or a claim that a reporter's TV is
fixed. The final implementation PR records actual command outcomes. Full final
candidate packaging/signing and exact-artifact device acceptance remain separate.

Local macOS arm64 verification before PR submission:

- Full installer profile: 1,146 cases passed, two platform skips; browser/runtime,
  payload and continuation checks passed. Final ownership hardening then passed
  all fifteen focused cases on both current Node and exact Node 0.12.2.
- Root removal/simple-removal dependency group: 92 cases passed, one platform
  skip. Source cleanup tail: 46 cases passed, one platform skip, including exact
  compiled Node 0.12.2 and final-fence publication interruptions.
- Actual packaged cleanup tail: 46 cases passed with two explicit exclusions:
  the Linux-only race fixture on macOS and a source-injection fixture that requires
  the unfilled source declaration. The packaged tail's private inventory child is
  modeled; separate real No-root cleanup tests passed 57 cases.
- Complete normal/C1/Beta public payload rebuilt and verified. Current Root
  coordinator/device bytes match their packaged files. Python 3.9 parsing,
  unchanged bound observer byte comparison, formatting and diff checks passed.

The final full TV-runtime rerun passed 1,173 Root cases (three platform skips),
132 System cases and native/service/legacy compatibility checks. Android passed
44 cases. Additional review reproduced a promotion-lock misclassification when
an absent Python parent lets Node reuse fd 4. The fix verifies the expected inode
when present and otherwise ignores that descriptor. Eighteen focused cases pass
on current Node, exact Node 8.12.0 and 0.12.2, with the Linux-only native
guard/worker integration skipped on macOS and required in Linux CI. No TV changed.

Broad runs exposed older test expectations that a completed goal would resweep
new files or reuse its destructive intent. Those cases now require a separate
explicit goal and preserve the historical record. Model tests restage current
support for that new goal because the prior cleanup retired its copy, matching
normal host dispatch. The final broad runtime rerun and CI are recorded in the PR;
these focused corrections do not establish physical acceptance.

The recovery/removal instructions and all thirteen localized guides now explain
the upcoming post-removal setup behavior. Completed historical evidence remains
intact; no raw device data, addresses, credentials or private paths are included.

## Integration

PR #436 merged into `release/next` at `9d4180cf7e0a20bbf2d5c0d7b487ca3c2d036525`
on 2026-11-08 after independent review and successful final-head
[Tests 42474339515](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42474339515):
all eight Linux/macOS runtime shards, both aggregate jobs, browser and optional
Python passed. The real Linux guard/worker integration is selected in installer
shard 3, which passed. Release PR policy and preview build also passed; full-release
and deployment were unselected. This is implementation CI, not a final candidate.

Actual macOS ARM64 console/desktop packaging and embedded 498-file payload/runtime
smoke passed. The frozen console reports cytv 0.14.0 and contains the exact final
ownership wrapper. The native delayed-worker lock case also passed with actual
Node 8.12.0 and 0.12.2 processes. No additional TV changes or physical acceptance
were performed. PR #435 is integrated separately; candidate versions and the
unselected final build/acceptance remain unchanged.

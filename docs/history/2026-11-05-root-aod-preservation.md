# Root AOD preservation investigation — 2026-11-05

## Evidence and limits

[#282](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/282)
contains a B4 follow-up identifying an activation readback mismatch with the AOD
category missing. That is a different device from the original C4 report; the
C4 cause and recovery remain unresolved. The follow-up does not isolate profile
rescan from the subsequent SAM write with independent intermediate readbacks.
No owner-device connection or new installation report was produced here.

Source inspection found two preservation gaps: the published override supplied
only `categories.home`, and activation bypassed `transport.write()` to invoke
SAM `setDefaultApp` directly. Existing trial fixtures updated a copy of the
baseline in memory and did not parse the actual override's nested map.

A host regression now parses the actual published JSON and replaces each profile
property, including the complete categories map. It models the reported destructive
SAM write and the preserving Settings operation. Before the correction, actual
activation failed with `Candidate readback mismatch` and the missing AOD category.
This establishes a source-level preservation defect under that resolution model;
it does not identify the proprietary retail implementation or prove which TV
boundary lost AOD. The correction preserves the full map at both boundaries.

## Implementation

See the [current contract](../development/ROOT-AOD-PRESERVATION.md) for preserved
fields, full Settings readback, version 1/2 recovery and the terminal bridge needed
by retained old runtimes. The complete routing comparison remains strict.

## Validation

- `npm ci` passed (281 dependencies, no reported vulnerabilities).
- Seven new AOD tests passed after observed pre-fix failures: actual publication,
  unrelated profile/settings data, interrupted recovery, terminal compatibility,
  unchanged input maps, malformed maps/invalid destinations and no write replay.
- The diagnostic plan's AOD-preservation test also failed before its correction
  and passed afterward; its nine-test suite passed.
- Existing 62 runtime policy/publication/device tests passed after updating two
  fixtures to publish their journal's actual bytes rather than the legacy constant.
- Independent read-only design and implementation review found no blockers;
  the diagnostic-plan consistency observation was corrected afterward.
- A broad initial run stopped because host Python lacked fonttools. Dependencies
  were then installed in an isolated worktree venv, not on a TV.
- `PATH=<worktree-venv>/bin:$PATH bash scripts/test.sh tv installer setup` passed:
  all selected TV/JS/native checks, 1023 Root tests (397.461 s), 132 System updater
  tests (22.642 s), 234 setup tests (182.407 s), Homebrew checks and 760 installer
  tests (49.710 s; 72 existing optional/platform skips). The earlier missing-fonttools
  run was not counted as success. Full frozen-candidate checks remain separate.
- The actual published `origin/main` recovery module accepted the resulting v1
  terminal record through its original `validate()` and `recover()` functions.
- Final independent review found no material issue; local documentation links
  and `git diff --check` passed. No user controls or setup choices changed, so
  localized guides require no new instructions.

No final candidate, signed package, target-firmware API acceptance, physical Home,
AOD rendering, emergency gesture, controls/audio, standby, cold boot, OTA or retained
rollback acceptance is claimed. Published v1.7.1 remains unchanged. No component
version, release inventory, selected build or release acceptance was modified.

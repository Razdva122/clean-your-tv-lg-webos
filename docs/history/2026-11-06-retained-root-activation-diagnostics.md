# Retained Root activation completion and diagnostic evidence

Related issue: [#334](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/334).
This is source analysis and host verification, not a device installation report.

## Problem and behavior

Recovery could explicitly retry a verified restored activation, but it could not
finish setup with Home off. A failed retry retained the old runtime and blocked
the separate System Updater preparation. New installer code cannot retroactively
add diagnostics to retained runtime files.

After declining activation, a separate default-No confirmation can finish only
an eligible profile-backend activation with disabled intent and restored stock
routing. Existing file, binding, completed/current product and Root Updater
baseline checks run again. The exact prior receipt data is archived privately
before resolving the local activation receipt. No TV file, package or Home state
is changed by this completion. A changed/unknown state keeps the operation pending.
C1 is excluded. Noninteractive execution and `--yes` do not approve it.

The operator can then separately use existing System Updater preparation (if it
is not already present) and a signed complete update. Those original compatibility,
transaction, baseline and rollback checks are unchanged. This is not a force-update
or launcher-only migration and does not certify that the reported device is eligible.

Standard reports now retain runtime status across product checks, mark pre-enable
status as `before-enable`, and classify pending Root activation separately from
`other-edition`. A passive stdlib collector observes the three project app metadata
versions, runtime release metadata and bounded emergency-log categories. These are
observations, not integrity or recovery authority. Collection never executes retained
runtime modules or writes TV files. Optional failures cannot hide the primary error.

A private ephemeral cursor checks file identity and a bounded overlap, including
large logs and complete-line boundaries. New records can be marked `since-enable`;
rotation, truncation or lost/mismatched overlap falls back to `historical-tail`.
Neither scope establishes the first causal error or excludes other TV writers.
Legacy generic failures remain generic. Seven current refusal reasons are preserved
without exporting transactions, boot identities, token values, PIDs, paths, raw log
lines, arbitrary error text or cursor hashes. Export and history revalidate fields.

## Verification

- Red/green tests reproduced loss of runtime status after product checks and the
  erroneous `other-edition` classification before the corrections.
- Red/green tests cover collector export/history privacy and isolation of primary
  enable failure from optional collection errors; pre-enable status timing is explicit.
- Snapshot cases cover legacy refusal, new fixed reason, missing/unsafe metadata,
  symlink refusal, hostile values, passive reads, rotation/truncation, large-log
  append, partial baseline lines and changed same-size file metadata. Independent review found the last two cursor
  gaps; each was reproduced red and corrected green.
- Eight activation recovery cases, eight snapshot cases, four retained-diagnostic
  cases and eight System Updater host orchestration cases pass. The new bootstrap
  case proves pending activation blocks preparation, explicit Home-off completion
  preserves the original receipt, and separate preparation uses its existing flow.
- Three existing real-runtime journal/lock eligibility proof cases pass. Twenty-two
  diagnostic-context cases and sixteen installer localization cases pass.
- Changed modules and the embedded remote program parse with Python 3.9 grammar.
  This is syntax evidence, not execution on that TV interpreter.
- `npm ci` passed (281 packages, zero reported audit vulnerabilities).
- All 502 relative documentation file targets in affected existing guides resolve;
  candidate recovery guidance is present in all thirteen localized guides.
- Independent read-only review has no unresolved actionable findings. `git diff
  --check` passes.

The affected `scripts/test.sh installer setup android` profile exited 0: setup
257 cases, installer 804 cases (75 reported skips), Android 35 cases, plus existing
Homebrew payload/runtime/bridge/UI and installer/continuation checks. Skips were
not executed. This is host verification, not physical update/rollback acceptance.
Final focused checks after the last timing-field refinement passed: 85 operation
cases and 38 diagnostic/context cases.

An initial broad installer run lacked host-only psutil, paramiko and pinned
fontTools. A separate temporary environment installed the repository requirements;
this is a verification prerequisite, not a product change. A recovery fixture was
updated to decline the new separate default-No choice. No test failure was hidden
or used as device evidence.

## Limits and delivery

Shared installer sources require normal desktop/console/Android rebuild and release.
No release/component version, frozen candidate, selected build, signing key,
permission, network endpoint or TV state format is changed. The private host archive
uses the existing receipt mechanism. New strings are translated in every installer
language; recovery/diagnostic references and all thirteen user guides are updated.

No TV was contacted. Test model, firmware/webOS, remote and physical installer-device
acceptance are untested. Home routing, controls, audio, standby, cold boot, update
and rollback on the reported device remain unverified. The original health-context
predicate/cause and successful reporter recovery are not established. Keep #334 open;
these are a guarded continuation option and diagnostic improvements, not proof of a
fixed TV or universal compatibility.

Linux PR CI found immediate inode reuse after file recreation. A same-size rewrite
regression reproduced the ambiguous cursor scope locally; unchanged size now also
requires unchanged mtime/ctime before selecting `since-enable`. Eight final snapshot
cases and the affected diagnostics/recovery/bootstrap cases pass after correction.

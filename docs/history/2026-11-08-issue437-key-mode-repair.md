# No-root configuration permission repair — 2026-11-08

## Scope

Related issue: [#437](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/437).
This is source/host verification for an implementation PR targeting
`release/next`, not a published fix or a reporter-device installation result.
No TV was contacted, changed or tested. No version, candidate inventory, build
selection or acceptance record is changed.

## Expected and observed host behavior

The original published `STATE_CHECK` rejects an otherwise owned pairing key
with mode 0775 before configuration upload. A synthetic reproduction retained
that mode and failed the new update regression. The implementation restricts
only that exact mode to 0640 through the checked file descriptor while retaining
its inode, owner, group and bytes. Read-only checks still reject the original
unsafe mode without changing it.

The real detached-observer/vendor-process host fixture installs once, models
vendor normalization to 0775, then updates. Configuration now completes, but a
retained emergency `blocked` marker prevents automatic Helper launch before its
claim. After a separately modeled explicit review removes that marker, the same
pending operation completes without resubmitting either package. This is not
permission for users to delete an emergency marker manually.

World-writable keys, hardlinks, symlinks and an unsafe companion `apps.json`
refuse without repairing the key. Both immutable observer source strings are
unchanged so compatible existing capsules remain bound to their original bytes.
Root SSH remains outside this repair path.

## Verification

Verification results are recorded in the associated implementation PR after
completion. Host platform: macOS ARM64. Files, identities, package responses and
key data in the regressions are synthetic; no reporter diagnostics are copied.

## Remaining limits

The reported C2 firmware's reason for normalizing permissions is unknown. Actual
reporter-device recovery and Helper access across its different UID/shared GID
remain unverified. Remote model is unknown. Physical Home routing, remote keys,
sound, standby, cold boot, OTA and rollback are untested by this task.

The separate [#438](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/438)
stock-Home launch refusal and
[#440](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/440)
Root inventory failure remain open pending requested read-only evidence. Their
recovery gates are unchanged.

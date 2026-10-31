# v1.5.4 — Themes, Root startup and publication recovery

This is the first public delivery of the fixes prepared for unpublished 1.5.3.
The 1.5.3 draft stopped before signing/upload because the Helper rollback approval
still named an earlier transition. No 1.5.3 stable assets/feed were published.

All 17 inherited changes and component targets are described in
[the 1.5.3 preparation record](RELEASE-1.5.3.md). PR #209 records the maintainer's
explicit acceptance of the exact untested Helper0.6.20→0.6.21 transition and
pins authenticated candidate/rollback hashes. No runtime, signature, trust,
rollback or emergency gate is weakened. Overall release is1.5.4; component
versions remain Home1.6.1, Helper0.6.21, Root/infrastructure0.6.2, Updaters0.3.4,
cytv0.6.1, Android0.5.1/code16 and unchanged System1.1.2.

## Known limitations and acceptance

Home preference can remain disabled after update/rollback (#202). Settings can
retain stale status after emergency/resume (#206): close and reopen Settings,
explicitly enable Change Home, and wait for Clean status. The maintainer deferred
both fixes/retests. The older different-session standby failure (#171) remains
unresolved; new same-session standby and true cold-boot C3 observations passed
first-screen Clean within their exact recorded scope.

[Signed C3 observations](history/2026-10-31-release-1.5.3-signed-root-qa.md) and
[exact Helper approval](history/2026-10-31-helper-0.6.21-approval.md) retain their
artifact/firmware limits. Final1.5.4 bytes must be compared before carrying any
result. Physical No-root Helper transition, additional inputs, uninstall and
physical phone/TV operations remain untested. Partial original reporter issues
are not resolved by diagnostic improvements. Homebrew promotion stays disabled.

A new complete candidate build, exact artifact/signature checks, Android original
signer update and verified publication remain mandatory. The1.5.3 full build is
historical source evidence, not the selected1.5.4 build.

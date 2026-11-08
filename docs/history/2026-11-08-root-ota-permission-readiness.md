# Root startup after a refused OTA profile read

Related issue: [#351](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/351).
The separately approved [device observation](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/351#issuecomment-6717541019)
records the public-update failure and successful automatic rollback. This note
describes source verification, not another device test.

## Failure boundary

`system_updater.cli.handle` checks supervisor integrity and legacy permission
lockdown before profile/status reads. Component replacement repairs registrations
before verification. A read can therefore be refused while startup is waiting.
The observed refusal was `Legacy updater permissions changed; computer recovery
required`; its transient offending bytes were not captured, so the exact
registration writer and equivalence to the original System 1.1.2 cause remain
unproved.

The Root bootstrap previously retried a null profile but sent a rejected read
straight to Recovery. This consumes its one-shot startup even if subsequent
permission/profile checks would succeed. A platform relaunch does not restart
that bootstrap. The regression executes the actual bootstrap and reproduces this
terminal transition with the observed service refusal.

## Bounded handling

Root retries only that exact permission refusal, including before the first
profile/status response, using the existing one-second / 120-retry startup budget.
It never loads the launcher or sends health while reads are refused. A later
profile still passes version, snapshot, known transaction identity, exact tile
and presented-frame checks. Once a permission refusal proves the supervisor
exists, service disappearance cannot fall back to the legacy updater.

Other errors still enter Recovery immediately. Persistent permission refusals
exhaust the shared budget and enter Recovery; alternating null/refused responses
cannot reset it. No supervisor deadline, authorization, permission file, journal,
health receipt or persistent preference is changed. The fix is delivered in Root
UI and does not require replacing a retained System supervisor.

## Verification and delivery boundary

The source regression covers initial and pending profile/status refusals,
permanent refusal, corrupt state, service loss, changed transaction identity,
shared retry exhaustion and real render-gated health. The compiled browser case
uses the normal service bridge with an early null response, a permission refusal,
then a valid snapshot, and checks health after painted frames.

The final signed Root package still needs ordinary public-feed/early-launch
acceptance on hardware. This source fix does not close #351 or certify the
original retained System 1.1.2 configuration. User update commands and controls
are unchanged; `docs/UPDATES.md` and `root-edition/UPDATES.md` were reviewed.

## CI follow-up — 2026-11-08

The Linux/macOS `test-catalogs.cjs` failure reproduced at `d55635a0`:
its source scan found the exact permission-refusal text absent from the Root
catalogs. Added that message in all thirteen languages without changing the
service-match bytes, startup retry policy or catalog assertions. The unchanged
catalog regression now passes (215 messages); `tests/system_updates/profile.cjs`,
`root-edition/ui/test-profile.cjs`, formatting and diff checks also pass.
Updated-head GitHub CI and release-coordinator integration remain separate gates.
No TV operation was performed.

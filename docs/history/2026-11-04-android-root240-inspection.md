# Android original Root inspection for #240 — 2026-11-04

## Existing evidence and unresolved failure

The [latest owner reply in #240](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/240#issuecomment-6612048529)
corrects the installation origin to Android. The owner upgraded Android 0.5.1 to
0.6.0 in place without clearing data; the app still detects `install /
coordinator-submitted` and SSH works. Availability of the original connection,
recovery records and pinned host key is not independently established. Do not
substitute the macOS account/profile described in older comments.

Reported TV: OLED55BX6LB, firmware 04.64.00 / webOS 5.6.2; remote model unknown.
Edition: Root; original component versions unknown. The newer public recovery
report identifies shared cytv 0.7.0 on Linux/aarch64 and SSH exit 127 at the status
driver boundary. The earlier Darwin status/doctor reports are separate evidence;
they do not establish the original Android worker environment.

The original installation and later failed status are different failures. A
working manually invoked private Python does not prove which interpreter the
historical status command selected. Host interpreter selection can fall back to
system Python when no verified retained binding exists, but this is a supported
mechanism, not a proved historical invocation trace. The reports do not contain
the original worker exception; installation effects and cancellation eligibility
remain unknown. Do not relabel a later inspection failure as that original cause.

## Reproduced Android gap and correction

The existing Android recovery action used an ordinary CLI connection before
reading pending state. That connection can use the current form's authentication
choice and persist profile/trust data; password selection removes a saved identity.
The strict original-profile passive reader was available only through an internal
PC script. The Android user needed an equivalent bounded path rather than an
instruction to use a macOS account.

For Root recovery at `install / coordinator-submitted`, Android now:

1. Requires the existing saved Root profile and pending operation. Missing local
   records refuse before connection instead of constructing a replacement profile.
2. Explains the read-only scope and asks the existing default-No confirmation.
3. Under the host lock, revalidates one exact original operation/profile, including
   the saved identity. The current form cannot substitute another imported key.
4. Uses the existing local host pin with `SSH.connect(persist=False)`. No new trust,
   profile, password, identity or authentication retry is saved. Interrupted
   authentication/cancellation stops.
5. Runs only the existing bounded Node reader of the original request/submission/
   worker snapshot and Python binding bytes. It stages no coordinator, executes no
   retained Python and calls no Luna API. Original record bytes are checked again.
6. Offers the existing allowlisted report while retaining recovery-required,
   no-resume and pending state. A read is not successful recovery or installation.

The internal PC script and Android use the same original-profile selector. Other
supported pending Root states keep their existing separately confirmed CLI flow;
No-root and ordinary installation/authentication remain unchanged. The Node
reader and its authority limits are unchanged. No package, Home-routing,
recovery-state, firmware, permission, endpoint or dependency change is introduced.

## Verification

The Android regression initially failed because recovery still entered the
ordinary CLI instead of the original-profile reader. After correction it verifies
original identity/pin/receipt bytes, exact passive command, no Luna/upload,
allowlisted report/retained pending, default-No cancellation, missing original
records/pin, invalid or duplicate operation identity and no authentication replay.

Independent review found a profile-change race before lock acquisition. A new
regression reproduced connection using a stale profile; moving the saved-profile
and unique-operation check under the lock made it refuse before network access.
A separate regression caught untranslated confirmation prompts; the existing
Console reader now localizes confirmation and scope in all twelve installer
languages. Eight Android regression cases and eleven existing passive tests pass. Corrupt or
unknown pending actions refuse before ordinary CLI connection rather than falling
back to authentication/profile writes.

`PATH="$PWD/.venv/bin:$PATH" bash scripts/test.sh installer setup android`
passed 224 setup tests, 671 installer tests (40 optional/environment-dependent
skips), 35 Android tests and 17 Homebrew Python tests, plus selected Homebrew JS
checks. An initial sandbox run stopped at the existing shell PTY fixture because
`/dev/fd` was denied; the appropriately permitted run passed. The local venv lacks
PySide6, so native frozen GUI acceptance is not claimed. After the final Android
guard/presentation refinement, all 35 Android and 11 passive tests passed again.

`node android/tests/maintenance.cjs` passed real Chrome maintenance/recovery
coverage in twelve locales. Independent read-only review and `git diff --check`
passed. Native APK upgrade/signature and physical phone/TV acceptance require a
future exact candidate artifact; no such result is inferred from these checks.
No TV or original phone was contacted. Tests use temporary app-private-style
records and simulated TV transport, plus existing actual-file Node reader tests.
They do not establish physical Android-to-TV inspection or device recovery.

## Delivery and owner handoff

This is source-only, partial #240 work. The original worker failure and device
recovery remain unresolved. Do not promise a completed installation or ask the
owner to repeat install, enable, Restore, removal, runtime preparation or journal
edits. The owner has already agreed to the proposed Android read-only inspection;
do not repeat the macOS/profile-availability question.

The [bounded phone procedure](../../android/README.md#interrupted-root-installation-inspection-unreleased)
requires an exact original-signer rebuilt APK and its reviewed acceptance before
execution. The published Android 0.7.1 APK does not contain this strict path.
A source merge cannot retrospectively repair or establish the owner's old data.
No new execution request or physical result is claimed by this record.

Future candidate packaging must rebuild Android and shared installer tooling.
Version selection, signed builds and publication remain coordinator work. Existing
four-file upgrade evidence does not prove the owner's original SSH pin survived.
Original-device install/removal, controls, Home routing, audio, standby, cold boot,
OTA and rollback are untested here. Any later publication of an owner-device
result still requires that owner's approval of a concrete redacted draft/target.

Reviewed/updated documentation: Android guide, individual Root recovery handoffs,
this record, history index and all twelve maintained localized guides. The Czech
UI supplement is separate from Android installer localization and is unchanged.

## Reviewed source file identities

| File | SHA-256 |
| --- | --- |
| `android/app/src/main/python/android_bridge.py` | `4e1fc4a5e24244bfce802d90ca21c723bc58e7a6161c0353b516ce717d36c4ff` |
| `cytv/root_passive.py` | `994466df88430404ef6dd5f7c9285592f9ad99e01eacb9497ba4abd8de470c99` |
| `scripts/root-passive-inspection.py` | `aea247a42d1a3e549d961bbbe050630858b38807bc7b68f5a2e095d23dbd5ffe` |

These host source hashes identify the reviewed reader path, not a signed APK,
recovery admission, candidate selection or permission for a device mutation.

## Candidate integration

[PR #289](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/289)
merged into `release/next` as `bb7d17cb6b1d0471ee401e0438c09838a496b47e` after exact-head
[CI 41789221689](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41789221689)
passed Linux/macOS runtime/test summaries, browser and ARM optional-Python checks.
Release PR policy, Integration policy and Preview Pages build also passed; deploy
and full-release were correctly unselected. The reviewed implementation head is
`66c78d34916999f069334ee1ffdafde8b01f653d`.

The unfrozen [candidate #281](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/281)
records this partial #240 work without selecting a version, build or acceptance.
The next maintainer action is an exact signed-APK handoff, not a repeat answer to
the superseded macOS question. Original #240 remains open at `status:planned`.

The host checks establish current retained-record consistency and byte
preservation during inspection. They cannot reconstruct record history or prove
that data was unchanged throughout the original installation and prior attempts.
No historical root cause, completed device recovery or public delivery is claimed.

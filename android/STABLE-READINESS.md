# Android stable readiness

Status: **Android 0.5.1 / versionCode 16 is selected for the unpublished 1.5.3
candidate.** Published 1.5.2 contains Android 0.5.0 / versionCode 15. See the
[1.5.3 release scope and acceptance limits](../docs/RELEASE-1.5.3.md). Final
candidate package/signature and upgrade verification remain required below.

For the 1.4.0 release, on 2026-10-27 the maintainer explicitly accepted emulator
verification as sufficient because no physical phone was available. That dated
decision and its results retain their original scope; they do not certify new
candidate bytes. Ship within the documented architecture/runtime limits and
collect community feedback; do not describe missing physical results as passed.

Developer Mode auto-renewal is outside this work. No automatic discovery,
uninstall UI, extra phone architectures or Google Play publication is required
for the first stable installer. Those remain documented limits.

## Existing physical evidence

In [issue #24, comment 6400650506](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/24#issuecomment-6400650506),
`gargaroff` confirmed successful use of v1.1.0 after the Android operation-receipt
fix in [PR #42](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/42). This
is positive Android/No-root setup evidence, not merely an emulator result.

The comment does not give the phone model, Android/WebView version, TV model or
firmware, or a complete controls/recovery test. The TV in the original issue
body belongs to a different reporter. Do not assign that configuration to this
Android success, infer Root acceptance, or close the original unfinished-removal
report. Its `status:needs-info` remains appropriate for the outstanding original
reporter response.

No physical Android result for 1.5.3 is recorded here. Physical device checks
remain follow-up; the dated maintainer decision above and the existing user
success retain their original scope and do not accept new candidate bytes.

## Production package and update identity

- Keep `com.cleanyourtv.android`, the existing app-private storage layout and
  `android/preview-certificate.sha256` unchanged.
- Build `assembleRelease` / `lintRelease`. `BuildConfig.DEBUG` is false, which
  also disables the WebView debugging API used by debug-only smoke scripts.
- Supply the persistent signing identity from the existing protected
  `CYTV_ANDROID_PREVIEW_KEYSTORE_B64` secret. The historical name/alias is retained
  for installed APK compatibility. Never export the key or print its contents.
- Packaging without `CYTV_ANDROID_KEYSTORE` fails. The APK verifier independently
  rejects `application-debuggable`, checks the pinned signer, SDK/ABI/version,
  source provenance and embedded TV payload. The trusted report explicitly
  records `debuggable: false`; final assembly requires that boolean.
- CI compiles `OperationChecks` but does not run it on physical hardware or claim
  device acceptance. The instrumentation APK is not a public release asset.
- A disposable local signer is suitable for emulator checks only. Such APKs must
  fail the pinned public-signer verifier. Do not change the pin to make them pass.

Before publication, verify the final protected-CI APK and its update over a
published preview with the **original** certificate. Local re-signing checks the
same-signer update mechanism but cannot replace this final artifact check.
Never instruct users to uninstall the Android app to bypass a signature error:
that deletes private keys, profiles and durable recovery receipts.

## Native emulator fixtures

Build the debug app and instrumentation APK:

```sh
android/gradlew -p android :app:assembleDebug :app:assembleDebugAndroidTest
adb -s emulator-5554 install -r android/app/build/outputs/apk/debug/app-debug.apk
adb -s emulator-5554 install -r android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
python3 android/tests/native.py --serial emulator-5554
```

The runner uses the real Android `Operation` and JSON implementation. It checks
both edition contexts, refuses a second operation, bounds replay to 450 events,
retains the started event and outstanding prompt across 500 background log
events, rejects stale prompt answers and keeps secret values out of replay.
Detaching the Activity listener models the missed-live-event boundary; this is
not a physical rotation/standby acceptance claim.

The regression failed before the fix with `Pending prompt lost during Activity
replay`. FIFO trimming used to discard the outstanding question; trimming now
protects the started event and current prompt, allowing a recreated Activity to
rebuild the dialog. Answered questions become ordinary evictable events again.

### Preview-to-release and process-death fixture

Use an isolated emulator containing no real TV profiles or keys. The wrapper
requires an explicit `emulator-N` serial and treats a missing success marker as
failure, because `adb shell am instrument` can exit zero after a test failure.

1. Download the v1.1.0 `cytv-android-arm64.apk` into a private test directory and
   verify its original certificate with `apksigner verify --print-certs`; its
   SHA-256 must equal `android/preview-certificate.sha256`.
2. Create a disposable local keystore. For local checks only, re-sign a **copy**
   of that preview APK with it, build the new release APK with the same keystore,
   and re-sign the instrumentation APK with that key as well. Keep the originals
   and never use or publish these test-signed APKs as release assets.
3. Install the test-signed preview and instrumentation APK on the emulator.
4. Run `python3 android/tests/native.py --serial emulator-5554 --upgrade seed`.
   This uses the real Python `Store` in the preview to save a synthetic profile
   and unfinished installation receipt, plus a dummy imported-key file and
   private preference. It performs no TV commands.
5. Force-stop the target app, then use `adb -s emulator-5554 install -r` with the
   new test-signed release APK. Do **not** uninstall between seed and verification.
6. Run `python3 android/tests/native.py --serial emulator-5554 --upgrade verify`.
   It requires a non-debuggable target, retained files/preferences, the canonical
   saved identity path and unchanged pending receipt. A second `Store.begin`
   must refuse the unresolved operation. A fresh process must not replay an
   installation automatically. Only its reserved synthetic fixtures are removed
   after success.
7. Run `python3 android/tests/native.py --serial emulator-5554` against the same
   release target to verify native operation behavior without debug mode.

Android canonicalizes `/data/user/0` and `/data/data` aliases; compare the saved
identity to the key's canonical path rather than interpreting alias spelling as
lost user data. These fixtures do not test actual SSH credentials, network loss
to a TV or a whole-edition TV rollback.

## Physical follow-up and compatibility limits

Record the exact APK hash, signer, source/build and component versions for every
result, with phone model, Android/WebView version, TV model/firmware and edition.
Separate Android installer results from TV runtime compatibility.

| Scenario | Current evidence | Community follow-up |
| --- | --- | --- |
| No-root installation from phone | v1.1.0 user success in #24 | Record device details and verify final candidate |
| Root installation from phone | Not established by #24 | Physical install, status and recovery |
| Published preview update without data loss | Original-signer code11-to-code12 file retention and native Store fixture below | Final candidate code16 original-signer APK; physical update |
| Activity recreation and prompt replay | Emulator idle UI rotation/background return; native bounded replay and browser suites | Rotation/background return during a live phone-to-TV operation |
| Phone lock and denied notification permission | Emulator idle UI checks; foreground service and bounded wake lock in code | Verify operation continuation / clear outcome on actual Android devices |
| Network loss / TV unavailable | Existing negative connection fixtures and recovery UI | Interrupt real transfer; status/restore must reconcile before retry |
| OS process termination | Emulator force-stop and durable pending-receipt fixture | Interrupt physical install; no automatic retry or receipt deletion |
| Supported Android/WebView floor | API 35 emulator and WebView feature gate | Oldest supported Android 7 / WebView 108 and an additional current phone |
| TV controls after installation | Historical edition-specific TV evidence | Final installed candidate: Home, arrows/OK, Back, volume, triple-Home and explicit resume |
| TV power / recovery | Not established by successful package installation | Standby/wake and cold boot separately; status/restore and rollback within supported scope |

For release 1.4.0, the maintainer accepted the emulator-tested scope for suffix
removal. That decision does not accept new 1.5.3 artifacts. The API 24 /
WebView 108 floor remains a declared minimum, not a tested device claim. Emulator
checks, CI success and one successful setup do not establish universal phone/TV
compatibility. Report failures with Android/WebView versions, phone and TV model,
firmware, edition and last completed step; exclude credentials and private logs.

<a id="automated-verification-record-for-this-preparation"></a>
## Historical development verification

- `npm ci` completed.
- `scripts/test.sh` passed: 984 Python tests across the suites (23 skipped for
  unavailable optional/platform coverage), plus the included JS/native checks.
  On macOS the POSIX upload fixtures used the system `shasum -a 256` through a
  local `sha256sum` adapter; product code was unchanged for that environment.
- Android `ui.cjs`, `localization.cjs`, `maintenance.cjs` and
  `connection-first.cjs` passed.
- `assembleRelease`, `lintRelease` and `assembleDebugAndroidTest` built locally
  using JDK 17, SDK 35 and Gradle 8.13. The local release used a disposable key;
  the pinned-certificate verifier rejected it as expected.
- Release packaging without a signer failed with the required-keystore error.
- The pending-prompt native regression failed before the fix and passed after
  it on Android 15 / API 35 ARM64 emulator, for both edition contexts.
- The published v1.1.0 preview certificate matched the pin. A test-signed copy
  updated from versionCode 9 to the test-signed release versionCode 10 without
  uninstalling; synthetic profile, key file, preference and pending receipt were
  retained after force-stop. Reinstall was refused while that receipt was pending.
  Native operation checks also passed on the non-debuggable release target.

These historical development checks predate the current candidate and are not
publication evidence. See the dated emulator record below and the release PR
for final artifact verification. Physical acceptance remains follow-up.

## 2026-10-27 emulator acceptance

Android Emulator 37.2.12, isolated Pixel 6 profile, Google APIs Android 15 / API 35
ARM64 image `AE3A.240806.043/12960925`, WebView 124.0.6367.219.
No real TV profiles, private keys or TV connections were used.

- Exact protected-CI APK from source `1114ccc518d352748f539aa8e44f52a90790ff93`,
  run 40478003842: original public signer update from published v1.3.0 code 11 to
  RC code 12 succeeded with `install -r`, without uninstall. Four synthetic files
  (profile, dummy identity, preferences, pending receipt) retained identical hashes
  after update and force-stop. This checks file retention, not live SSH recovery.
- Original RC UI launched with notifications denied. Portrait/landscape recreation,
  background/return, lock/wake and force-stop/relaunch returned to the Activity;
  screenshots were inspected and the crash buffer was empty. These were idle UI
  checks, not an active installation continuation test.
- Separate test-signed copies of that baseline and candidate, plus the current
  instrumentation runner, passed real Python Store seed/verify across upgrade
  and process death. Pending receipt blocked a second begin without being changed;
  a new process did not automatically resume. No uninstall occurred between
  seed and verify. Disposable signing material is never a release asset.
- Native OperationChecks passed both edition contexts, single-operation exclusion,
  450-event bounded replay, outstanding prompt retention over 500 logs, stale
  answer rejection, secret exclusion and Chinese resource qualifiers on a
  non-debuggable release target.

These checks supported the maintainer's dated suffix decision, not physical-TV
acceptance. For that release, the final 0.4.0/code13 protected-CI artifact required
separate signer, metadata, payload and original-signer upgrade verification; the
code12 results alone could not satisfy those checks. These historical results
also do not establish acceptance of the 1.5.3 / Android 0.5.1 / code16 artifact,
which requires its own exact source, hash and verification record.

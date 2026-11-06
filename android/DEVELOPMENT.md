# Android development

For installing the signed APK and recovery, use the [Android guide](README.md).
This page covers building, signing, fixtures and screenshot evidence.

## Build

Run builds from the maintained project root. Requires JDK 17, Python 3.12, Android SDK platform 35/build-tools 35.0.0/platform-tools and accepted SDK licenses. Gradle 8.13 is pinned by the wrapper; Android Gradle Plugin 8.9.2 and Chaquopy 17.1.0 are pinned in the build.

From the repository root, prepare a public TV payload using the existing build flow (or use an already built, hash-verified `build/cytv/payload`):

```sh
python3.12 -m venv android/.build-venv
android/.build-venv/bin/pip install -r scripts/build-requirements.txt -r cytv/requirements.txt ziglang==0.14.1
android/.build-venv/bin/python scripts/build-cytv.py --payload-only
export CYTV_BUILD_PYTHON="$PWD/android/.build-venv/bin/python"
export ANDROID_HOME=/path/to/android-sdk
export JAVA_HOME=/path/to/jdk-17
cd android
./gradlew :app:assembleDebug :app:lintDebug :app:assembleDebugAndroidTest
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk` relative to the repository root. No release signing material is stored in the repository. The first build downloads dependencies; runtime installation uses the embedded payload. Runtime extraction is cached by the bundled manifest SHA-256, so reinstalling a preview with the same versionCode cannot reuse a different older payload. Staging validates every payload hash and copies only public source modules, excluding Qt/desktop entry points, caches and local profiles. It does not automatically rebuild TV payloads during Gradle execution.

For a release APK, supply the private `CYTV_ANDROID_KEYSTORE` through the protected
build environment and run `:app:assembleRelease :app:lintRelease`. Output is
`android/app/build/outputs/apk/release/app-release.apk`. Release packaging fails
without the keystore. CI uses the existing persistent signer; never replace that
key or the pinned certificate just to remove the preview label. Local builds may
use a disposable test key, but their APKs are not public release artifacts and
must fail the pinned-certificate verifier. Run `android/verify_release.py` against
the final signed APK in the trusted environment. Release WebView debugging is
disabled through `BuildConfig.DEBUG`; debug instrumentation is not bundled into
the public APK.

Python dependencies are resolved normally against PyPI and the official Chaquopy wheel index: Paramiko 3.5.1, websockets 15.0.1, cryptography 42.0.8, bcrypt 3.2.2 and PyNaCl 1.5.0. Python 3.12/arm64 is used because its available bcrypt wheel satisfies Paramiko's minimum version; dependency constraints are not bypassed. These versions are the available Android package combination, not a claim that all packages are the latest upstream versions.

## Checks and screenshots

```sh
# Repository Python dependencies must be installed in the chosen interpreter.
python3 -m unittest discover -s android/tests
bash scripts/test.sh
# Requires Playwright and a local Chrome; CYTV_CHROME can override its executable.
node android/tests/ui.cjs
node android/tests/localization.cjs
node android/tests/maintenance.cjs
node android/tests/recovery-journey.cjs
node android/tests/removal-result.cjs
node android/tests/simple-removal.cjs
node android/tests/restart-result.cjs
node android/tests/screenshots.cjs
```

Native operation fixtures run separately on an emulator after installing the
debug APK and `android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk`:

```sh
python3 android/tests/native.py --serial emulator-5554
```

This checks both edition contexts, duplicate-operation rejection, bounded replay,
pending-question retention and stale-answer rejection. It also checks that secret
answers are absent from replay. `--upgrade seed` and `--upgrade verify` exercise
synthetic private-data and unfinished-operation retention across an APK update;
see [the upgrade procedure](STABLE-READINESS.md). These fixtures do not connect to
a TV and cannot establish physical installation compatibility.

The localization suite checks all twelve complete candidate catalogs, system-language resolution, the current-language picker, saved selection, preserving connection fields, localized native requests and progress, and returning from recovery to a fresh installation. Operation logs and the foreground notification use the language selected when the operation starts; changing the interface language does not rewrite earlier logs.

The browser suite covers both editions, IP/port/key validation, explicit trust, secret isolation, error recovery and widths 320/375/412/768/1024. Files `screenshots/01-*` through `05-*` show the same offline UI in browser demonstration mode, clearly labeled; progress and completion there are simulated.

The `screenshots/android-language-*` files and `android-languages-overview.png` show the actual APK language picker and Russian, German, Korean and Hindi screens. Run `node android/tests/languages-emulator.cjs` against the same forwarded debug WebView to check all twelve candidate languages and recreate them.

Files `screenshots/android-*` are screenshots of the actual debug APK on an Android 15 ARM64 emulator. Native smoke checks reached the real Python No-root code/passphrase request, then tested the recovery result for an unavailable synthetic Key Server. The Root negative SSH fixture checked the real fingerprint confirmation and hidden password callback, then rejected an intentionally invalid synthetic password. It never executes TV commands. These checks do not establish successful hardware installation.

For native smoke tests, forward the APK's debug WebView socket (`adb shell cat /proc/net/unix` identifies `webview_devtools_remote_PID`) with `adb forward tcp:9228 localabstract:webview_devtools_remote_PID`. Run `node android/tests/emulator.cjs` with `CYTV_ADB` set to adb's path. For the Root negative fixture, run `python android/tests/root-handshake.py` first, then set `CYTV_TEST_ROOT=1` for the Node command. To avoid an older fixture’s remembered host key, set a fresh `CYTV_TEST_SSH_PORT` in both commands. Start the app on its Russian welcome screen with no operation running. WebView debugging is enabled only in debug builds; it is disabled in release builds.

## Maintenance connection continuity in 1.3.0 (issue #12)

Since 1.3.0: after Done returns to the start screen, Tools retains the
selected TV, edition and SSH port. No-root keeps port 9922; a custom Root port is
also retained. Status, restore and Home button diagnostics no longer inherit the
start screen's old hard-coded port 22. Home Helper recording remains No-root only.
This UI change is not in the published v1.2.0 APK.

Regression coverage drives a full install-result → Done → Tools → action flow
for No-root and custom-port Root. A TCP connection failure does not establish
that the Developer Mode passphrase was wrong. The report attached to issue #12
records action status and phase ssh-connect; the exact reporter path/port still
needs device confirmation.

## Historical Android delivery evidence

The historical **v1.2.0 APK was a preview/debug build**. A user confirmed successful Android setup with v1.1.0 after the operation-receipt fix in [issue #24](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/24#issuecomment-6400650506). The comment does not identify the phone, Android version or TV configuration; do not attribute the original issue author's TV to this separate reporter. Full physical-phone acceptance for **both editions**, including recovery, remains outstanding. The 1.3.0 preview uses a non-debuggable release build with the existing pinned signing identity; [acceptance and evidence](STABLE-READINESS.md) records the scoped decision for the next candidate.
## Operation lifecycle

Activity recreation replays the current operation and pending question. Pending
questions time out after ten minutes; the foreground wake lock is bounded to
25 minutes. OS process/service termination can interrupt networking; retained
receipts remain authoritative. Status and restore display their own operation
progress without installation steps.

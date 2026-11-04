# No-root Ribbon prototype

Standalone, unreleased Developer Mode window experiment. The default build is
the original three-control static probe. The optional real-Ribbon build below
uses the project's actual shared Home renderer and Ribbon theme. Neither is a
production Home integration or compatibility claim. Build and automated tests
do not install or connect to a TV.

## Scope

- Separate app ID: `com.cleanyourtv.lab.norootribbon`, experimental version `0.0.1`.
- Requests `defaultWindowType: overlay`, transparency, relaunch handling and
  splash/spinner suppression. These window hints are not a supported public TV
  overlay contract; firmware policy may reject or suppress the window.
- No service, permissions, network, app inventory, media, wallpaper, storage,
  Helper change, startup hook, Home category or routing write.
- Ordinary launch uses an opaque static fallback. Launch parameters
  `{"mode":"overlay"}` explicitly request transparent mode; missing, malformed
  or unknown mode stays opaque. This is a manual choice, not content detection.
- Left/Right wrap between Overlay, Fullscreen and Close panel; OK activates the
  focused native button. Pointer and Tab work too.
- Back (461), Escape, Close panel and another `webOSRelaunch` request self-close.
  The absolute 60-second lifetime is never extended by input or relaunch.
  Physical Home is not intercepted: repeat **app launch** models a future
  Helper-driven toggle. Pressing the real Home key retains platform behavior.

Fullscreen is an opaque drawing in the same overlay window, not a separate card
app. Underlying lifecycle/audio may continue. The app uses no decoder even in
fullscreen. A compositor that refuses overlay windows cannot be rescued by the
opaque background. Self-close and the timer depend on the web app running;
neither replaces Helper's independent emergency/watchdog. A browser may refuse
to close a tab opened by the user; the document hides its panel on that request.

## Local build and verification

Run from the repository root:

```sh
npm ci
python3 prototypes/no-root-ribbon/build.py
node tests/no-root-ribbon-prototype.cjs
```

The browser test uses installed Chrome by default; set `BROWSER_CHANNEL=chromium`
to use an already installed Playwright Chromium. It loads the **compiled** app,
simulates only the platform activation/close calls, and exercises navigation,
opaque defaults, explicit overlay, dismissal and the lifetime boundary. These
are host tests, not TV video/audio/focus acceptance.

Build outputs:

- `build/no-root-ribbon-prototype/app/`: compiled local preview.
- `dist/no-root-ribbon-prototype/com.cleanyourtv.lab.norootribbon_0.0.1_all.ipk`.
- `dist/no-root-ribbon-prototype/SHA256SUMS`.

The build reuses the repository's Babel/PostCSS/ES5 compatibility compiler,
deterministic IPK writer and Home icon. No additional dependencies are needed.
Only an explicit file list plus generated local compatibility assets is packed;
the application has no install/remove scripts or service payload.

For a visual preview, open the compiled `index.html` on the computer. Its exact
query `?mode=overlay` selects transparent mode when no TV system object exists.
The browser background is not an underlying TV application.

## Later device gate — not executed

Coordinate a separately authorized session before installing or launching this
package. Keep the real Home/Helper packages and routing unchanged. A direct
launch without parameters should show the opaque screen; an explicit overlay
launch should expose the current picture outside the bottom panel. Relaunch
should dismiss, not replace/restart the underlying content app.

Check cold and warm launch separately over HDMI, Live TV and a native video app:
moving picture, sound continuity, loading/black frames, navigation, Back,
relaunch, 60-second expiry and underlying focus after close. A launch reply is
not proof of a visible window. Recovered playback is not uninterrupted playback.
Activation/visibility event ordering, actual Home integration and content
classification are outside this prototype's host evidence.

TV model, firmware/webOS, remote and installer platform: **not tested**.
TV installation, video/audio, standby, cold boot, OTA and rollback: **not tested**.
Browser/platform simulation does not establish pristine No-root compatibility.

## Real Ribbon mode — 0.0.2

```sh
python3 prototypes/no-root-ribbon/build.py --real-ribbon
node tests/no-root-ribbon-real.cjs
```

Use the project's build Python environment with
`scripts/build-requirements.txt` installed (fonttools 4.60.1). Normal font
preparation may download pinned, hash-verified sources on the build computer.
It never installs dependencies on the TV.

This reads committed project source revision
`68fb76cc47951fad304d25b147efc9db2da41229` through a temporary Git archive,
without checking out or editing the other feature branch. That commit must be
available locally. The existing TV development staging adapter supplies the
shared Home/Ribbon renderer, real bundled theme/assets, and public reference
app cards. Its Root-specific service/settings UI remains simulated; there is
no Root runtime, elevated service, or production profile in the lab package.
Native window activation and self-close are captured by a small host before
the product's service APIs are replaced and locked. The pinned source revision
is included as `lab-source.json` in the package.

The real build keeps the separate lab ID, sets version `0.0.2`, empty ACG, and
overlay metadata. It uses its own `cytv.lab.norootribbon.` storage namespace.
The simulated content background is removed. Wallpaper playback is suspended
for the entire session, including settings/fallback; CSP also rejects media.
Application launches, updates, Home control and system settings remain mocked.

Unlike the static probe, actual Ribbon/controller semantics apply: Back first
closes an open dialog or Settings, then dismisses unobstructed overlay navigation.
Relaunch dismisses a visible unobstructed overlay; opaque fallback/modal/hidden
activation may show it instead. Physical Home is still not hooked. The host's
absolute 60-second lifetime remains the bounded exit; it is not an independent
watchdog if the web engine stalls. Context is an explicit launch parameter,
not a compositor or SSAP observation.

Outputs are `build/no-root-ribbon-prototype/real/` and
`dist/no-root-ribbon-prototype/com.cleanyourtv.lab.norootribbon_0.0.2_all.ipk`.
The compiled-app browser regression verifies real cards/navigation, opaque
settings, Back and unobstructed relaunch, the lifetime boundary, disabled native
service calls, and absence of synthetic content/wallpaper video. A separately
authorized physical session is recorded only in the local private task record;
it is not automatically published or counted as release acceptance.

## Host verification — 2026-11-04

The existing web compiler regression and 11 compiled-app browser scenarios
passed. Archive inspection found exactly eight allowlisted files, with no
services, privileged metadata or install scripts. Two builds produced identical
IPK bytes. Visual inspection at 1920×1080 found the panel inside the bottom safe
area, with visible focus and no horizontal overflow. Independent source review
found no actionable issues. All system activation/close calls in the browser
suite were simulated; no TV result is recorded.

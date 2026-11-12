# Fast TV development

These are source-checkout maintainer tools. Run from the source checkout with Node.js 20.19+, Python 3.9+ and the existing dependencies:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 -m pip install -r scripts/build-requirements.txt
python3 scripts/tv-dev.py --help
```

Choose the feedback path that matches the change. UI staging tests rendering and
navigation with simulated TV APIs. Direct signed Root QA tests a real package set
through the installed updater after explicit owner authorization. Neither path
satisfies final release admission; follow [Release flow](../RELEASE-FLOW.md) for
full frozen-source checks, pinned builds, physical acceptance and publication.

## Reproduce firmware-dependent bugs offline

Start with the reporter's model (including its regional suffix), firmware,
webOS/SDK version, CYTV version, failed operation and first recorded failure.
Use the diagnostic or existing observations to identify the smallest boundary
to test: a factory setting, filesystem layout, native command, or service reply.

1. **Locate the image.** Search LG's support page for the exact model and
   firmware. Check the archive's applicable model list and record the source
   URL, model, firmware, platform/build identifier and SHA-256. If the exact
   image is unavailable, choose a comparable image using the platform and the
   component under test. Record what matches and what differs before using it
   as evidence. An available SDK emulator can exercise web app behavior.
   Factory firmware behavior requires evidence from the image or a device.
2. **Inspect the files.** In a disposable workspace, verify ZIP integrity and
   extract the EPK with a reviewed, pinned extractor. The previous LG image
   investigations used [epk2extract at a pinned revision](https://github.com/openlgtv/epk2extract/tree/a0ccd8a4b4f48d05675a4cddd233f8780ee36767)
   with `epk2extract -s -n firmware.epk`, then `unsquashfs -ls` and
   `unsquashfs -cat` for the specific files in the root filesystem and BSP
   partitions. Record the signature verification result separately from
   extraction success. Keep archives and vendor files outside Git. If the
   available tools cannot read the image, record that blocker and continue
   with the accessible factory files, prior evidence, or a bounded fixture.
3. **Run only the component you need.** Check the executable's architecture,
   ELF interpreter and library dependencies with `file` and `readelf`. In an
   isolated Linux container or VM, mount the extracted filesystem read-only,
   disable networking and run selected binaries unprivileged. For a 32-bit ARM
   image, use `qemu-arm -L "$sysroot"` with the image's own loader and libraries.
   Recreate only the relevant filesystem or process condition inside the
   disposable environment. For example, with `/tmp` already mounted as `ramfs`
   inside the test environment, run the stock BusyBox applets:

   ```sh
   qemu-arm -L "$sysroot" -E LD_LIBRARY_PATH="$sysroot/lib:$sysroot/usr/lib" \
     "$sysroot/bin/busybox.nosuid" df -Pk /tmp
   qemu-arm -L "$sysroot" -E LD_LIBRARY_PATH="$sysroot/lib:$sysroot/usr/lib" \
     "$sysroot/bin/busybox.nosuid" stat -f -c %t /tmp
   ```

4. **Replay the failure.** Feed the actual files or command output into the
   affected CYTV release and compare the failure stage, reason and trace. Use
   the same inputs with the candidate and include a control where it helps
   isolate the cause. If a live service such as `configd` is needed, model its
   reply or state transitions and say which values are simulated. Record the
   source revisions, image and tool versions, commands, observed result and
   remaining device-only questions. Factory files show defaults. QEMU user mode
   runs individual processes on the test kernel. A replay can verify a code
   path while leaving the reporting TV's live state and hardware behavior open.

Prior examples:

- [#101](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/101):
  C2 04.40.90 factory files and a modeled mount table reproduced an installer
  rejection of the stock BSP overlay.
- [#541](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/541):
  stock ARM BusyBox in QEMU reproduced the zero `df` output and `ramfs` type,
  which were replayed through CYTV's storage check.
- [#389](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/559):
  the C1 03.53.45 factory filter chain passed. Adding an old CYTV filter in
  modeled `configd` reproduced the reported removal stage and trace.

## Compile UI without a TV

```sh
python3 scripts/tv-dev.py ui --stage-only
```

The output defaults to `build/tv-dev-ui`. A custom `--output DIRECTORY` must be
separate from sources. The command refuses symlinks and existing directories it
did not create. It compiles the current Root UI through the ordinary Chromium 38
Babel/PostCSS/ES5/CSS gates, using the public preview inventory and mock bridge.
It needs no webOS CLI or TV connection. Offline staging requires npm/Python build
dependencies and the verified Chinese font source cache from a prior preparation;
see [automatic font preparation](../TV-WEB-BUILD.md#chinese-ui-fonts).
Compilation failures preserve the previous successful output.

The staged metadata uses `com.cleanyourtv.dev.ui`, without Home category or
privileged ACG permissions. Its ordinary opaque CARD window delegates activation
and relaunch to webOS, matching the current single-Home window contract. LocalStorage and IndexedDB access use the
`cytv.dev.ui.` namespace, including when a hosted CLI reuses its own origin.
The native bridge is disabled before loading the preview simulation, then the
mock is locked against replacement. A single bootstrap loads product scripts only
after isolation succeeds; a readonly native API stops startup safely. `webOS.service.request`, PalmSystem and
webOSSystem cannot reach native services. CSP permits same-origin bundled assets
needed by the theme engine, permits validated blob images and blocks connections
to external endpoints;
settings, launches, Root activation, audio and firmware actions are simulated.
Bundled video wallpapers use their verified local MP4 files in this UI-only
package, rather than the disabled native media-cache service. External/personal
media retains the browser Blob fallback and may depend on the TV decoder.
No Root service, updater, startup hook or Home routing configuration is staged.

`com.cleanyourtv.root.preview` is the **production Root app ID**, despite its
name. Never install the historical Root preview staging to speed up UI work.
Use this entrypoint instead.

## Reload compiled UI on a TV

Use an already configured, trusted named webOS CLI device with the owner present:

```sh
python3 scripts/tv-dev.py ui --device lgtv --owner-present --watch
```

This runs `ares-launch --hosted build/tv-dev-ui -d lgtv`. The TV and computer
must be able to reach each other over the development network. The command does
not pair, discover a device, replace a connection key or configure Home routing.
It watches the UI, fonts, preview fixtures and compiler sources, debounces edits
and compiles a complete generation. A successful rebuild stops the hosted
process, replaces the managed directory, then relaunches that complete generation.
A failed compile keeps the last running generation. Ctrl+C stops the host process.
Without `--watch`, the initial compiled generation remains hosted until stopped.

LG's [CLI developer guide](https://webostv.developer.lge.com/develop/tools/cli-dev-guide)
documents the SDK container ID `com.sdk.ares.hostedapp`, automatic reload from CLI
1.12.0 and the exclusion of JavaScript services. Thus the actual hosted container
has the SDK's identity while the staged app metadata retains our separate dev ID.
Keep the extra storage namespace even when the SDK origin is reused. The CLI can
install or reuse its SDK container; this is still an explicit device operation.

Use the real TV renderer to inspect text, geometry, focus, remote navigation and
animation. UI preview does not verify real app launching, services, physical Home
control, sound recovery, standby, cold boot, OTA or rollback. Record those as
untested until exercised on the appropriate real package candidate.

## Dispatch and obtain signed Root QA packages

Use authenticated GitHub CLI with access to the repository's Actions and protected
signing environment. Select a committed named branch, exact 40-character source
SHA and the numeric unpublished release version in that source's frozen plan.
The release must advance the stable baseline. This command never connects to a TV:

```sh
python3 scripts/tv-dev.py candidate \
  --branch release/next --source-sha EXACT_40_CHARACTER_SHA --tag vX.Y.Z \
  --output work/private-tv-qa
```

The entrypoint dispatches `tv-candidate.yml`, waits for its exact successful source,
then uses the existing candidate admission inspector. The direct artifact contains
Root IPK, Root Updater IPK and Root infrastructure archive with source, versions,
run/attempt and public-key provenance. Affected runtime checks run before artifact upload. Desktop and Android executables
are not prerequisites for this preliminary TV payload build.

It dispatches protected `publish-release.yml` tools on `release/next` with
`publish=false`, `preliminary_root_qa=true` and `direct_tv_qa=true`, waits for
signing, and downloads the exact signed artifact. Protected signing verifies the
archive without executing candidate source with signing credentials. The host
checks Actions digest/size/source/attempt, flat inventory, production RSA signature,
source-bound notes, public-key hash, all three versions and package hashes, then
rechecks the selected build and signing artifact. No private signing key is needed
on the computer. No stable release, feed or shipping notice is published.

The signed artifact is named
`signed-root-candidate-BUILD_RUN-BUILD_ATTEMPT`; its own Actions provenance points
to the separate **signing** run. `DELIVERY.json` retains that signing receipt
alongside the six original signed files. Keep the directory private and unchanged.
A verification failure leaves diagnostic evidence without a verified receipt;
do not install it.

To resume after a wait/connection interruption without dispatching another build,
select the original `--run-id BUILD_RUN`; add `--sign-run-id SIGNING_RUN` if signing
already started. Use a new `--output` directory. Ambiguous concurrent dispatches
stop rather than guess a run. A changed branch, attempt or artifact requires
review and a new selection; the tool does not silently follow a newer source.

## Select device checks and owner actions

Use the smallest case set that can establish whether the changed behavior is
safe to ship. Record the changed input, expected behavior, artifact and TV
state in the verification ledger. Reuse a prior result when the relevant
inputs, TV state and artifact match. A new branch or release number alone
does not select a physical case.

| What changed | Agent checks first | When to involve the owner and exactly what to ask |
| --- | --- | --- |
| Installer setup, retained receipts, file permissions, cleanup or edition handoff | Run the ordinary installer and check original operation identity, package versions, protected state, Stop and terminal readback. Use a verified software restart for reboot-dependent file and cleanup cases. | If SSH fails to return, check discovery and the saved connection. If the screen is off, ask the owner to turn it on with the remote. Apply the AC criteria below if recovery still needs a verified full restart. For an on-screen pairing prompt, ask the owner to approve it and report the outcome. |
| Home launch, foreground routing or a launcher surface | Start from a known app or input, send one network HOME and check the exact foreground or surface. | If the change affects the physical input hook, or the network path fails to exercise the affected route, ask the owner to open the named app/input, short-press Home once and report the screen that opens. |
| Native key filter, relay event delivery, key release or emergency Stop | Feed synthetic down/up events through the real filter/relay and check Stop, ungrab and key release. Check persistent Stop and stock Home on TV. | If the change affects physical key timing, device selection, hardware input release or the physical emergency path, ask the owner to open the named app/input, press Home three times within two seconds and then short-press Home once. Ask whether LG Home opened and stayed open, and whether arrows and volume still work when those controls are in scope. |
| Power handling, active Helper startup or behavior after loss of mains | Check startup status, actual processes, file modes and Home routing. Use a verified software restart for cleanup and permission checks when it preserves the case preconditions. Use standby for same-boot power behavior. | Request an AC cycle only for a selected case that requires loss of mains and lacks applicable evidence. Ask the owner to unplug for 10 seconds, reconnect, turn on the TV and report when the screen returns. Leave Helper controls untouched until the agent reads its automatic state. For a physical standby case, use the remote with mains connected. |
| Audio routing, input restoration or a physical display state | Use available readback for the expected app, input and settings. | Ask for the smallest observation the agent cannot measure. For audio, name the app/input and the expected result, such as audible video and one volume change. A volume indicator alone does not establish audible playback. |

Do not unplug the TV as part of the default release pass. Select an AC cycle
only when a changed startup hook, boot-state reader, permission repair used
during automatic startup, or power-loss recovery path could affect the result,
when reproducing a failure observed specifically after loss of mains, or when
recovery requires a verified full restart and no safe software restart is
available. A software restart that changes the precondition, for example by
latching Stop while an active Helper shuts down, establishes the need for AC
evidence only for that affected case. Reuse applicable evidence when available.

Before requesting the owner's help, record the affected behavior, expected
failure and why standby, a verified software restart, fixtures and existing
device evidence cannot answer the question. Compare the actual packaged files
and trace the changed branches. Carry forward an AC result on the same
model, firmware and relevant starting state when the startup path and its
dependencies are equivalent. Record the earlier build and the relevant
comparison. A version bump, different aggregate IPK hash, or a change confined
to a Stop or removal path does not by itself require unplugging the TV. Run
those affected branches with the final package using the ordinary operation,
verified restart or matching regression fixtures.

Software restart on the tested Root-accessible C3 uses ordinary
`/sbin/reboot` through the saved SSH identity. Use it only after checking
that the active operation is safe to restart. Confirm uptime reset and a
new installer boot session or disappearance of a unique temporary QA
marker. Preserve the existing operation receipt and verify that the ordinary
continuation accepts the restart. A kernel boot ID can be reused. Standby or
Quick Start can leave the same session running.

On OLED55C3RLA firmware 43.21.71, software restart and AC power loss both
expanded Helper file modes to 0777. Software restart with an active Helper
latched Stop before boot after input cleanup failed. AC power loss let the
same Helper start automatically and restore its private key mode. Reuse
software restart for equivalent cleanup and permission cases on this setup.
Pause standby/wake, software restart and AC tests if the TV shows an OLED
Pixel Cleaning notice in progress or repeatedly reports incomplete cleaning.
Let the cycle finish in standby with mains connected. LG identifies loss of
mains and early wake, including HDMI-CEC wake, as causes of interrupted
cleaning. [LG Pixel Cleaning guidance](https://www.lg.com/us/support/help-library/how-to-stop-repeated-pixel-cleaning-notifications-on-your-lg-oled-tv--20155440799135)

Keep AC recovery and physical key evidence distinct. A network HOME message
has no specified press duration. Three network messages opened LG Home
briefly on this C3 without triggering native emergency Stop. The relay
simulation covers valid timed down/up pairs and release behavior.
[Recorded C3 comparison](../history/2026-11-11-release-1.17.1-candidate.md#c3-software-restart-versus-ac-power-cycle)

## Explicit device preflight and installation

Use an existing saved Root `cytv` connection profile and a previously verified SSH
host key. These commands reuse the normal profile store (`--data-dir` can select
an existing alternative), existing identity/SSH agent authentication and the
receipt-authenticated installed Python binding. They reject an unknown host key,
missing/ambiguous profile or unresolved installer operation. They never discover,
bootstrap, provision or repair a TV. Existing `cytv` Python dependencies are
required; see [source build requirements](../BUILD.md).

First obtain owner authorization for this particular test with the owner present:

```sh
python3 scripts/tv-dev.py preflight \
  --bundle work/private-tv-qa --host SAVED_TV_HOST --owner-present
```

The read-only device admission rechecks the signed build and exact signing artifact,
then runs the existing [Root acceptance controller](SIGNED-ROOT-CANDIDATE-ACCEPTANCE.md)
with `preflight`. It does not upload executable code or write the TV's cache,
profile, journal, lease or Home state. An error is a stop. Use ordinary status and
supported recovery; do not delete state, substitute a supervisor/key or force retry.

For an explicitly authorized install, capture the **current running production UI**
with `RootProfile.capture({system:true})`, save its full returned JSON privately,
and restrict the file to owner access. This includes real configuration, order,
language/layout and embedded icons. Never create an empty profile or reuse a
historical capture merely to pass admission.

Fresh discovery can include an empty optional icon color. Capture omits colors
outside the canonical six-digit hex form from its copy of that inventory; it
does not rewrite the live catalog or relax validation of a stored/received
profile. A valid existing color is preserved.

```sh
chmod 600 work/current-root-profile.json
python3 scripts/tv-dev.py install \
  --bundle work/private-tv-qa --host SAVED_TV_HOST --owner-present \
  --profile work/current-root-profile.json
```

Install always runs read-only preflight before the separate install request. The
controller then repeats admission under the original device lease, passes the
actual captured profile to the original Manager and starts its unchanged worker.
Installed trust, rollback caches, recovery journals and profile restoration remain
in force. Equal-version, backward or component-identical candidates are refused;
there is no force/downgrade option. A maintenance release whose TV bytes did not
change should reuse applicable evidence, not reinstall equal components.

A returned admission phase means the worker was started, not that installation
completed. Observe ordinary System Updater status, real launcher/profile health,
original component hashes and supported rollback. Request owner confirmation for
physical controls and sound. Record actual model, firmware/webOS, remote if known,
versions, installer platform, tests, failures, workarounds and untested cases.
Keep raw profiles/logs private. Share results only within the authorization and
redaction rules in [AGENTS.md](../../AGENTS.md#installation-results-and-user-consent).

## Theme-only changes

For author CSS/assets, reuse the existing theme toolkit rather than rebuilding TV
packages. On a matching theme-enabled TV, open Settings → Appearance → Receive from
computer, then use the preview's **Send to TV** or the existing command:

```sh
node "$THEME_TOOLKIT/bin/theme.cjs" send themes/ocean \
  --runtime "$THEME_RUNTIME" --tv TV_PRIVATE_IPV4 --pin SIX_DIGIT_PIN
```

The receiver sends a fixed compiled snapshot; inspect and apply it on TV. A new
edit needs a new receiver session/PIN. Hosted UI simulation cannot exercise this
native receiver. Follow the [theme contribution guide](CONTRIBUTING-THEMES.md#7-try-the-theme-on-your-own-tv)
for toolkit setup, current transfer behavior and its acceptance limits.

## Local verification

```sh
python3 -m unittest discover -s tests/setup -p test_tv_dev.py
python3 scripts/tv-dev.py ui --stage-only --output build/tv-dev-check
node tests/tv-dev-ui.cjs
```

Tests model native-bridge traps, storage separation, staging failure, unsafe paths,
command construction, exact signed artifact identity, package tampering and the
existing admission controller transport. They never connect to a TV. Final release
checks and device evidence remain separate.


Fresh System Updater registration refreshes the LS2 service scan and restarts the
exact edition launcher process before reporting completion. A page reload alone
retains the old client's grants and can refuse `restoreProfile`. The normal
close/relaunch does not enable Root or clear emergency Off. If close or relaunch
is refused, keep bootstrap evidence and use the supported continuation; do not
edit permissions or readiness receipts.

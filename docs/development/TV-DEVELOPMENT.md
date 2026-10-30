# Fast TV development

These are source-checkout maintainer tools. Run from the source checkout with Node.js 20.19+, Python 3.9+ and the existing dependencies:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/tv-dev.py --help
```

Choose the feedback path that matches the change. UI staging tests rendering and
navigation with simulated TV APIs. Direct signed Root QA tests a real package set
through the installed updater after explicit owner authorization. Neither path
satisfies final release admission; follow [Release flow](../RELEASE-FLOW.md) for
full frozen-source checks, pinned builds, physical acceptance and publication.

## Compile UI without a TV

```sh
python3 scripts/tv-dev.py ui --stage-only
```

The output defaults to `build/tv-dev-ui`. A custom `--output DIRECTORY` must be
separate from sources. The command refuses symlinks and existing directories it
did not create. It compiles the current Root UI through the ordinary Chromium 38
Babel/PostCSS/ES5/CSS gates, using the public preview inventory and mock bridge.
It needs no network, webOS CLI or TV connection once npm dependencies are present.
Compilation failures preserve the previous successful output.

The staged metadata uses `com.cleanyourtv.dev.ui`, without Home category or
privileged ACG permissions. LocalStorage and IndexedDB access use the
`cytv.dev.ui.` namespace, including when a hosted CLI reuses its own origin.
The native bridge is disabled before loading the preview simulation, then the
mock is locked against replacement. A single bootstrap loads product scripts only
after isolation succeeds; a readonly native API stops startup safely. `webOS.service.request`, PalmSystem and
webOSSystem cannot reach native services. CSP permits same-origin bundled assets
needed by the theme engine, permits validated blob images and blocks connections
to external endpoints;
settings, launches, Root activation, audio and firmware actions are simulated.
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

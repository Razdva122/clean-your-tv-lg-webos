# Installer personalization

The desktop wizard places **Set up your Clean Your TV** after verified core
installation. The interactive console and Android bridge use
the same mode validation in `cytv/install_settings.py`. Non-interactive installs
and console `--yes` keep existing/default preferences. Unresolved recovery never
opens customization or repeats optional service writes.

| Choice | Root | No-root Developer Mode | No-root through root SSH |
| --- | --- | --- | --- |
| TV name (existing primary launch point; API/readback required) | Attempted | Attempted | Attempted |
| Classic, Liquid Glass, Ribbon | Yes | Yes | Yes |
| Home weather | Yes | Yes | Yes |
| Developer Mode auto-renewal Beta | No | Yes | No |
| LG firmware update blocking | Yes | No | No |

Ribbon disables weather. Liquid Glass retains its existing compact renderer.
Weather opt-in uses the existing automatic location mode when no city has been
saved; it creates no new endpoint. A saved city and other weather preferences
remain intact. An edition fallback determines the final mode before customization.

## Application and persistence

The installer sends a bounded `cytvSetup` object through the existing
`com.webos.applicationManager/launch` method to the installed edition's Home app.
The object contains a random request identity plus built-in theme, weather and
optional validated TV-name choices. TV naming writes the existing `tvhome.name`
preference and does not add an application-managed loading screen. This does not rewrite packages, inventory, private recovery data or LS2
permissions. It adds no network endpoint or elevated service API.

The shared `launcher/install-settings.js` handler reads initial launch parameters
and `webOSRelaunch` parameters after Home readiness. It validates the exact fields,
writes existing app-owned preferences with readback and reloads only Home's web
interface. Normal theme startup validates the chosen built-in theme. A saved city
and weather preferences are preserved; weather opt-in uses automatic location
when no city exists.

The localStorage marker `tvhome.installer.settings.v1` stores the last request
identity so stale launch parameters cannot override later TV-side changes or
create a reload loop. Invalid input causes no writes. Storage errors leave the
marker uncommitted and display the existing save-error toast. Root reinstallation
retains its existing full-removal semantics before this optional stage.

TV naming is also on this final page, rather than before package installation.
The CLI asks at the same stage; `--tv-name` applies after a successful installation,
including non-interactive runs. Omitting it in non-interactive mode preserves the
existing/default name. Cancelling optional customization does not undo installation.

`cytv/launchpoint_name.py` lists launch points and selects exactly one primary point
for the installed edition's app ID (an explicit default marker or the app's default
ID). It never creates a shortcut, rewrites package titles or changes permissions.
It sends only `launchPointId` and `title` to
`com.webos.applicationManager/updateLaunchPoint`, then reads `listLaunchPoints`
again and requires the same identity and exact title. Missing/ambiguous primary
points, permission denial, timeouts and readback mismatch are unconfirmed, without
automatic retry or reinstall. The TV-side name panel uses the same selection and
readback rules through `PalmServiceBridge`, retaining the Home preference if LG
refuses the system change. A later reset also attempts the primary-point rename.

Diagnostics keep only `saved`/`unconfirmed` under `launchpoint_title`; the separate
`tv_name` result is `requested-in-home`/`unconfirmed` and never contains the name.
The GUI reads the existing primary title to prefill the final field when possible.
An API success and matching readback do **not** establish LG Home presentation,
loading-screen behavior, Home-button routing or persistence through app/TV restarts.
Those checks remain pending on genuine Developer Mode hardware; OSE's public
API reference does not establish consumer-TV permission or behavior.

Optional service choices use their existing APIs after installation:

- Renewal uses its existing `enable`/`disable` API and checks enabled state and
  scheduling/storage errors. Saving an enabled preference does not prove that
  LG extended the session.
- Firmware blocking reads Homebrew configuration, changes only `blockUpdates`,
  then reads the configuration back. Missing, unsupported or non-root Homebrew
  cannot trigger a write. No TV restart is performed; the existing real-restart,
  security-update and effective-blocking limitations still apply.

The desktop presents three exclusive theme cards using bundled offline previews.
Weather and the mode feature use keyboard-accessible two-state switches. Before
showing the stage, the installer reads the current renewal/Homebrew preference
with a bounded read-only request. A known value initializes the mode switch;
failed reads leave it disabled and explicitly untested. An unchanged switch is
omitted from the write request. The console/Android **Keep current settings**
choice also omits service writes. Explicit On/Off requests remain distinct.
There is no automatic retry after an uncertain write. Each optional failure is
reported separately from core package installation. Redacted diagnostics retain
only fixed result categories under `tv.installation_settings`; appearance remains
`requested-in-home`, rather than claiming physical acceptance. Cancelling
customization preserves installation success and records the Home check as
untested. If interrupted before optional configuration, check the settings on
the TV afterward; recovery never replays those requests.

## Verification

`tests/cytv/test_install_settings.py`, `tests/installer-settings.cjs` and
`tests/installer-settings-ui.cjs` exercise mode boundaries, post-install ordering,
launch parameters, one-time storage, storage failure, partial Homebrew writes and
readback, renewal errors, Android skip/off choices and diagnostic projections.
Desktop widget coverage exercises mode-specific controls, Ribbon weather gating
and wrapped layout at the minimum supported window size. Existing profile startup
checks cover readiness/recovery behavior. These checks do not establish physical
weather, renewal, firmware blocking, standby or cold-boot acceptance.

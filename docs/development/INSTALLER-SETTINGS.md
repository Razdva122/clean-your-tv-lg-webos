# Installer personalization

The desktop wizard places **Set up your Clean Your TV** after verified core
installation. The interactive console and Android bridge use
the same mode validation in `cytv/install_settings.py`. Non-interactive installs
and console `--yes` keep existing/default preferences. Unresolved recovery never
opens customization or repeats optional service writes.

| Choice | Root | No-root Developer Mode | No-root through root SSH |
| --- | --- | --- | --- |
| Home screen name (existing primary launch point) | Available | — | — |
| Classic, Liquid Glass, Ribbon | Yes | Yes | Yes |
| Home weather | Yes | Yes | Yes |
| Developer Mode auto-renewal Beta | No | Yes | No |
| LG firmware update blocking | Yes | No | No |

Ribbon disables weather. Liquid Glass retains its existing compact renderer.
Weather opt-in uses the existing automatic location mode when no city has been
saved; it creates no new endpoint. A saved city and other weather preferences
remain intact. An edition fallback determines the final mode before customization.

## Debloat

The optional Debloat step comes before customization. The desktop wizard starts
with all ten choices selected and applies them when the user clicks Continue.
With root SSH, both editions read and write through the LG Settings Service.
No-root in Developer Mode writes through a separate SSAP pairing requesting
the regular `WRITE_SETTINGS` permission. It reads preferences through Developer
Mode SSH and can also read Live Plus through SSAP. The file reader returns
only the requested `on` or `off` value. A firmware may expose a setting
without making its value readable to the installer.

The installer skips values that already match. Before a selected write with a
readable original, it saves the original and requested value in the private
per-profile `debloat.json` record. It retains the first recorded original on
subsequent installations. The record captures pre-write values for future
restoration support. Its presence alone does not prove that a write changed
the setting.
Selected settings with unreadable originals can be sent without adding a
restore entry. Automatic restoration on uninstall is not implemented yet.

The SSAP setter may be unavailable or rejected on a given firmware. Debloat
reports the rejected write for each affected setting. It verifies accepted writes
with a separate read. Debloat is skipped for non-interactive installs and
console installs using `--yes`.

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

**Home screen name** is available during Root Edition installation. The field
is optional, and blank input keeps the current name. Enter `Home` explicitly to
reset it. The Root CLI accepts `--tv-name` for scripted installations.

The installer selects the existing Root primary launch point, requests a title
change and checks the same ID and exact title with `listLaunchPoints`. Missing
or ambiguous points, denied writes, timeouts and readback mismatches remain
unconfirmed. The installer sends the Home preference separately with the
cosmetic launch parameters. The preference is stored in Home’s local storage.
Root updater profile formats remain compatible with installed supervisors. An
update or full reinstall that clears app storage may reset the name. Blank input
skips renaming after installation.

Diagnostics report `saved` or `unconfirmed` for `launchpoint_title`, and
`requested-in-home` or `unconfirmed` for `tv_name`. Root hardware acceptance
still needs to check LG Home, the system loading screen, Home-button launch
and persistence after app and TV restart.

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

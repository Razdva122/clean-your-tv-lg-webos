# Manage apps on Home

Hold OK on an app for 0.6 seconds to pick it up. Use the arrows to move it,
press OK to place it, or Back to cancel. With a pointer, hold the tile,
release, point at its new position and click to place it.

The **+ / Add app** tile stays last when shown. It lists installed apps which
are not on Home, including apps previously hidden here. Selecting one adds
it at the end, before + when shown. This does not install software.

To hide an app, pick it up and move down beyond the last row of apps to
**Hide from Home**, then press OK. The pointer can select this button directly.
The app remains installed on the TV. **Undo** receives focus immediately;
press OK to restore the original layout, or Back/an arrow to dismiss Undo.
You can also restore the app later through +. Hiding every app leaves + available when shown. If + is hidden, the top controls
and Settings remain accessible.

<a id="hide-the--tile-unreleased-candidate"></a>

## Hide the + tile (Home 1.6.0)

In both editions, open **Home settings → Appearance** and turn off
**Show Add app tile**. The default is on. This only hides +; it keeps your
app selection, ordering and editing controls. Use **Add app** in the same
settings section to add apps or restore hidden ones without showing + again.
The choice survives restart and is included in the layout saved for system
update/rollback recovery. A failed save leaves the previous choice active.

## Live TV discovery (unreleased, #290)

**+ / Add app** can offer the broadcast tuner under the TV's own localized name
(for example, Live TV) when Application Manager reports it installed. Some
firmware omits the tuner from launch points and marks its app invisible; the
candidate includes this discovered tuner without exposing other hidden system
apps. It does not invent an app on models where the tuner is not discovered.

No-root needs the updated Home Helper for picker refresh and the updated installer
for initial inventory. Root needs the updated Home package. An unsupported or
failed supplementary query preserves the normal app list. These changes are not
yet in published downloads. Discovery is verified separately from launching
channels; tuner launch and firmware-specific compatibility still need TV acceptance.

## Inventory and persistence

The launcher asks its edition's service for a fresh inventory whenever the app picker opens.
No-root uses the helper's existing SSAP pairing key and the TV's local network
addresses. Root uses a fixed, read-only Application Manager query. Both requests
are bounded. A missing pairing key, denied request or timeout falls back to the
saved inventory with an explicit message. No pairing dialog is intentionally
started, and no uninstall endpoint is called.

The new UI requires the corresponding updated service package for fresh discovery.
With an older service it can still manage the saved inventory. A live television
check is required before claiming compatibility with a specific firmware.

`tvhome.layout` stores order, hidden IDs, the optional boolean `showAddApp` (default true)
and the known app catalog in localStorage.
Existing `tvhome.order` and configured hidden apps migrate on first use. Discovery
never automatically adds tiles. The no-root profile backup includes the new key,
so the updater can restore it along with the existing settings. Root retains the
layout in its application storage across in-place updates.

## Local verification

Run `bash scripts/test.sh` in a Python environment containing the project dependencies.
The model, service transport and profile tests are in `tests/apps/`.
Run the browser scenarios separately:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright node tests/apps/ui.cjs
node tests/themes/add-tile-ui.cjs
```

The browser test uses simulated TV replies and an isolated Chrome profile; it
checks remote/pointer hold, movement/cancellation, hide/undo, multirow navigation,
empty screen, addition, offline fallback and restart persistence.

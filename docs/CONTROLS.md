# Remote controls and emergency exit

[Documentation](README.md) · [Recovery](RECOVERY.md)

## Use Home

| Control | Result |
| --- | --- |
| Arrows, OK or pointer | Navigate and open apps. |
| Hold OK on a tile | Move or hide it; Back cancels. [Details](APP-MANAGEMENT.md). |
| Short Home | Open your launcher while Home control is enabled. |
| Short Back | Normal app navigation and exit confirmation. |
| Volume, mute, power | Normal TV controls. Standby and a true cold boot are different test paths. |

The Magic Remote pointer and wheel pass through. Wheel-to-tile navigation is not
implemented. The launcher does not take over app-specific Back behavior.

### Inputs shelf (Classic)

Classic shows your TV inputs and Live TV as a row of tiles between the clock and
the dock. Press **Up** from the dock to reach it, **Left/Right** to choose a
source and **OK** to switch to it. **Up** again reaches the Inputs, Wi-Fi and
Settings buttons; **Down** or **Back** returns to the dock. When the TV reports
input status, connected sources show a green dot and the connected device's name,
and empty ports are dimmed with "Not connected" but stay selectable. If the TV
does not report status, the shelf lists the inputs captured during installation
without status. Turn it off with **Settings → Appearance → Show inputs on Home**;
Up from the dock then reaches the header buttons as before. Other layouts keep
the header **Inputs** button only. Live status depends on the TV allowing Home
to read it; it has been confirmed on one webOS 6 TV with the No-root Edition.

Rest on a connected HDMI source for about a second and its tile shows the live
picture, muted. Only the focused tile previews. Moving away, opening the header,
the Inputs dropdown or Settings, launching an input or leaving Home stops it. Empty
ports, other input types and Live TV show the usual tile. If a picture does not start
within four seconds, that source shows the usual tile for a minute. Turn previews off with
**Settings → Appearance → Preview inputs on focus**. After switching to an input,
pressing **Home** returns focus to that input's tile, so switching back is one press.

## Return to LG Home

**Press Home three times within two seconds.** Home interception stops and LG
Home opens. Saved preferences remain. On legacy No-root Helper versions through
0.6.13, use a two-second Home hold instead.

Do this once after installation so you know the recovery path works on your TV.
If controls are still unavailable, stop setup and use [recovery](RECOVERY.md).

## Resume deliberately

- **No-root:** open Home Helper from LG's app list and confirm starting Home control.
- **Root:** use the documented Root activation control after checking the retained status.

Opening the launcher alone does not clear an emergency stop. Regular control is
also available through the **Change Home** setting. Do not reset recovery data or
remove stop files to force activation.

## Back, app exits and startup

**Hold Back for about 1.2 seconds** to visit LG Home once. This preserves the
saved Home choice and does not stop Home control; a later short Home returns to
Clean. Use triple Home when you want to stop interception. Short Back remains
the current app's normal navigation/exit action.

The No-root Helper can return to the launcher after watched apps exit, and LG Home
may briefly appear. Firmware-specific long-Back behavior still needs device
confirmation. Root uses its own system routing; one edition's test does not prove
the other.

Startup can initially show a black screen or LG Home. Standby/wake success does
not prove cold-boot reliability or a fixed startup time. See [device limits](COMPATIBILITY.md).

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

### Inputs (unpublished 1.7.0 candidate)

The selected theme chooses the header **Inputs** menu or an input shelf. Liquid
Glass uses the shelf; Classic and themes without a shelf keep the header menu.
There is no global **Show inputs on Home** or placement switch. On a shelf, press
**Up** from the dock, **Left/Right** to choose and **OK** to launch. **Up** again
reaches the header; **Down** or **Back** returns to the dock. The shelf replaces
the header Inputs menu when tiles are present. Empty ports remain selectable.
A supplied device name is shown when firmware provides it; otherwise a connected
source says **Connected**. Home does not invent a console name or guarantee CEC
identification. These candidate controls differ from published 1.6.0.

Live previews are **off by default**. **Settings → Appearance → Preview inputs on
focus** is available for a shelf theme. When explicitly enabled, a connected HDMI
source can preview after about 0.8 seconds of focus. Moving away, opening another
surface or leaving Home stops it. Live TV and empty ports keep static tiles.
Firmware can still play audio or switch HDR despite element mute; silence is not
guaranteed. Home does not change global TV mute/HDR settings automatically.

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

In the unpublished Root candidate, **Home settings → Open Clean Your TV first**
chooses native startup sources: LG Channels / Live TV defaults on, YouTube and
HDMI default off. With **Change Home** off these choices remain visible, muted
and disabled with an explanation; saved values remain. Late boot/wake launches
are removed. Exact-package first-screen and control acceptance is pending.

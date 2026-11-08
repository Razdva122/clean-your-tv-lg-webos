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

<a id="standard-ir-remote-unpublished-no-root-candidate"></a>

### Standard IR remote (No-root Helper 0.8.0)

Helper observes `LGE RCU` read-only without grabbing or re-emitting its
keys. Releasing a short Home press schedules Clean after about 700 ms; stock LG
Home may flash first. Held Home stays with webOS. Triple Home still stops Helper;
Home-control Off, Stop, relay exit and watchdog recovery cancel pending IR work.
An input overflow discards the incomplete IR gesture until synchronization
returns; only fresh complete presses can activate Home or count towards escape.

This is source behavior, not verified access or acceptance on stock Developer
Mode TVs or the original LJ550T. Do not change input permissions to enable it.
This feature is included in published v1.13.0 / Helper 0.8.0; v1.12.1 did not include it.
[Source checks, attribution and remaining gates](history/2026-11-08-issue207-ir-safety.md).

<a id="inputs-unpublished-170-candidate"></a>

### Inputs (1.7.0)

The selected theme chooses the header **Inputs** menu or an input shelf. Liquid
Glass uses the shelf; Classic and themes without a shelf keep the header menu.
There is no global **Show inputs on Home** or placement switch. On a shelf, press
**Up** from the dock, **Left/Right** to choose and **OK** to launch. **Up** again
reaches the header; **Down** or **Back** returns to the dock. The shelf replaces
the header Inputs menu when tiles are present. Empty ports remain selectable.
A supplied device name is shown when firmware provides it; otherwise a connected
source says **Connected**. Home does not invent a console name or guarantee CEC
identification. Root uses its authenticated read-only service snapshot. No-root
keeps direct EIM where allowed and uses the already paired Helper after a
definitive permission refusal. Failed reads leave status unknown; no new setting
or pairing prompt is added. These 1.7.0 controls differ from version 1.6.0.

Live previews are **on by default**; an explicitly saved Off stays off. Disable
**Settings → Appearance → Preview inputs on focus** to turn them off. While
enabled for a shelf theme, a connected HDMI source can preview after about
0.8 seconds of focus. Moving away, opening another
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

**Single Home in 1.8.2:** Ribbon is an ordinary theme of the same
full-screen Home in both editions, with its own background. Home opens or
reactivates that window. Back closes menus/editing first; on the input shelf it
returns focus to the app cards. It does not dismiss a transparent bar or reveal
video/HDMI underneath. Selecting an app uses normal TV app switching, without
Home forcing its own window to close. See the [1.8.2 tested scope and known limits](RELEASE-1.8.2.md); new candidate artifacts need their own affected acceptance.


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

In Root 1.7.0, **Home settings → Open Clean Your TV first**
chooses two native startup sources: LG Channels / Live TV defaults on and
YouTube defaults off. There is no HDMI startup switch; a source switched off
leaves startup to firmware. See the [global startup-setting dependency](../root-edition/README.md#candidate-native-startup-choices). With **Change Home** off these choices remain visible, muted
and disabled with an explanation; saved values remain. Late boot/wake launches
are removed. See [1.7.0 acceptance and limits](RELEASE-1.7.0.md) for the
recorded first-screen and control scope; no universal compatibility is implied.

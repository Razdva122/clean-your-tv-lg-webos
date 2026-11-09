# Update, disable, rollback and uninstall

For cytv installations of either edition, use its saved connection and maintenance
actions: [desktop maintenance](DESKTOP_INSTALL.md), [CLI reference](CLI.md).
For manual Root setup, follow [Root removal and replacement](../root-edition/ROLLOUT.md#remove-or-replace-root-edition)
and [Root updates](../root-edition/UPDATES.md). Root recovery/updater state is
retained intentionally; never delete it to force reinstallation.

The webOS CLI procedure below applies to **No-root source installations**.
Stop Helper with triple Home in current builds, or hold Home for about two
seconds in Helper versions through 0.6.13.

For a **one-script installation**, run CLI commands from the repository folder.
The CLI is local; expose it in your current terminal:

```sh
export PATH="$PWD/build/tools/node_modules/.bin:$PATH"
```

The automatic device name is `clean-your-tv-<IP-with-dashes>` (for example
`clean-your-tv-192-168-1-50`), or the `DEVICE` override you supplied. Replace
`-d lgtv` in the commands below with `-d clean-your-tv-192-168-1-50`, using your
actual device name. Manual installations below use the profile `lgtv`.

## Update

For normal installations, start with [updates](UPDATES.md). The source procedure
below is for installations without the independent System Updater.

Read the release notes. Pause interception with triple Home before updating. Keep
known-working packages locally. Do not uninstall first: that can remove app data.

Build the new version, then install helper followed by launcher. Refresh app inventory
and rerun `scripts/configure-tv.sh` to restore pairing/watch configuration if the
installer has replaced state. Manually open Home Helper only when ready.
State preservation across every firmware/installer version is not guaranteed.

## Remove input restoration

Run on your computer with the configured `lgtv` device:

```sh
ares-novacom -d lgtv --run "luna-send-pub -n 1 luna://com.webos.service.eim/deleteDevice '{\"appId\":\"com.gathin.tvhome\"}'"
```

Check for `returnValue: true`. This removes the input registration; it does not
uninstall the applications. First press Home three times within two seconds to stop interception.

## Uninstall

The next installer update adds removal support for older LG stock screens: if
there is no separate LG Home app, No-root removal may switch to Live TV. This is
not yet in the published installer. Keep the TV on and follow the normal restart
and **Try again** prompts; retain the saved connection and recovery records.

In published v1.11.0 and later, select **Uninstall Clean Your TV** on desktop
or Android (`cytv uninstall`) with the saved connection and confirm once. It
removes known present apps/files and skips missing ones, even after partial setup.
When asked, disconnect/reconnect TV power, wait for the network and choose
**Try again** for the final sweep. Standby/Quick Start is not a full restart; CYTV
never reboots the TV automatically. Connection loss also offers Try again on the
same approved goal. Actual permission denial asks for Root access; an actual busy
operation asks you to wait. Success appears only after final cleanup is verified.
Keep keys and reports; do not reinstall or clear app data just to retry removal.
Returning to LG Home remains a separate action.
See [removal](RECOVERY.md#next-candidate-original-operation-recovery-and-full-removal).

<a id="unreleased-removal-and-reinstallation-continuation"></a>

### Removal and reinstallation continuation (v1.13.0)

After a removal connection error, open the connection details on desktop or
return to the connection screen on Android. The pending TV address, edition,
SSH port and host-key verification remain fixed. Check network access or select
an existing Root SSH private key, then retry the same removal. Choosing a key
does not replace the saved host pin or recovery records.

No-root setup checks Helper before pairing. If it is running, stop it with the
documented Home gesture and confirm the recheck in the current setup. An unknown
process state still blocks replacement; emergency-stop markers are preserved.

A completely empty No-root installation can finish without a restart only after
current files, package registrations, input shortcuts and process absence have
been checked, with no unresolved prior installation. Actual removal still uses
the requested full restart. If the input-list API fails, CYTV tries deleting only
its own input shortcut and continues safe package cleanup. A remaining unverified
shortcut keeps removal pending; retry after the service is available. No success
is shown merely because the packages disappeared.

### Root reinstallation through the installer (unreleased, #355)

Choose **Set up my TV** with the saved Root connection and confirm **Reinstall
Root**. This also works after a failed profile-based Home activation. The installer
validates its replacement bundle and reads a fresh inventory before removing
anything. It restores LG Home, removes the previous Clean Your TV installation
including updaters and any No-root Home/Helper, and checks complete removal before
installing and activating its own packages and runtime in the same setup.
Back up preferences first; other TV apps and existing root access are preserved.

Incomplete cleanup or a required restart stops replacement. Continue the saved
removal in the installer, then choose setup again. Standalone removal never
starts installation. Earlier recovery records remain on the computer. A retained
runtime cannot be silently activated as the newly selected runtime: both the
worker and pre-activation checks compare actual code against the installer bundle.
Fresh, recognized activation refusals have specific explanations; historical logs
are not attributed to a new attempt. Native C1 remains fresh-install-only.

The following manual steps are for the source installations described above.

1. Press Home three times within two seconds to stop interception.
2. Remove input restoration using the command above.
3. Remove the startup task if the service is still installed:

```sh
ares-novacom -d lgtv --run "luna-send-pub -n 1 luna://com.local.nativehome.service/disable '{}'"
ares-install -d lgtv --remove com.local.nativehome
ares-install -d lgtv --remove com.gathin.tvhome
```

Remove any Quick Access assignment manually. Uninstalling the launcher can delete
its saved tile ordering. Keep your local configuration if you want to reinstall.
Revoke the SSAP pairing through TV device/connection settings if desired; erase
`.lgtv-key.json` and `build/setup/ssap-key.json` on the computer when no longer needed.

## Rollback

If the independent System Updater is installed, use its edition Updater's
Recovery flow for the verified previous component set. Do not manually replace
packages around its captured baseline. The manual procedure below applies to
source installations without that supervisor.

Pause first, then reinstall your saved previous packages. Reconfigure pairing/input
registration if necessary. Previous helper versions have different recovery behavior;
read their instructions before manually starting the helper. This repository does
not silently downgrade or reset your TV.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="whole-edition-updates-in-110"></a>

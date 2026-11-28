# Clean Your TV tile — unreleased

The Clean Your TV tile is an unpublished Homebrew Channel candidate for compatible,
already-rooted TVs. It can install Root or offer No-root when its compatibility checks
select that edition.
The current public installation paths are the desktop and Android installers.
The candidate and its catalog draft still require exact-package TV acceptance,
public asset verification, screenshots, human review and catalog approval.
[Desktop setup](../docs/INSTALL.md) · [Android setup](../android/README.md) ·
[Localized guides](../docs/LANGUAGES.md)

The installer requires a rooted compatible LG webOS TV, Homebrew Channel's exec
service with actual root execution, Node.js 8+, and a usable Python 3.9+ or the
bundled pinned ARMv7 Python 3.13 runtime. Runtime preparation requires 320 MiB free
after Installer is installed. Allow additional space for the selected IPK and
package-manager staging. See the acceptance record for measured package bytes.

For a fresh Root setup, choose **Install and activate** and confirm once.
This includes preparing the bundled Python runtime when needed. The Installer checks the payload and
the TV again before submitting the packages. It requests activation after
verifying installation. Restore LG Home cancels outstanding setup approval. After an
interruption, choose **Check status** to read the original request. This
one-confirmation workflow awaits physical acceptance on the selected IPK.
[Candidate setup](../docs/INSTALL.md#candidate-on-tv-root-installation) ·
[Acceptance record](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md)

After installation, Root Home opens **Set up your TV**. Choose a built-in theme
under **Themes**. To change LG ads or recommendations, open **Adjust LG settings**,
select the options you want, and choose **Apply selected settings**. Check the
result beside each option. Choose **Restore selected settings** to return selected
options to their saved original values. Choose **Open Home** to continue. To return
later, use **Settings → Advanced → Set up your TV**.

After verified setup, opening the tile opens your Home. A stopped Home
controller stays stopped. If Home fails to open, choose **Recovery** to inspect
an available product rollback or use the computer installer. **Restore LG Home**
restores LG button routing. It does not change the installed product version.

For an existing older edition, continue on the computer when prompted. Returning
from the single-tile generation to the older edition requires complete removal
and a fresh installation of that edition. The tile cannot restore that earlier
generation. Desktop and Android distributions can install an edition-specific
tile without the Homebrew payload. Its normal launch uses the TV's application
manager and works without an Internet connection or a Homebrew status check.

The single-tile desktop and Android candidates let you keep an older installation
or choose a clean switch. A clean switch removes saved layout, themes, personal
wallpapers and preferences. No-root also needs fresh pairing. Removal and new
setup each have their own confirmation. For Root, install the full Homebrew
tile first so the host can open it when setup is ready.

On a Developer Mode TV already using the single tile, the desktop or Android
installer can repair a missing tile and update a compatible screensaver.
It keeps the installed Home and Helper, including the current preferences,
pairing and stopped state. Replacing Home requires a verified backup of its
browser data. LG documents that updating a packaged app clears its local
storage. [Web Storage on webOS TV](https://github.com/webOS-TV-app-samples/WebStorage#local-storage)

On a TV with on-device updates, open Home settings and choose
**Update Clean Your TV**. A later update in this generation can be rolled
back from **Recovery**.

On a fresh supported TV, the installer selects Root by default. If the
Root checks confirm that standard Root cannot control Home and the bundled
No-root components pass their own checks, the installer selects No-root.
Confirm installation once, then choose **Allow** when webOS asks to pair the
TV remote control. Reopen the installer to check or continue the same request.
Verified No-root setup keeps the same Clean Your TV tile.

If a supported Root backend requires the desktop installer, continue on a
computer. If Homebrew cannot run the TV installer or cannot verify the
No-root prerequisites, use the desktop or Android installer. An inconclusive
Home check offers **Check status**. This package requires an already-rooted
TV even when it installs the No-root edition.

On webOS 11, stock Homebrew Channel **0.7.3** can reject Installer's `exec`
request with `Denied method call` even when the same entry works from root SSH.
Homebrew's [upstream correction #233](https://github.com/webosbrew/webos-homebrew-channel/pull/233)
grants its elevated service to the `lunabus.query` group used by newer apps.
That correction is not in the published 0.7.3 release. Checking root execution
from SSH alone does not validate the application's access. An appinfo-only
`requiredPermissions` declaration did not grant the group on the tested TV.
Do not silently patch Homebrew's ACLs or count a temporary prerequisite patch
as an unmodified public installation. See the
[current submission record](catalog/SUBMISSION.md).

For candidate testing on webOS 11 or later, use
[Homebrew Channel 0.8.0](https://github.com/webosbrew/webos-homebrew-channel/releases/tag/v0.8.0)
or later. Version 0.8.0 is the first published release that includes #233.
Verify access by opening the Installer app on the TV and checking its status.
If access remains denied, use the published computer or Android installer.

The list of checks shows what passed, the current installation stage and any
failure the Installer could confirm. Choose **Check status** to inspect the
existing operation. The error screen describes the cause and the next step.

Choose **Save diagnostic report** and scan the QR with your phone. The
project's support page offers a JSON file in the same diagnostic format as
the computer installer. **Open draft on GitHub** includes that report in the
issue text. Add a short description and optionally attach the saved JSON
before submitting. **Open saved report** shows the last report on the TV.

A self-registration step inside the Installer bootstrap cannot solve a denial
that prevents that bootstrap from starting. The Root Home firmware helper's
package-owned permission registration concerns only configuration methods and
requires an existing trusted root execution path; it is not an Installer `exec`
permission solution. No Homebrew/shared ACL, appinfo permission experiment,
root-check relaxation or automatic service restart is added here.

The candidate package ID is `io.github.razdva122.cytvinstaller`. Earlier TV
observations cover the draft ID `com.cleanyourtv.installer`. Homebrew treats
the new ID as a separate application, with its own installation and removal.
Homebrew updates the tile and its setup client. Product updates use the signed
release for the installed edition.

To remove the product from the TV, open **Settings → Advanced → Clean Your TV
recovery** in Root Home, choose **Remove complete product**, and confirm. If a
full restart is requested, restart the TV, reopen Clean Your TV and choose
**Continue after restarting**. After the installer verifies removal and restores
LG Home, **Remove Installer** also removes the tile. Removing only the tile
through Homebrew leaves installed product components. External component removal,
emergency release, standby and separate cold boot still require physical acceptance.

## Development and publication gates

Build and CI artifacts are development candidates. They do not authorize a public
release or catalog submission. `homebrew/release.json` is absent; promotion remains
disabled until exact-artifact TV acceptance and meaningful human review are recorded.

Required evidence includes clean setup, storage/staging measurement, both client
handoffs, upgrade/rollback, System Updater setup, setup with and without
compatible Home settings, component/direct Installer removal, triple-Home,
standby and separate cold boot. Public URLs and TV screenshots also need
verification. See [acceptance](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md).

For build APIs, metadata generation, protected release carry-forward and catalog
submission requirements, use the [development and promotion contract](DEVELOPMENT.md).

<a id="reproducible-candidate-preparation"></a>
See [candidate preparation](DEVELOPMENT.md#reproducible-candidate-preparation).
<a id="acceptance-and-existing-release-gate"></a>
See [release gate](DEVELOPMENT.md#acceptance-and-existing-release-gate).
<a id="catalog-review"></a>
See [catalog review](DEVELOPMENT.md#catalog-review).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="cytv-installer-candidate-and-homebrew-metadata"></a>

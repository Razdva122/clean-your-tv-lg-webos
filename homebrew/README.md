# Homebrew Installer — unreleased

CYTV Installer is an unpublished Homebrew Channel candidate for Root setup.
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

On a fresh, compatible TV the candidate offers **Install and activate**. Review
the selected components and optional System Updater before confirming. If
needed, this confirmation also covers preparation of the bundled Python
runtime. The installer checks the reviewed payload and the TV again before
submitting the packages. Activation is a separate operation after verified
installation. Restore LG Home cancels outstanding setup approval. After an
interruption, choose **Check status** to read the original request. This
one-confirmation workflow awaits physical acceptance on the selected IPK.
[Candidate setup](../docs/INSTALL.md#candidate-on-tv-root-installation) ·
[Acceptance record](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md)

If the TV needs a Root Home backend available through the desktop installer,
continue on a computer. If the candidate confirms that Root cannot control
Home, it directs you to computer or Android setup to check No-root and pair
Home Helper with the TV. The TV package has no No-root installer or supported
way to establish the Helper's first pairing on the same TV. An inconclusive
Home check offers **Check status**. With Node older than 8, use the computer
or Android installer to check available editions.

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

The candidate uses its existing read-only, app-originated `inspect` as the access
preflight. An exact LS2 `exec` denial shows **Homebrew access denied** with
the update and fallback instructions in all supported languages. Only Check
status and Close are offered. A saved request ID is retained, and retry inspects
before querying its status.
The message also applies if access is lost after opening. Missing services,
malformed replies and backend/root failures retain their generic handling; raw
service diagnostics are never displayed. This does not grant access or establish
physical-TV acceptance.

A self-registration step inside the Installer bootstrap cannot solve a denial
that prevents that bootstrap from starting. The Root Home firmware helper's
package-owned permission registration concerns only configuration methods and
requires an existing trusted root execution path; it is not an Installer `exec`
permission solution. No Homebrew/shared ACL, appinfo permission experiment,
root-check relaxation or automatic service restart is added here.

The candidate package ID is `io.github.razdva122.cytvinstaller`. Earlier TV
observations cover the draft ID `com.cleanyourtv.installer`. Homebrew treats
the new ID as a separate application, with its own installation and removal.
Homebrew updates the Installer application. Root Home,
Root Updater and optional System Updater retain their product and recovery
contracts; complete product updates belong to System Updater. Removing the
installer leaves those components installed. Complete-product removal is an
explicit installer/cytv operation. External component removal, emergency release,
standby and separate cold boot still require physical acceptance.

## Development and publication gates

Build and CI artifacts are development candidates. They do not authorize a public
release or catalog submission. `homebrew/release.json` is absent; promotion remains
disabled until exact-artifact TV acceptance and meaningful human review are recorded.

Required evidence includes clean setup, storage/staging measurement, both client
handoffs, upgrade/rollback, optional supervisor behavior, component/direct Installer
removal, triple-Home, standby and separate cold boot. Public URLs and TV screenshots
also need verification. See [acceptance](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md).

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

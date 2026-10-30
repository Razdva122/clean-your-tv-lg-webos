# Homebrew Installer — unreleased

For a supported published installation path, use the [desktop installer](../docs/INSTALL.md)
or [Android](../android/README.md). Homebrew Installer is **not included in the
published 1.4.0 distribution**; no catalog listing is approved.

This is an unpublished Root-edition installation path. Physical TV acceptance
(Task 8), public asset verification, meaningful human review, screenshots and
catalog-maintainer approval remain separate gates. The catalog file is a review
**draft**, not a submitted or approved listing. See the [candidate setup guide](../docs/INSTALL.md#candidate-on-tv-root-installation),
all twelve [localized guides](../docs/LANGUAGES.md), and the [physical acceptance/state inventory](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md).

The installer requires a rooted compatible LG webOS TV, Homebrew Channel's exec
service with actual root execution, Node.js 8+, and a usable Python 3.9+ or the
bundled pinned ARMv7 Python 3.13 runtime. Runtime preparation requires 320 MiB free;
the approximately 57 MiB development IPK also requires unmeasured package-manager
staging capacity. No new model, firmware or webOS compatibility is claimed.

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

Homebrew updates the separate `com.cleanyourtv.installer` application. Root Home,
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

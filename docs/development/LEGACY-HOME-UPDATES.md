# Legacy Home-only updater reference

Historical procedures and evidence for installations through v1.0.3. These are
not current setup or publication instructions. Start with [current updates](../UPDATES.md)
and [release process](../RELEASE-PROCESS.md).


The remainder records the older Home-only path and its historical evidence.
It applies only while no System Updater is installed. Its promise that Helper
is unchanged does not describe the 1.1.0 whole-edition path above. Retain this
reference for existing installations; do not apply legacy permissions or sign
legacy example manifests as a shortcut to the new bootstrap.

Available in v0.8.1. Published signed Home update and rollback were verified on LG OLED55C3RLA / 43.21.71, including app preservation, remote controls and disabled renewal. Installation from the TV requires root, Homebrew Channel and the scoped setup below.

## Legacy: What users get

Home Settings → Software updates → Check for updates shows installed and available Home versions. The separate **Home Updater** app owns the backup and recovery journal. Installation requires root, Homebrew Channel and the scoped LS2 permission setup below. The no-root launcher remains supported with computer-assisted updates; checking releases through this updater also depends on access to Homebrew's metadata API and is not promised on an unrooted TV.

Developer Mode auto-renewal is paused automatically before installation and its prior preference is restored after verified success or rollback. Users do not have to disable it manually. Helper code, emergency-stop markers, autostart configuration and system Home profiles are not changed.

The first upgrade to Home 1.2.0 requires a personalized package using the existing sync/build flow. Subsequent in-app updates require an installed Home version at least 1.2.0 and a signed matching previous package. Never install an empty generic package over a pre-1.2.0 installation expecting migration.

## Legacy: Preserved data

Home captures the app inventory, embedded icons, input labels, configuration, tile order and renewal diagnostic history. It saves a local copy and then an independent updater backup before installation. The transaction's renewal receipt, not diagnostic history, controls restoration of the enabled preference. Missing icons, invalid profiles and storage failures stop installation.

The new Home loads its saved profile before rendering, or restores the independent backup when local data is absent. A damaged local profile is not silently replaced. Current bounds are 200 apps, 100 inputs, 256 KiB per icon and 4 MiB profile JSON; maximum-sized profiles have not been validated on hardware. A personalized rebuild is not an inventory reset once a saved profile exists.

## Legacy: Recovery

Root and No-root confirm startup health automatically after installation; users do
not need to confirm that the updated launcher works. Confirmation does not remove
the previous-version rollback. Recovery has no time limit and refers to the last
update until a subsequent update replaces the saved transaction and profile.
Rollback restores the previous Home version and the pre-update settings snapshot;
the confirmation dialog warns that settings changed afterward will be lost.
An unrelated installed version blocks a confirmed transaction's rollback, and an
uncertain or failed rollback cannot be submitted repeatedly.

Root uses the independently saved package cache and profile, restores LG Home
before rollback, and checks the restored launcher's profile readiness before
finishing. After verified startup, it automatically restores Home control if it
was persistently enabled immediately before the update suspended it. A disabled
choice stays disabled. Explicit or emergency off during installation cancels
resumption; changed boot, failsafe, changed intent or failed input/guardian
readiness leaves LG Home selected. There is no user health-confirmation step or
two-minute confirmation prompt. The internal startup health deadline still
protects the installation.

No-root retains its signed previous package reference and saved
profile; its on-device updater still requires root and Homebrew Channel. On an
unrooted TV, use the computer installer. This change does not add package-install
privileges to an unrooted TV. Its separate Helper is not replaced or restarted, so
its existing Home-control preference, controller and emergency-stop state stay
in place. An explicit or emergency stop is never undone by update completion.

Both editions use the same readable update layout: versions and status above the
release notes, a stationary action row below, Up/Down to read notes, Left/Right to
choose an action, and Back to return. Notes use an inert Markdown subset for
headings, lists and emphasis; release HTML, scripts and links are never executed.
Background polling preserves reading position and remote focus.

No-root stores new snapshots inside the same atomic journal as their transaction;
legacy journals still read the separate profile backup. Transaction-aware
launchers restore retained browser settings once, using the rollback transaction
and installed version as the restoration marker. A prior package released before
this bootstrap fix may keep its retained local settings; it can only restore the
backup automatically when local package data is absent. The stronger settings
restoration guarantee therefore requires a previous package containing this fix.
Root's independently provisioned updater must also be upgraded from the computer;
installing a new Root launcher IPK alone does not replace the pinned updater code.
Setup and the updater check `HOME_RESUME_PROTOCOL = 1` in the verified runtime
before reserving routing. The runtime owns private `update-home-resume.json` and
`update-home-cancel.json` records tied to the update reservation and suspension
cycle. An activation-attempt receipt is synced before enabling Home, preventing
replayed activation after a process interruption. Unresolved cleanup can be
reconciled without reinstalling or repeating an activation attempt. An uncertain
activation is restored off, not silently retried. Home restoration errors are
reported separately from successful package installation.

Open Home Updater to inspect the transaction or restore the signed previous Home package. Recovery checks root, helper compatibility, manifest signature and package hash. The previous package must remain downloadable; this is not an offline recovery image or a full TV backup.

Homebrew does not distinguish transport failures from terminal installer failures in its error envelope. A failed installation call therefore stays in recovery; it does not automatically start another install. Timeouts and interrupted installation remain blocked in `recovery-required`; reading a version is not proof that an installer has stopped. There is no clear-lock-and-retry button. A confirmed install waits for the populated Home grid on launch before restoring renewal. This is a startup signal, not a complete UI health test.

The service fetches and verifies metadata again at confirmation so idle shutdown between Check and Confirm does not lose the offer. A changed offered version requires a new confirmation. Installation uses a subscription and waits for Homebrew's terminal `finished` reply; progress messages are not success.

## Legacy: Scoped permission setup (maintainer procedure)

The package alone does not grant cross-package permissions. Build `scripts/build-updater.sh`; its `dist/updater-setup/` directory contains the CLI and its dependencies. Transfer that directory intact to a temporary directory on an already-rooted TV. From that directory, as root:

```sh
node scripts/update-permissions.cjs plan production
node scripts/update-permissions.cjs apply production
```

Review the plan before applying it. It creates only dedicated API/client permission files and a permission-only manifest under `/var/luna-service2-dev`, plus an ownership receipt. It does not edit Homebrew's manifest or grant `all`, `public`, shell access or system Home/profile permissions. Only named methods are exposed. Bus identity checks remain enforced by the updater and renewal service.

The CLI rejects filename collisions, symlink paths and changed owned files. Writes are staged, synchronized and installed without overwriting existing files; the manifest is last. A bounded `ls-control scan-services` refresh follows. `installed` means files were applied and scanning completed, **not** that every running provider has adopted the grants.

On the tested TV, an already-running Homebrew JS service needed re-registration before the new permissions worked. Do not kill processes by a broad name match or restart SSH/dropbear. Confirm the exact service identity and that no installer operation is active before a targeted service restart. This procedure is not yet an automated user-facing installer. A transient `Message not processed` was also observed on a first read; never turn that into automatic retries of installation.

Remove with the same LS2 root. This version also recognizes the previous exact-service client plan; it does not accept arbitrary paths from a receipt. To upgrade those permissions, remove the old plan first, then apply the new one:

```sh
node scripts/update-permissions.cjs remove production
```

Removal deletes only files matching the receipt, removes the manifest first and refreshes LS2. Changed files or stale lock/staging files require inspection, not deletion by guesswork. After removal verify that cross-package calls are denied; cached permissions may require provider re-registration. The lab's post-removal check was rejected.

On the tested C3, scoped grants persisted through a software reboot. Activity Manager required that reboot to adopt the new canonical API grants. Keep the same setup directory to remove/update its owned permissions. The alternative `/var/luna-service2` root, factory reset and all power-loss cases are not validated. No additional boot hook is installed.

## Legacy: Build, signing and release checklist

```sh
scripts/test.sh
scripts/build.sh
scripts/build-updater.sh
```

The updater package is `com.cleanyourtv.updater_0.1.2_all.ipk`. Its service creates private state with its actual runtime UID (directory 0700, files 0600); no fixed UID is packaged. Earlier prototypes with incorrectly owned state require explicit migration.

The feed is `https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/update.json`. Requests are user-triggered. The HTTPS reader restricts redirects to this project's release assets and GitHub's asset CDN. RSA-SHA256 metadata is verified against the packaged `updater-service/release-public.pem`; it fixes the package URL, Home version, exact helper requirement and SHA-256. Homebrew checks the downloaded hash.

Example manifest input:

```json
{"schema":1,"release":"v0.8.0","home":"1.2.0","helper":"0.6.13","url":"https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v0.8.0/com.gathin.tvhome_1.2.0_all.ipk","sha256":"<actual 64-character lowercase SHA-256>","notes":"Release notes"}
```

Sign reviewed metadata using an explicitly supplied private key kept outside the repository:

```sh
node scripts/sign-update.cjs manifest.json /secure/path/private.pem update.json previous-update.json
```

The signer validates the result against the pinned public key and validates the previous envelope. One previous descriptor supports only its exact installed version; other older versions need manual updates. Every future stable release, even tooling-only releases, must retain usable signed metadata.

Before publishing:

- Verify scoped permissions after setup; running providers may require a controlled reboot before the update can start.
- Build public packages from clean sources, never personalized/live-TV backups. Exclude lab identifiers, loopback URLs, fake LG adapters, test keys and runtime state.
- Compute hashes from the final IPKs; sign with the real pinned key. Verify the candidate and previous IPK version, helper requirement, URLs and hashes against both signed descriptors.
- Keep the previous package downloadable. Test the public asset URLs before making the release latest. Do not publish the lab's signed envelopes to the stable feed.
- Include updater setup files, install/removal instructions, bootstrap limitations and recovery instructions. Publishing metadata and changing the stable feed are separate from merging this PR.

## Legacy: Validation and limits

On 2026-10-22, the corrected service completed a user-triggered isolated 1.2.0 → 1.2.1 update, restored the enabled renewal preference, and rolled back to 1.2.0 automatically. The user confirmed the preserved test tile, remote navigation and working production Home afterwards. Scoped permissions were removed and the temporary server stopped; production package metadata and helper processes matched the baseline.

An earlier attempt required manual journal recovery after the terminal installer reply was lost. It is not counted as unattended success. The subscription fix was then tested with a fresh transaction, without manual recovery. See [the detailed lab record](UPDATE-LAB-RUNBOOK.md).

The lab used fake LG responses/scheduling, an ephemeral signing key, loopback package delivery and a rooted TV. It does not prove real LG renewal, unrooted installation, maximum profile sizes, power-loss recovery, production permission persistence or public GitHub delivery. Local tests cover signature/policy checks, transaction failures, erased service state, manual preference overrides, service restart between UI actions and remote navigation. No new feature work is required for this PR.

### Renewal pause permissions

The scoped setup also grants only Activity Manager `create` and `cancel` to the renewal service, using the canonical `com.webos.service.activitymanager` API identity rather than the legacy call alias. On the tested C3, the installer derived service grants from the application and ignored the service-level `requiredACG`; declaring it in `services.json` alone was insufficient. Without these grants, even disabled renewal can stop an update at `renewal-recovery` before installation. Do not bypass pause confirmation or clear the transaction. Upgrade the scoped setup (remove the matching old plan, apply the new plan), then use Recovery to reconcile the pre-install transaction. Re-registration may be required for running providers.

### Published-package C3 validation (2026-10-23)

Home 1.2.0 → 1.2.1 using public GitHub assets completed, followed by signed rollback to 1.2.0. Journals confirmed complete/rolled-back and renewalRestored; renewal remained disabled. The user confirmed app order, arrows/OK, short Home and normal helper behavior. This release adds the scoped canonical Activity Manager grants needed to avoid the initial cancel-unconfirmed failure, plus Recovery refresh on relaunch. These final UI changes have regression tests; the exact v0.8.1 binaries have not yet had another on-TV cycle.

## Historical feed and publication guard

The v1.0.0 distribution uses Home 1.3.6 with Helper 0.6.17, matching
[`release-versions.json`](../../release-versions.json). Its signed Home rollback
retains the exact Home 1.3.5 package from v0.10.9, paired with Helper 0.6.17
under the reviewed compatibility record introduced in v0.10.10. See
[the update and rollback requirements](../RELEASE-0.10.10.md#updating-and-rollback).
In-app installation requires root, Homebrew Channel, scoped permissions and a
baseline accepted by the signed feed. Other baselines use the computer installer.
No-root TVs still cannot install packages through this service.

Startup health reads the version from the installed `appinfo.json`; it never
substitutes a source literal if the manifest cannot be read or validated.

Normal releases start automatically after a new `release` version in
`release-versions.json` is merged into `main`: CI builds and tests the exact
commit, prepares the draft and invokes signing/publication. For prepared-draft
repairs, `node scripts/publish-release.cjs vX.Y.Z` still queues the
protected GitHub signing workflow: both feeds and rollback assets are generated
from the exact release bundles, signed, uploaded and checked before publication.
`--check-only` validates existing feeds without signing or publishing. See
[the release process](../RELEASE-PROCESS.md) for setup, failure conditions and a
non-publishing test run. The read-only Release update feed workflow also checks
public release edits. Never carry an older Home feed forward when the release's
Home version has changed.

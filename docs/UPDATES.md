# Update Clean Your TV

> For 1.5.0 changes, known limitations and scoped acceptance, see the [release notes](RELEASE-1.5.0.md). Historical acceptance retains its original scope.

**Existing Root installations:** published 1.4.0 is incompatible with the original
1.3.0 System Updater destination inventory. Do not force that update or edit
private pins. An aborted pre-replacement attempt installed nothing; retain its
journal. The [supported replacement preparation](development/ROOT-OTA-13-COMPATIBILITY.md)
was delivered in 1.5.0. Use its verified recovery/replacement boundary; do not
force an old retained supervisor to accept incompatible destinations. New
candidate artifacts still need their own affected update/rollback acceptance.

## Choose your update method

| Installation | Method |
| --- | --- |
| No-root on an unrooted TV | Use cytv on your computer; keep Developer Mode active |
| Root, or No-root on a rooted TV, with compatible System Updater | Open Software updates and use **Update all** |
| Older installation without System Updater | Check existing state, then follow the preparation below |

Read the release notes and keep a working recovery path before changing packages.
A signed complete edition update needs compatible installed infrastructure;
a launcher IPK or legacy Home-only update cannot install that infrastructure.

## One-time computer preparation

1. Turn on the TV and select its saved connection in cytv.
2. Run **Check TV status**, then diagnostics. For a saved Root connection:

```sh
./cytv --language en status
./cytv --language en doctor --report
```

3. Resolve failed requirements and active or uncertain transactions using the
   installed Updater's matching **Recovery** flow. Existing Root Updater state
   can deliberately block reinstallation. Keep journals; do not bypass the block
   with `--yes`, a standalone IPK or an old updater.
4. Ensure the matching Home interface and edition recovery Updater are installed.
   Use a compatible complete release and review the [Root update requirements](../root-edition/UPDATES.md).
5. For a saved Root connection, choose **Enable updates for all TV components
   (root required)**, or run:

```sh
cytv enable-system-updates --edition root --host TV_ADDRESS
```

This separate action prepares the supervisor and captures verified rollback
packages from the installed components. It does not reinstall Home or change its
routing. It needs existing root/Homebrew services, TV Node.js 8+, suitable Python
3.9+ and compatible Home metadata (`systemUpdateProtocol = 1`). Eligible TVs can
receive [optional verified Python](OPTIONAL-PYTHON.md) during setup.
SSH access alone does not establish readiness. Partial or retained supervisor
setup needs inspection; do not delete state and rerun after an uncertain result.

For **No-root on a rooted TV**, first install matching Home/Helper/Home Updater
from the computer. Use an existing OpenSSH alias that logs in as root, and run
from the directory containing the generated `system-updater/` bundle:

```sh
python3 system-updater/setup-system-updater.py --bundle system-updater \
  --edition no-root --ssh TV_ROOT_ALIAS --apply
```

Without `--apply`, the script prints the permission plan. Use the packaged setup,
not repository source `system-updater/setup.py`.

If Home Root shows `Denied methods call status` immediately after preparation,
close and reopen **Home Root** once. If it persists, save diagnostics and check
status; retain supervisor and recovery state.

## Updating every component from the TV

**Update all** uses a signed release set for the installed edition:

- No-root: Home, Home Helper and Home Updater.
- Root: Root Home, Root Updater and the Home routing/recovery runtime.

Keep the TV on until verification completes. Packages and the previous release
are verified and cached before replacement. The worker can continue after Home
or the Updater closes. Root temporarily returns Home routing to LG. Explicit and
emergency stops are preserved; an update never clears them to resume Home control.
After supervisor setup, conflicting legacy Home-only installation is disabled to
protect the captured rollback baseline.

### Installation and recovery

Open the edition's Updater and choose **Recovery** to inspect a failed update or
restore the verified previous component set and saved profile. **Rollback loses
settings changed after the update.** Keep the transaction journal and cached
packages. An ambiguous installer result blocks both rollback and reinstallation;
reading a version does not prove the installer has finished. Do not clear a lock
or repeatedly submit an uncertain operation.

Local tests do not establish physical power-loss or complete system
update/rollback acceptance. Read [compatibility](COMPATIBILITY.md) and the
[Root update guide](../root-edition/UPDATES.md) for the exact tested scope.

## Candidate: Installer updates and product updates

**Unpublished Homebrew Installer:** Homebrew upgrades only CYTV Installer itself.
It does not upgrade installed Root Home or product updaters. Optional System
Updater preparation is explicit; product updates retain their signed complete-set
and recovery requirements. Deleting Installer alone leaves the product installed.
[Candidate setup and recovery](INSTALL.md#candidate-on-tv-root-installation).

<a id="unreleased-availability-correction-108--109"></a>

### Published availability correction (#108 / #109)

Published 1.4.1 checks the installed edition's supervisor and suppresses
same-component-version offers. Network, permission and state failures preserve
the last confirmed badge; they do not select another feed. Physical current,
newer, checking, failed and supervisor-absent cases remain unverified. See the
[delivered 1.4.1 scope](RELEASE-1.4.1.md) and its
[recorded acceptance and limits](RELEASE-1.4.1-ACCEPTANCE.md).

## Legacy Home-only updates (through v1.0.3)

For an older installation without System Updater, retain the matching recovery
path. Historical behavior, permission commands, signing and lab evidence are in
[the legacy updater reference](development/LEGACY-HOME-UPDATES.md). Do not apply
those permissions as a shortcut to current setup.

<a id="legacy-what-users-get"></a>
<a id="legacy-preserved-data"></a>
<a id="legacy-recovery"></a>
<a id="legacy-scoped-permission-setup-maintainer-procedure"></a>
<a id="legacy-build-signing-and-release-checklist"></a>
<a id="legacy-validation-and-limits"></a>
<a id="renewal-pause-permissions"></a>
<a id="published-package-c3-validation-2026-10-23"></a>
<a id="current-feed-and-publication-guard"></a>

Older links to legacy sections now lead here; use the corresponding section in
the reference above. Current release publication instructions are in the
[release process](RELEASE-PROCESS.md).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="updates-and-recovery--110"></a>

<a id="candidate-141-root-supervisor-prerequisite"></a>

## Candidate 1.5.0 Root supervisor prerequisite

Release 1.5.0 provides System Updater 1.1.2 for the updated
Root receiver/runtime flow. Existing 1.1.0 and 1.1.1 installations can use the
explicit [supervisor-only replacement](RECOVERY.md#replace-the-root-system-updater-candidate)
with a complete matching 1.5.0 installer before on-TV updating. That command
verifies the retained owner/code, archives the old supervisor state and preserves
Root and Home preferences. Do not modify retained state to force admission.
Each supported transition still needs matching artifact/device acceptance.
Published 1.4.1 used System Updater 1.1.1; its historical acceptance does not certify
this candidate. The fixed readiness service retains its bounded ownership-lock
wait without extending the launcher's health deadline.

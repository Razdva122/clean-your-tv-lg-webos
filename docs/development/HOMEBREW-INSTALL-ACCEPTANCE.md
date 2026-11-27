# Homebrew Installer candidate acceptance

The candidate package ID is `io.github.razdva122.cytvinstaller`. The October
and November device observations below used the earlier draft ID
`com.cleanyourtv.installer`. Their exact artifacts, hashes and outcomes remain
part of the historical record. Acceptance of the new ID requires a selected
IPK and tests of its package registration, foreground identity, app-originated
access, and removal. Record its product workflow against those same bytes.

The [October catalog record](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/edd4053f495cebf14f49ff5d9d9df1d60402a72b/homebrew/catalog/SUBMISSION.md)
records the earlier package's isolated installation and webOS 11/Homebrew
0.7.3 access failure. Its supervised test with a temporary upstream patch
applies only to that modified Homebrew installation.

Status: **Unreleased candidate. Final hardware acceptance is pending.**
No new model, firmware, webOS, input ABI, boot or Homebrew catalog compatibility
is established. All current implementation and code reviews were AI-assisted;
meaningful named human review and supervised TV testing are pending. This record
does not approve public promotion or catalog submission.

Candidate packaging uses canonical gzip metadata for shared IPK/control/data
and baseline archives: no filename, zero gzip timestamp, compression level 9
and OS byte 255. USTAR entries retain fixed 2024-01-01 timestamps and desired
ownership/modes. This removes host-dependent gzip headers; exact cross-host
hashes still require comparing final builds, including their compression bodies.
`cytv/package.py` is also copied into private bundles as `root_package.py`, so a
packaging-source change requires rebuilding private source closures, manifests
and the enclosing Installer/bootstrap pin even if public component IPKs match.
The published Helper archive and its existing pin stay unchanged. Source review
and focused format tests do not approve an exact candidate artifact; record the
final rebuilt hashes before physical acceptance or human artifact approval.

## Limited correction test (not product acceptance)

At correction source `1be47b2c`, isolated Installer0.1.0 passed installation,
actual package-file hashes and fixed HBC read-only inspection. Launch was
acknowledged but the foreground screen was not confirmed. Only Installer was
removed afterward, with terminal/absence proof and unchanged existing-product
baseline. The packaged console also completed read-only status. Private device
facts and logs are retained locally; no product update, activation, control,
startup, boot or rollback acceptance is inferred. The local reproducible IPK
SHA256 is `c3061975151fc9d25c54d7814cf670b0f7a9e3052dc4bf5d2ea9b1b0ee0077cd`
(59,725,142 bytes). Later integrated packages need their own identity and checks.

## Historical candidate identity and automated artifact evidence

The 2026-10-26 private staging/startup-guard correction supersedes the source and
startup representation below. These exact earlier artifacts remain historical
software evidence; rebuild corrected artifacts before candidate acceptance.

The integration base is `2b76134a` (includes `origin/release/next` at `fe7e8c1b`).
The earlier source is `7b8738bceaf1d5ffc79ba9987d27c2e12ef6619d`. Two builds from that source
produced byte-identical IPKs. Installer remains **0.0.0 development**, with
embedded Root **0.3.0**, Root Updater **0.2.1** and System Updater supervisor
**1.0.0**; these are not selected public Homebrew versions.

| Final automated artifact | Exact value |
| --- | --- |
| IPK filename | `com.cleanyourtv.installer_0.0.0_all.ipk` |
| IPK bytes | 59,713,434 |
| Installed regular bytes | 63,982,503 |
| IPK SHA256 | `e498f6164c4d10a0aa1be06bb433de581b09861e7f8ff53412a0c5630186e506` |
| Serialized local manifest SHA256 | `0ad3e0e7e3e6ca78c5ecc6cacbf6dd9ec1649c585a0e8097e49742ab349d7b6d` |
| Offline payload manifest SHA256 | `579b6fc21603397a2ea79bf9bb91983c4cc23cde474625bba1c53a812e03d40b` |

Local artifacts and redacted verification/review evidence are preserved outside
the temporary worktree at `homebrew-candidate-7b8738bc`. These are development artifacts;
manifest URL strings do not establish reachable public downloads. Earlier
`b45dd5...`, `936c4f...` and `11d35b...` prototypes are superseded for acceptance.

The final all-scopes `bash scripts/test.sh` run on the source above passed with
exact Helper Node 0.12.2 enabled. The Python suites ran 1,151 cases with 23 environment skips (21 optional Qt
cases and two isolated-Linux-root runtime cases). JavaScript/native/compatibility
and all ten locale browser checks also passed. The preserved test log and
implementation PR retain the command and scope. Focused real-manifest tests
reject changed same-version packages, changed bundle identity and absent original
bootstrap receipts before standalone continuation. Actual Node 8 runtime/bridge,
source-free payload, release/catalog metadata and reproducibility checks passed.
Browser tests mock only the HBC boundary and cover ten locales at 1280×720 and
1920×1080; they do not invoke a TV. These establish software properties only.

Runtime preparation requires **335,544,320 bytes (320 MiB) free in `/var/lib`
after Installer is installed**. The embedded normalized runtime archive is
51,462,118 bytes (unchanged pinned runtime). These values are not a measurement of
actual TV package-manager staging or peak storage. Record free space before IPK
installation, after package installation, during runtime/product staging and after
completion on the TV. If the eventual frozen source/components/versions differ,
rebuild and record the exact IPK, bundle, runtime and serialized manifest hashes
again; do not reuse earlier acceptance by version label alone.

## Supervised session identity (not supplied)

| Field | Recorded value |
| --- | --- |
| Candidate source commit / sourceApproval | NOT RECORDED |
| Exact Installer IPK name, byte size, SHA256 | NOT RECORDED for physical session |
| Root / Root Updater / supervisor bundle and IPK hashes | NOT RECORDED for physical session |
| Offline payload manifest / runtime archive / runtime binding hashes | NOT RECORDED for physical session |
| Serialized Homebrew manifest hash / frozen original URLs | NOT RECORDED for physical session |
| TV model / firmware / webOS | NOT RECORDED |
| Homebrew Channel version / actual effective UID | NOT RECORDED |
| Node version / architecture / userspace ABI / loader | NOT RECORDED |
| Python version, system/private path and smoke outcome | NOT RECORDED |
| Initial installed product, profile and recovery/operation state | NOT RECORDED |
| Free space and peak package/runtime/product staging | NOT MEASURED |
| Supervising human / meaningful code reviewer / test date | PENDING |

Keep credentials, local addresses, SSIDs, app inventories, private logs and captures
outside this public record. Record only redacted observations and artifact IDs.
Disruptive removal, power-loss, frozen-UI and rollback tests require a supervised
session with known-good recovery and separately retained artifacts.

## Task 8 physical matrix

Every row below is **NOT RUN** on the new installation path. Automated tests and
historical acceptance cannot be substituted for actual observations.

| Scenario | Required observation | Physical result |
| --- | --- | --- |
| Clean HBC install with suitable system Python | One confirmation covers Root Home, Root Updater, System Updater, automatic import from a compatible previous Home when present, and activation. Verify installation, activation readback, opening Home and subsequent Home-button routing independently. | NOT RUN |
| Clean HBC install without suitable Python | The same confirmation covers pinned offline runtime preparation. Verify that reinspection of the reviewed payload admits Root before product submission, then check activation and Home routing. | NOT RUN |
| cytv install → TV maintenance | Same profile, identity, ownership and recovery records without reinstall/reset | NOT RUN |
| HBC install → cytv maintenance | Status, restore and complete removal without reinstall | NOT RUN |
| Concurrent cytv/TV operations | Exactly one owner; second client blocked safely | NOT RUN |
| Complete signed upgrade | Matching signed component set and preserved profile; independent updater remains usable | NOT RUN |
| Complete signed rollback | Exact previous set/profile and valid recovery bindings; later settings loss explained | NOT RUN |
| Lost UI / network during each stage | Original operation/snapshot persists; status first; no blind package replay | NOT RUN |
| Reboot/power interruption during each stage | Recovery respects exact receipts and emergency/off; uncertain outcomes stay blocked | NOT RUN |
| Triple-Home emergency release | LG Home restored and emergency-off remains set | NOT RUN |
| Frozen Installer/Home UI and emergency release | Recovery independent of UI; LG Home and ordinary remote input remain usable | NOT RUN |
| Standby/wake | Actual routing/recovery and normal arrows, OK, Back/Cancel, volume/pointer | NOT RUN |
| True cold boot (separate from standby/software reboot) | Observed startup routing/recovery and normal remote input | NOT RUN |
| Direct Root Home deletion through LG/HBC | No stranded routing or recurring worker; owned 50 hook inert; retained recovery coherent | NOT RUN |
| Direct Root Updater deletion through LG/HBC | Owned 51 hook inert; live workers stop/refuse activation; independent recovery remains coherent | NOT RUN |
| Direct System Updater deletion through LG/HBC | Owned 52 hook inert; live worker/activities stop; product recovery remains coherent | NOT RUN |
| CYTV Installer-only deletion through LG/HBC | Separately installed product/profile/updaters remain coherent; interrupted snapshot not lost | NOT RUN |
| Complete product removal through either client | LG Home restored; exact owned package/registration/startup cleanup; recovery retained | NOT RUN |
| Standard System Updater preparation | A fresh install registers all three components and captures the exact installed baseline. Opening maintenance on an older installation preserves its recorded component set. | NOT RUN |
| Automatic Home settings transfer | With a valid previous Home, transfer its supported personalization and verify the files. A clean TV installs with fresh settings. Confirm there are no separate prompts for either path. | NOT RUN |
| No-root cytv regression | Existing installation, maintenance, emergency release and recovery still work | NOT RUN |

Keep unavailable/failed scenarios explicit. Resolve material removal/recovery
failures before promotion. Do not infer safe external deletion from a broken boot
symlink alone: live package-disappearance handling and routing must be observed.

## Historical evidence stays separate

Root **0.2.0**, Root Updater **0.2.0**, supervisor **1.0.0** on
**OLED55C3RLA / firmware 43.21.71 / webOS 11.2.0**, source `d344d92`
(product contents identical to `4b66951`), passed the controls/emergency and
standby checks recorded in the [published acceptance](../RELEASE-1.2.0-ACCEPTANCE.md).
True cold boot and complete signed upgrade/rollback remained untested. Those
results are not Root 0.3.0 or Homebrew Installer acceptance. Later diagnostics,
fonts or integration fixes do not close unrelated hardware reports.

## Review inventory: persistent files, permissions and endpoints

This inventory describes the implemented candidate's bounded device effects for
implementation-PR review. Paths containing `<id>`, `<lease>` or `<sha256>` are
validated identifiers, not arbitrary caller paths. Directories listed with
contents cover that component's existing files, receipts and caches; this feature
reuses their recovery contracts rather than adding a competing updater.

| Device scope | Contents and ownership/lifetime |
| --- | --- |
| `/media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller/` | Installer web assets, fixed `bootstrap.js` and verified `payload/` containing Root, Root Updater, supervisor, baseline, the edition reader and the runtime archive, manifests and licenses. Archive modes are 0644 or explicitly executable 0755. Under the prior ID, SDK package directories and files were observed with mode 0777. The reader accepts those modes only for root-owned package data verified against the pinned outer manifest and file digests. |
| `/media/developer/apps/usr/palm/packages/io.github.razdva122.cytvinstaller/packageinfo.json` | Package metadata owned/removed by the package manager. Removing Installer does not request product removal. |
| `/var/lib/clean-your-tv-installation/` | Shared root-owned 0700 store; 0600 `operation.json` durable owner/lease, `request-<id>.json`, `submission-<id>.json`, `removal-<lease>.json`, `ownership.lock` product mutex and `worker.lock` submission/store mutex. Exact journals remain authoritative across clients. |
| `homebrew-activation.lock` in the shared store | A root-owned 0600 file serializes setup approval, revocation and the first durable enable claim. The installer releases the file lock after each short operation and retains the inode for the next caller. |
| `homebrew-activation-token.json` and `homebrew-activation.json` in the shared store | Private 0600 records. A fresh setup request obtains a 32-hex token. After candidate and device preflight, the approval records the Installer ID, install operation ID, candidate SHA-256 and token. The submission receipt binds the same issuer and token. Explicit Restore or product removal revokes the approval by unlinking the token and approval under the lock. A later approval must match its own submission. |
| `activation-<operation>.json` in the shared store | Private 0600 attempt record. The original worker records its PID, operation ID, product lease and launch acknowledgement, starting in `ready`. After the install mutex is released, the guarded activation changes the attempt to `claimed` before enabling Home. A successful launch reply and matching routing readback allow `active`. Failure can leave `unverified`, and interruption can leave a claim. The durable attempt remains with the request for read-only status after UI close, Restore or a generation change. Status cannot resubmit enable. |
| `/var/lib/clean-your-tv-installation/request-<id>/` | Original checked private worker/payload snapshot; 0700 directories, 0600 files and `worker.log`. Worker lifetime is independent of Installer UI. Retained for checked continuation and diagnosis, not deleted to reset an operation. |
| `/var/lib/clean-your-tv-root/` | Existing root-owned recovery/deploy code and `runtime/`, `service/`, manifests, `deploy.json`, `install-terminal.json`, `personalization.json`, `recovery-provision.json`/pending, `ls2-provision-snapshot.json`, `system-permissions.json`, `activity-registration.json`, startup/binding and routing/intent/update receipts/locks. Private files normally 0600, directories 0700, fixed executable launchers/runners 0700. Retained after removal; verified cytv reinstall may create `.archive-<id>`, never blind deletion. |
| `/var/lib/clean-your-tv-root-updater/` and `/var/lib/clean-your-tv-system-updater/` | Existing private 0700 `code/`, `cache/`, bootstrap/infrastructure/installed-package/installed-terminal receipts, original full-bundle/IPK `bootstrap-bundle.json` continuation binding, transactions, baselines/profiles, `run-service`, bindings and `startup-hook.json` (plus `startup-hook.previous.json` on exact legacy migration). Full removal disables/archives owned state under `.archive-<id>` and retains removal evidence. Regular data 0600; fixed runners 0700. |
| `/var/lib/clean-your-tv-root-staging/cytv-homebrew-<32hex>/` | Per-call, root-owned 0700 execution snapshot. The bootstrap copies and verifies 0600 files against the pinned inventory. Full staging includes `root/`, `root-updater/`, `supervisor/`, `baseline/` and `edition/`. Code-only staging uses the Root Updater support files. Python runs from this private tree. After child exit the bootstrap checks and removes its own entries and retains unexpected changes. It removes a newly created staging parent only if still empty and unchanged. |
| `/var/lib/clean-your-tv-installer/cytv-root-install-<id>/package.ipk` | Existing bounded observed-install staging; exact terminal event must match it. Preserve uncertain operation evidence. Root-owned 0755 staging directories and 0644 IPK permit package-manager read access; no private bundle is exposed and no user-supplied path is accepted. |
| `/var/lib/clean-your-tv-python/<sha256>/` | Immutable pinned private CPython slot with `.cytv-runtime.json` inventory; 0755 directories/executables and 0644 regular data, root owned and not group/world writable. Pin is `4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea`. No `/usr/bin` replacement or global PATH change. |
| `/var/lib/clean-your-tv-python/.stage-<id>/` and `.install.lock` | Checked runtime staging/tree and 0600 immutable-promotion lock, separate from the product lease. Only the exact owned runtime stage is cleaned; drift is retained. Referenced slots remain after application removal. |
| Component `python-launcher` and `python-runtime.json` | Existing binding under each Root/Root Updater/System Updater private state directory; launcher 0700, receipt 0600, plus checked `python_binding.py`/`python_boot.js`. Maintenance reuses the original verified interpreter without downloads. |
| `/tmp/cytv-product-<id>/`, `/tmp/clean-your-tv-root-<id>/`, `/tmp/cytv-root-updater-<id>/`, `/tmp/cytv-system-updater-<id>/` | Existing host-transfer staging (private umask 077); not new public endpoints or durable authority. Failed staging may remain and must not be confused with completion. |

Independently SHA256-pinned package DATA reads allow any owner on the exact
shared SDK containers `apps`, `apps/usr`, `apps/usr/palm`, and their
`applications`, `packages` and `services` containers. The expected hash comes
from a separately trusted source. Own package leaves and files still require
trusted owners, and descriptor/path/inode bindings remain strict. Unanchored
reads retain strict leaf permissions and the legacy UID 501 allowance for the
exact shared `packages` container. Private code and state use separate readers.

The shared removal program also allows different owners on these SDK containers.
It enters each verified parent without following symlinks before removing a
project path authorized by the removal flow. The caller, private directory and
staging ownership requirements remain in force.

Package-managed product scopes remain `/media/developer/apps/usr/palm/` under
`applications/<app>`, `services/<app>.service`, and `packages/<app>` for
`com.cleanyourtv.root.preview`, `com.cleanyourtv.root.updater`, and optional
`com.cleanyourtv.system.updater`. Complete-project removal also handles the
existing ordinary `com.gathin.tvhome`, `com.local.nativehome`, and
`com.cleanyourtv.updater` if present, using their owned disable/registration checks;
it does not remove foreign applications. App/GUI mutable preferences keep their
existing package/profile storage; changing installation clients does not reset them.

### Owned private startup wrappers

| Regular 0700 file in `/var/lib/webosbrew/init.d/` | Private guard |
| --- | --- |
| `50-clean-your-tv-root` | `/var/lib/clean-your-tv-root/startup_guard.py` |
| `51-clean-your-tv-root-updater` | `/var/lib/clean-your-tv-root-updater/code/startup_guard.py` |
| `52-clean-your-tv-system-updater` | `/var/lib/clean-your-tv-system-updater/code/startup_guard.py` |

Each wrapper invokes its private `python_boot.js` binding gate, then validates
owner package metadata against its phase-selected private inventory before marking
normal Root boot or starting its updater. The Root admission action writes the
current-kernel marker and returns while the transient HBC failsafe may still be
set; it never waits for that flag or enables intent. Later rearm retains the
marker, cleared flag, current identity, profile, guardian and intent gates. No shared package startup bytes execute. V3 receipts bind exact wrapper
hash/path/owner; exact v1 regular and v2 link receipts retain prior proof during
migration. An exact owned link can be removed after its target is replaced or
missing. Unknown hook/receipt bytes remain collisions. Package loss stops rearming;
independent private recovery remains available to restore LG Home. Live worker and
ActivityManager disappearance protections still require physical acceptance.

HBC's initial privileged installed-app launch is an explicit trust assumption.
The built bootstrap pins the outer manifest digest, and later staging reads and
writes exact bytes against that original inventory. A newly self-consistent source
manifest cannot authorize replacement code. Runtime preparation separately stages
the authenticated archive privately before extraction/verification. Never chmod
shared platform directories; new package archives explicitly secure only their
own app/service/package leaves.

### Cold-boot DATA authority correction

Observed cold-boot SDK mode changes are a measured layout, not a firmware-wide
claim about which component changed permissions. No chmod/chown repair is used.
Root selects its private current descriptor and checked original cached IPK.
Standalone and System publications tag that existing descriptor with their
transaction id; standalone tags retain the last System publication id across
successive updates. These fields are private provenance, not signed/public
manifest bytes or a second current record. A merely captured System baseline
cannot override a later standalone publication. A captured prior archive may
have different control/tar bytes; its independently checked private full payload
inventory must equal the committed original before that prior can explain an
active publication window. Installed bytes never choose between anchors. The explicit initial provisioning
reader uses the original private bundle/release pin and terminal; normal startup
never falls back to that bootstrap release.

System setup retains its independently pinned own IPK before submission, then
publishes its own inventory only after the original terminal and full installed
readback. Its product baseline does not prove the supervisor's own package.
Missing legacy self proof inhibits automatic startup; explicit continuation may
retain a supplied original IPK only against the existing original bootstrap pin.
System completion also refreshes Root Updater's existing original-file/mode
inventory. Root baseline capture verifies against private originals and keeps
archive modes rather than learning modes or hashes from writable SDK files.

Health selects only the phase-authorized candidate after actual terminal success,
or prior after proved rollback. Unknown submissions remain unknown and cannot
be replayed. A known owned replacement window may run only its original private
recovery worker; it does not establish ordinary presence or normal rearm.
Existing live input health keeps the exact committed prior through untouched
preparation/download and the pre-ticket suspension window. Normal rearm remains
current-only; the actual suspend captures active intent before disabling it. All
required owners are checked before a touched transition is deferred, so another
owner's absence or integrity failure stops the worker. Legitimate sticky shared
ancestors remain readable; own SDK special bits, shared setid and private modes
stay strict. Unchanged installed metadata is reread on every two-second observation; only
expected inventories are cached in process against private anchor/cache identity.

These private helper/inventory changes require checked removal/rebootstrap or
an explicitly authenticated original-source continuation. Do not patch retained
private code/receipts or clear disabled/emergency intent. Installation and
activation remain separate. New exact artifacts still require supervised cold
boot, standby and controls acceptance; earlier hardware records stay historical.

### Existing LS2 permissions and registrations reused

Installer creates no new generic execution service, shell input or service port.
Its browser bridge calls only
`luna://org.webosbrew.hbchannel.service/exec` with fixed
`/usr/bin/node /media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller/bootstrap.js`
and action-specific validated arguments. Effective UID is checked again in the
backend. It does not patch Homebrew's runner or firmware Node/service launcher.

For a fresh installation or verified clean removal, the bootstrap also runs the
fixed `edition/edition.py` entry from the private snapshot. Its inventory includes
`cytv/__init__.py`, `checks.py`, `errors.py` and `root_capabilities.py`.
The reader checks the Home settings and System Profile interfaces. When the
System Profile service is positively absent it uses the shared desktop
classifier's fixed queries for system information, KeyFilters, native Home,
embedded compositor and ribbon. It returns an edition decision to the UI.
The No-root outcome directs the owner to computer or Android setup for
pairing and installation. An inconclusive result offers another status check.
An older Node runtime can report the installer prerequisite before loading the
edition reader. [Edition reader](../../homebrew/edition.py) · [Private staging](../../homebrew/runtime.js)

Existing Root recovery, Root Updater and System Updater each use owned service,
role, client and API files under `/var/luna-service2-dev/{services.d,roles.d,client-permissions.d,api-permissions.d}/`.
For each exact service ID (`com.cleanyourtv.root.preview.service`,
`com.cleanyourtv.root.updater.service`, `com.cleanyourtv.system.updater.service`),
`services.d` uses `<service-id>.service`, `roles.d` and `client-permissions.d` use
`<service-id>.service.json`, and `api-permissions.d` uses `<service-id>.api.json`.
The package manager's existing `manifests.d/<app-id>.json` registration remains
subject to matching identity/receipt checks during removal. Registration
snapshots retain original bytes, mode/UID/GID and installed hashes; cleanup
restores/removes only matching owned state. Runners use the immutable firmware
Node bootstrap and private component code. The existing legacy updater permission
files are `com.cleanyourtv.updater.permissions.json` under the API, client and
manifest directories in `/var/luna-service2-dev` or `/var/luna-service2`; only
receipt-proven lockdown/removal is allowed.

Root grants its own GUI `status`, `restore`, `enable`, `confirm`, `listApps`;
ActivityManager calls/callback are scoped to recovery and the fixed
`com.cleanyourtv.root.preview.service.recovery` activity. Its separate
`/var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json` references
private `/var/lib/clean-your-tv-root/permissions/{client.json,api.json}` for
ActivityManager `list/create/cancel/adopt/complete`; the ownership receipt is
`system-permissions.json`. The fixed installer activity sender is
`com.webos.lunasend-cytvrootrecovery`; creator/definition readback is checked.

Root Updater grants Root Home and its own GUI scoped
`check/status/reconcile/rollback`; only Root Home gets
`install/restoreProfile/ready/confirm`. Optional System Updater grants Home,
Root Home and both updater GUIs `check/status/rollback/reconcile`; only Home and
Root Home get `install/restoreProfile/healthy`. Exact service/app sender patterns
are those of `permission_plan()` in the component setup sources. Existing legacy
permission lockdown remains receipt-bound when System Updater is prepared;
complete removal uses the matching legacy permission and EIM input cleanup.

Existing Luna calls cover local application/package discovery and observed
installation/removal, recovery/routing, service refresh, ActivityManager,
application launch and EIM cleanup. They do not add a network listener. The
candidate's scope does not expand telemetry, wallpaper, rooting or firmware work.

### Network endpoints

- TV Installer runtime/payload verification and installation are **offline**;
  the runtime upstream URL is authenticated build provenance, not a TV download.
  Existing host cache uses the immutable python-build-standalone `20261021`
  GitHub release artifact pinned in `cytv/python_runtime.py`.
- HBC's existing exec LS2 endpoint above is local. Existing product updater feeds
  are GitHub project `/releases/latest/download/root-update.json` and
  `/releases/latest/download/system-update-root.json` (or the existing No-root
  counterpart). Signed component URLs stay under immutable project release URLs;
  only existing GitHub release asset redirect hosts
  `release-assets.githubusercontent.com` and `objects.githubusercontent.com` are
  allowed. No new feed trust or arbitrary URL execution is introduced.
- The **intended, unpublished/unverified** catalog manifest endpoint is the project
  `/releases/latest/download/homebrew-manifest.json`; its future IPK URL is an
  accepted immutable project release asset. No reachable public assets or catalog
  availability are claimed. Icon/source URLs are fixed by later accepted metadata.
- cytv keeps existing trusted SSH, local discovery, SSAP/control and icon transport.
  This feature adds no server ports or new authentication transport. No private
  device addresses, credentials or app inventories belong in this record.

Source references: [fixed bridge](../../homebrew/app/bridge.js),
[bootstrap/runtime](../../homebrew/bootstrap.js),
[shared ownership](../../root-edition/installation.py),
[worker snapshot](../../root-edition/install_driver.py),
[device operations](../../root-edition/install_device.py),
[startup ownership](../../root-edition/startup_hook.py),
[recovery provisioning](../../root-edition/provision.py),
[activity permissions](../../root-edition/system_permissions.py),
[Root Updater grants](../../root-edition/updater/bootstrap.py),
[System Updater grants](../../system-updater/setup.py), and
[private Python binding](../../root-edition/python_binding.py).

## Publication and handoff checklist

- [x] Run and record final whole-branch automated verification on a stable commit.
- [x] Whole-branch review, push and [draft implementation PR #74](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/74)
  to `release/next` completed; PR attached and needed artifacts preserved outside
  the managed worktree for cleanup.
- [ ] Complete every physical matrix row with exact observations/artifacts, resolving
  material recovery/removal failures; obtain genuine named human review.
- [ ] Freeze independent nondevelopment Installer version and exact artifact hashes.
- [ ] Add the accepted originating-release record only after those gates pass.
- [ ] Verify normal protected publication, exact public manifest/IPK/checksum/feed
  bytes, screenshots and required issue notices/statuses.
- [ ] Submit catalog change with accurate AI disclosure and human/TV evidence;
  catalog-maintainer approval remains distinct from submission.

`homebrew/release.json` is absent: promotion is disabled. Later acceptance must
bind exact IPK and serialized manifest hashes, frozen original URLs, independent
Installer version, originating project release selector and genuine hardware/human
references. Signing/publication compare sourceApproval to the immutable committed
record; mutable BUILD-INFO is insufficient. Unaccepted/stale-record candidate CI
is optional; selected promotion requires successful workflow and Homebrew job.
Unrelated releases carry an approved older Installer's bytes/metadata unchanged,
with honest embedded versions and original immutable URL. See
[packaging/release contract](../../homebrew/README.md) and
[release flow](../RELEASE-FLOW.md#homebrew-installer-candidate-and-promotion-gate).

## Combined correction verification

Source `cb1c789a` includes Chinese #76 and correction #77. Full local suite passed
1,178 Python cases (two isolated-Linux-root skips), with Qt enabled, JS/native/
compatibility, twelve-locale browser checks and actual Helper Node0.12.2. Actual
Node8 runtime/bridge checks passed. Required Linux/macOS/optional-runtime CI passed
in run40315333002. macOS console/desktop embedded155-file payload and frozen GUI/
package smoke passed. Two Installer0.1.0 builds were byte-identical: SHA256
`f29e4975537735e53527a1296326e2fd46428393eac88eeb07a55e099d814c2b`,
61,228,554 bytes; payload manifest
`54d4c78d93d21f1e128223eeb4fe858e4e222008e2eeb37989a7fe08e327e964`.

The combined isolated TV test passed installation, actual file hashes and fixed
HBC read-only inspection. Bounded foreground observation after one launch
confirmed Installer on the third sample; the earlier immediate read was premature.
Exact Installer-only terminal removal/absence and unchanged prior-product baseline
passed. This proves application foreground identity, not manual screen/remote
acceptance. Supervised product transition was subsequently authorized; its results
are still pending. All-platform integrated builds and final publication acceptance
remain separate. No Homebrew public approval record is added.

## Issue #116 access preflight follow-up (2026-10-30)

On 2026-10-30 Homebrew 0.7.3 was the latest release and the webOS 11 correction
#233 was available only in upstream source. The candidate classified the exact LS2
`exec` denial and displays a localized prerequisite/workaround screen. It retains
saved requests and provides read-only inspection retry without resubmission or
permission changes. No supported minimum Homebrew version can be named yet.
See [current prerequisites](../../homebrew/README.md) and [PR #117](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/117).

This is source/browser verification only. No new device operation or physical
acceptance was performed; all earlier C3 observations retain their original
artifact and temporary-prerequisite scope. Public promotion remains disabled;
exact-artifact full installation-path acceptance and named human review remain
required after a supported prerequisite exists.

## Homebrew 0.8.0 verification (2026-11-25)

[Homebrew Channel 0.8.0](https://github.com/webosbrew/webos-homebrew-channel/releases/tag/v0.8.0)
includes [upstream #233](https://github.com/webosbrew/webos-homebrew-channel/pull/233).
The candidate's denial screen now directs webOS 11+ users to update Homebrew,
retry the read-only status check, and use the computer or Android installer if
access remains denied. The October experiment above remains scoped to its
temporary patch.

Development preparation used the macOS ARM64 checkout. The official Homebrew
IPK matched GitHub's declared SHA-256
`44bbca8e7b86a2491ec3ffed0d469094602b9f965c6dbd05bac5899392bececa`.
The published service still contains the `stdoutString` response field used by
the CYTV bridge.
The local Installer 0.0.0 IPK passed the repository manifest and payload checks
at 117,599,636 bytes (122,658,589 installed bytes), with SHA-256
`68e332018dac843f930f02d5a50248e54f3843944797b6c5b8aa54ffaca398ae`.
It is a development build from the working checkout. Select and record the
checkout and exact artifact that will be installed after the TV handoff.

Local Homebrew payload, runtime, bridge and continuation checks passed.
The source and compiled browser suites passed for 13 locales at 720p and
1080p. The wider host Installer suite reported four wallpaper GUI failures
from English assertions against Russian translations. The wallpaper suite
passed all eight tests when run independently with English selected.

The project C3 was reachable over SSH and reported Homebrew 0.7.3 before the
planned retest. The maintainer scheduled TV changes after the C3 checks for
[release candidate #827](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/827).
The following device cases are pending. Record the actual package identities,
preconditions and result of each case before counting it toward acceptance.

| Case | Expected result |
| --- | --- |
| HB08-01 | Official Homebrew 0.8.0 update completes, installed version matches, configured root service and recovery access are available, and existing CYTV state matches its baseline. |
| HB08-02 | The exact CYTV Installer IPK installs and launches. The actual TV app completes read-only inspection without the LS2 denial and shows the setup or maintenance screen matching the starting product state. |
| HB08-03 | Clean setup and runtime preparation complete with measured staging/free space, and both computer/TV continuation paths preserve and resume the same operation. |
| HB08-04 | Upgrade, interruption/recovery, rollback and optional System Updater behavior satisfy the existing cases in this ledger. |
| HB08-05 | Affected product Home activation, network Home, physical emergency controls, standby and separate AC cold boot meet the planned outcomes. |
| HB08-06 | Installer-only and component/full-product removal meet their separate cleanup and preserved-state expectations. Run only after cases needing the corresponding installed state. |
| HB08-07 | While Root Home is installed, confirm its LG firmware-blocking UI can read and change the Homebrew setting, verify it after a software restart, and restore its original value. Keep this result with the firmware-blocking evidence. |

Device reconciliation at handoff: seven selected groups, zero new observed
passes or failures, zero covered by matching earlier evidence, all seven pending
the C3 release-QA handoff. The remaining publication and human review gates
are tracked above.

### C3 first pass on released Homebrew (2026-11-26)

The maintainer handed back the project OLED55C3RLA after #827. The Mac used
the paired network remote and existing trusted SSH connection. The previous
C3 record identifies firmware 43.21.71 / webOS 11.2.0. Physical remote model
unknown. Homebrew's built-in self-update downloaded and verified 0.8.0, then
installed it over 0.7.3. SSH remained available, Homebrew reported effective
root and blockUpdates enabled, and the existing Home and Ambient app metadata
hashes matched their baseline. No-root Home 1.22.0, Helper 0.11.0 and Ambient
0.0.7 were installed, with Root Home absent.

Selected [CI run 45761587837](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45761587837)
at source `1337f4c6` from the 1.29.1 release cycle. Workflow and Homebrew
job succeeded. Installer 0.0.0 with Root 0.25.0, Root Updater 0.6.8 and
System Updater 1.2.11 measured 123,903,520 bytes. The CI artifact ZIP matched
GitHub's digest and the staged IPK matched its manifest and build record
(`c32390775a58c1199f5df64a514bd522a48ba5696b508c6a8cdddd7787a37785`).
The LG package manager reached installed, all 174 installed application files
matched the IPK, and the Installer reached foreground. Available /var/lib
space measured 447,156 KiB before and 447,148 KiB after installation.

| Group | Observation on the original CI artifact |
| --- | --- |
| HB08-01 | Passed self-update, version, configuration and SSH readback. |
| HB08-02 | Failed. The genuine Installer showed the unsupported screen. Its own read-only bridge returned installer_unavailable. The packaged inspect entry reproduced “Execution snapshot too large” over SSH. The manifest has a 32,562,014-byte Root IPK, the same bytes in the rollback cache, and 72,459,002 bytes of staging inputs. The TV runtime allowed 16 MiB per file and 32 MiB in total. No product submission was possible. |
| HB08-03/04 | Clean setup, runtime/continuation and subsequent product transactions depend on passing the failing inspection. Neither client started a Root installation. |
| HB08-05 | The paired network Home test on the existing stopped No-root setup passed. Media Player held foreground before one HOME, and LG Home stayed foreground for the one-second readback. Root activation, emergency and power cases need the installed Root product. |
| HB08-06 | Installer-only removal reached removed. Both SDK package and app directories disappeared. Existing Home and Ambient metadata still matched the baseline. Direct removal of the Root components and full-product removal need the corresponding installed components. |
| HB08-07 | Root Home was absent. Its configuration switch and restart verification require an installed Root product. |

Original-artifact reconciliation: seven groups, one pass, one failure, two
partial groups with independent subcases observed and three groups blocked by
missing product setup. The remaining portions of the partial groups require
Root installation. The owner authorized clearing CYTV test data for the clean
setup. The next artifact needs the affected inspection and dependent device cases.

The ordinary computer client also returned stopped for the existing No-root
Helper. Corrected development IPK SHA-256
`be6d82a787ff68d540d9c1db6faefcbd1151919143219342ec77f6a229c74732`
measures 123,903,688 bytes. Its component inventories match the trusted
1.29.1 CI artifact. The embedded runtime staging module, its manifest and
bootstrap pin, and the localized denial instructions changed. The specific
oversized-media regression failed before the change and passed afterward.
The runtime and bridge tests, 20 Homebrew Python tests and the browser suite
against the compiled IPK UI passed.

The source CLI without a prepared desktop payload could not start device
cleanup. The verified 1.29.1 macOS ARM64 CLI resumed the same cleanup goal
and requested an AC power cycle before its final sweep. This is setup for
the clean-install case. A zero exit with a pending power cycle is an
intermediate state.

### C3 clean install and removal with setup checks (2026-11-26)

The project OLED55C3RLA ran firmware 43.21.71, webOS SDK 11.2.0 and stock
Homebrew Channel 0.8.0. The first attempt stopped at the existing installation
check. A previous package removal had left the Root deployment record at
`uninstalled-state-retained` after its packages and startup hooks were gone.
The matching desktop installer resumed full removal. It reached
`restart-required`, then verified clean after a confirmed software restart
and continuation of the same operation.

The exact development IPK from source `506e70e8` was 122,169,002 bytes, SHA-256
`24ad97ea5d027ea23b945b324d56b6757e3815e1ad63525911b77ce56af3871e`.
The installer was 0.0.0 with CYTV 0.24.3 diagnostic metadata, Root 0.25.0
and System Updater 1.2.11. The C3 used the ordinary Homebrew catalog UI with a
temporary local feed. Device controls were driven by automated UI input and
the paired network remote. The physical remote model was not established.

| Case | Observed result |
| --- | --- |
| HB-E2E-01 | Previous retained state was resolved through full removal and verified restart. Inspection admitted a clean setup. |
| HB-E2E-02 | Homebrew installed and launched the exact IPK. One confirmation installed Root and System Updater. The operation reported verified completion and Root Home appeared in the foreground. |
| HB-E2E-03 | The first-run setup opened with theme previews. Liquid Glass applied and remained selected after the network remote sent HOME once from Media Player to Root Home. |
| HB-E2E-04 | Debloat showed limiting ad tracking was already applied. Applying the sports notifications option changed it from On to Off. Both that change and restoration to On passed a fresh readback. Back returned to Root Home. |
| HB-E2E-05 | The matching desktop installer verified full product removal after a verified software restart. Project packages, startup hooks and owned registrations were absent. Only allowed ownership records remained. One network HOME from Media Player opened LG Home and it stayed in the foreground for the one-second readback. |
| HB-E2E-06 | The temporary feed came out of Homebrew settings, and Installer-only removal completed through the package manager. Homebrew 0.8.0 and its prior root and update-blocking settings remained in place. |

All six focused device cases passed. The previously verified on-TV QR and
desktop-schema JSON result is reusable for the same IPK. The browser suite
also covered the mobile download and the prefilled GitHub issue. This
development run did not cover OTA, standby, loss of mains or physical key
timing. Final release and catalog acceptance require the selected release
artifact.

### C3 full removal from the TV Installer (2026-11-27)

The project OLED55C3RLA used firmware 43.21.71, webOS SDK 11.2.0 and stock
Homebrew Channel 0.8.0. Installer 0.0.0 from source `9b7ce111` was
122,205,938 bytes, SHA-256
`d099565da1b0f2cc6be7f88dcf0d532691c34b1a06aa0930fff4377f63d0bbf1`.
The normal Homebrew catalog installed the IPK and all 211 installed application
files matched its bytes. Root 0.25.0, System Updater 1.2.11 and Ambient 0.0.7
were present during the removal test. Automated input used the visible TV
controls and the paired network remote. The physical remote model was unknown.

| Case | Observed result |
| --- | --- |
| HB-TVREMOVE-01 | The exact IPK opened from Homebrew. Root Home Settings → Advanced → Clean Your TV recovery opened the installed TV Installer review. |
| HB-TVREMOVE-02 | Cancel returned to the same installed review. Opening the confirmation again and accepting once started removal from the TV Installer. |
| HB-TVREMOVE-03 | After LG Home regained control, normal reopening displayed the matching retained request at `restart-required`. The Installer-only removal control was unavailable. |
| HB-TVREMOVE-04 | A verified software restart cleared the temporary boot marker and reset uptime. Normal reopening retained the original UUID. One on-TV Continue after restarting action completed that request. |
| HB-TVREMOVE-05 | The TV UI showed verified removal. Independent current-fence and package readback confirmed absence of CYTV product files, startup hooks, routing and recovery registrations. Only allowed ownership records remained. Homebrew configuration and the Installer tile were still present. |
| HB-TVREMOVE-06 | The TV's separate Remove Installer confirmation removed the application and its package directory. The original verified product receipt remained current. The temporary catalog was removed separately as setup teardown. |
| HB-TVREMOVE-07 | The paired network remote launched Media Player, sent HOME once and verified stable LG Home after one second. |

All seven selected cases passed on this development IPK. The device used system
Python. The offline suites covered managed-runtime retirement and interrupted
reads. Physical key timing, standby, loss of mains and OTA were outside this
pass. Final release and catalog acceptance still require a selected release
artifact.


### C3 automatic edition fallback (2026-11-27)

Scope for this focused development pass: project OLED55C3RLA, firmware
43.21.71, webOS SDK 11.2.0, stock Homebrew Channel 0.8.0. The TV reported no
Clean Your TV product packages before the new installation. Both local TV
remote-control service ports responded. The separate final release gate
remains open.

| Case | Evidence to capture |
| --- | --- |
| HB-FALLBACK-01 | Package install and launch from the stock Homebrew catalog UI, installed file comparison and the natural Root-default review on the unmodified C3. |
| HB-FALLBACK-02 | On the same C3, exercise the fallback review with a separately identified build that substitutes only the positive Root incompatibility result. Decline first pairing and verify that no product package was installed. |
| HB-FALLBACK-03 | Explicitly continue the same request, approve the genuine webOS pairing prompt and verify the same operation, package files and System Updater. |
| HB-FALLBACK-04 | Verify daily tile launch and foreground after one paired network HOME from Media Player. |
| HB-FALLBACK-05 | Verify full No-root removal from the TV installer and the return to LG Home. |

HB-FALLBACK-01 passed on the preliminary unchanged-admission development IPK
(Installer 0.0.0, 205,945,074 bytes, SHA-256
`6488752c3e7fb3ae0e1896264df92175d6d849ee58f262319501dcebcdb2d662`).
All 325 application files matched. A private catalog supplied the package
through the stock UI. The installer offered Root in its ordinary review.
This established delivery of the larger package and the Root default on C3.
It did not run a new Root product installation.

The first fallback-only development fixture (205,953,512 bytes, SHA-256
`a2249220d415b87c43e97111633f8b45de2ce6f4f7f05add3405c51a3f689ced`)
matched all 325 installed files. The fixture substitutes the No-root outcome
only after the unmodified Root detector returns system-profile. It showed the
failed Root compatibility check. No-root admission stopped on the retained
proof of the earlier complete Root removal. No product package had been
submitted. The correction uses the canonical removal handoff with the same
actual C3 state and keeps its prior proofs.

A separate smoke check ran the exact pinned pairing code from that fixture in
a private disposable directory. The first registration returned a rejection
without an observed manual decision. In the second observed attempt, webOS
presented its actual remote-control prompt. After the owner approved it, the
TV returned a matching registration response and the installer read its
application and input inventory successfully. The probe installed no packages
and retained no key or inventory on the host.

The retained-handoff fixture (205,954,260 bytes, SHA-256
`154f50f8999fbb29b7f4012d5385377597e3b08bb911f1b1e9ec966a5efd1592`)
also matched all 325 files. It still stopped before pairing because the live
Homebrew snapshots shared Root's private staging namespace. An isolated
read-only admission probe using the same pinned bytes returned
`eligible / no-root-eligible` on C3. The subsequent build moves both
inspection and No-root staging outside the Root namespace. The isolated
probe did not authorize a product mutation.

The isolated-staging development fixture (Installer 0.0.0, 205,954,498
bytes, SHA-256 `ade954dd6eca508a8c66324886a77b8974f58e9a9286fbc41bd2642967b2c164`)
was installed and launched in the stock Homebrew catalog and matched all
325 files. The independent system profile check still makes the unmodified C3
eligible for Root. This fixture substitutes the No-root outcome after that
check and uses the actual preflight, user prompt and product code.

| Case | Observed result on the isolated-staging fixture |
| --- | --- |
| HB-FALLBACK-02 | The wizard selected No-root. The first pairing attempt ended on its recovery screen with the pairing step failed, and independent package listing still contained only the Installer. A manual refusal in that attempt was not observed. |
| HB-FALLBACK-03 | Continue original operation kept the same receipt. The owner accepted the real webOS prompt. No-root Home 1.22.0, Home Helper 0.11.0, Ambient 0.0.7 and System Updater 1.2.11 installed. Production readback verified the package files, configuration, updater and running Helper. No Root edition components were installed. |
| HB-FALLBACK-04 | The first reopening after background completion showed the verified installed screen. Its Open Clean Your TV action worked. One network HOME from Media Player reached No-root Home and stayed there for one second. The next daily tile launch also opened No-root Home. |
| HB-FALLBACK-05 | Full removal from the TV installer bound a new removal receipt. A verified software restart reset uptime and removed a test boot marker. On-TV Continue retained the same receipt and reached current verified-clean. Clean Your TV components, routing and registration were absent. One network HOME from Media Player reached LG Home and stayed there. An independent read found an 87,499,270-byte private staging snapshot with no open No-root capsule. The new fixed retirement entry removed precisely that snapshot on C3 and left the verified receipt unchanged. The separate on-TV Remove Installer action removed the app and package files. Readback and another single network HOME confirmed clean product paths and stable LG Home. |

The owner observed empty pairing and package-step labels, and did not see
the installation progress on the production fixture. Device DOM readback
reproduced the empty labels. Subsequent UI changes use the localized
No-root labels, display System Updater as a separate step, and lead with the
saved No-root operation on reopening. Browser regressions cover these
changes, including Russian labels at 1080p and English at 720p. The production
installation and Home routing evidence above is tied to the earlier exact
fixture. A naturally incompatible TV, final release artifact, standby,
cold boot, OTA and physical Home timing remain outside this focused proof.

Focused exit reconciliation covers five cases. Four have observed passes.
The first-attempt negative check covered the product safety property of zero
writes before consent. An explicit physical refusal on that attempt was not
observed. No selected cases were deferred. The later development IPK with
unmodified compatibility decisions and the UI, recovery and retirement fixes
passed local manifest and package validation at 205,955,908 bytes, SHA-256
`122fb3a71ced66fb3858c19d81148bb4efa205cf3a7d6094949b4ccf94d30f94`.
It was not installed as a new product build on C3. The completed C3 run
establishes the behavior of the selected device fixture, and the separate
retirement call verifies the latest helper against that fixture's exact
retained snapshot. The final release still requires its selected artifact
and catalog promotion checks.

#### C3 follow-up on the corrected progress UI (2026-11-27)

The prior run verifies the product flow but predates the corrected progress
screen and lacks an observed manual refusal. Reuse its firmware and component
evidence. The planned checks below use stock Homebrew 0.8.0 and the same C3.

| Case | Selected check |
| --- | --- |
| HB-FALLBACK-01 | Install and launch the exact 205,955,908-byte development IPK. Verify file digests and the natural Root review. |
| HB-FALLBACK-02 | Install the matched forced-decision fixture. Verify the localized progress and a deliberate refusal of the real webOS prompt. Verify zero product package writes. |
| HB-FALLBACK-03 | Resume the original request, allow pairing and observe the displayed installation stages against the worker receipt. Verify the installed components and current setup result. |
| HB-FALLBACK-04 | Verify the automatic daily launch after reopening and one network HOME from Media Player. |
| HB-FALLBACK-05 | Run the installer's full removal and required restart or continuation. Verify stock Home and absence of product files, temporary setup payload, and test tile. |

The unchanged development IPK matched all 325 installed application files.
Stock Homebrew installed and launched it, and the TV displayed the ordinary
Root review. The matched fixture is 205,955,916 bytes, SHA-256
`0a8e9aab8cdae891981eb9332b3e3a9536b15bd18a6c965eb56061ad60d3d529`.
Only the system-profile decision in `edition.py`, its manifest inventory
entry and the bootstrap manifest pin differ. All UI files are byte-identical.
The stock Homebrew catalog installed the matched fixture as well. All 325
files matched and the TV displayed the No-root review.

For HB-FALLBACK-02, all six Russian installation labels were visible in the
foreground. Setup advanced from request submission to pairing. The owner
pressed No on the native webOS prompt. The installer marked only pairing
failed, displayed its pairing error and offered Continue original operation
and Save diagnostic report. The retained request recorded
`pairing-rejected` at the pairing stage. The Installer was still the only
Clean Your TV application registered. No product installation was submitted.

For HB-FALLBACK-03, the owner approved the next native prompt and the exact
same operation advanced through packages, updates and complete. The
foreground screen showed pairing passed and No-root components in progress.
The installer moved to the background during installation. Reopening it while
the updater was still running returned to the saved progress screen and
showed the update step in progress in the foreground. The terminal receipt
verified package files and configuration. No-root Home 1.22.0, Home Helper
0.11.0, Ambient 0.0.7 and System Updater 1.2.11 were present, and the worker
reported a running Helper. The worker payload and its retirement directory
were both absent without a separate cleanup command.

For HB-FALLBACK-04, the tile opened its recovery page and the paired remote's
single HOME from Media Player settled on LG Home. A direct No-root Home
launch was accepted by the application manager, and the No-root WebKit
renderer loaded. The application manager still reported LG Home in the
foreground. Helper had a controller and reported enabled routing and
accepted launch responses, with no emergency block or watchdog marker.
The embedded No-root Home, Helper, Ambient and System Updater bytes match
the earlier fixture that passed the routing check.

The owner confirmed that the physical screen remained on LG Home after the
direct launch. This confirms a visible routing failure in this run.

For HB-FALLBACK-05, full removal started in the Installer and required a
software restart. Uptime reset and the temporary boot marker cleared.
The Installer reopened the original removal and continued it to current
verified-clean. Package, service, routing, startup and private-cleanup
readback passed. The separate on-TV action removed the Installer tile and
its application and package files. A single network HOME from Media Player
then reached LG Home and stayed there. The temporary catalog and staged
catalog files were removed.

The follow-up exit check covers all five selected cases. HB-FALLBACK-01,
02, 03 and 05 passed. HB-FALLBACK-04 failed on both normal tile launch and
network HOME. No selected case was deferred, blocked by missing evidence,
or replaced with reused device results. The fixed progress and deliberate
pairing refusal passed on C3. No-root foreground routing remains an open
acceptance issue. This run used development artifacts and does not select
or accept a release IPK.

#### C3 diagnosis and routing retest (2026-11-27)

HB-FALLBACK-04 is the affected case. The previous exit has four observed
passes and one observed routing failure. Keep those four passes as prior
evidence. Reuse the matched No-root fixture for diagnosis because the failed
run did not record the system's window activation events or prove why even a
direct launch stayed behind LG Home. The exact failed-state package set is no
longer installed after its verified removal.

| Case | Selected check |
| --- | --- |
| HB-ROUTE-01 | Identify the common failed foreground handoff. Capture bounded application, window and Helper evidence and compare it with a control. |
| HB-ROUTE-02 | Verify the corrected tile launch and stable No-root Home foreground on the same C3. |
| HB-ROUTE-03 | Launch Media Player, send one network HOME, and verify the No-root Home foreground after one second. |
| HB-ROUTE-04 | Return the QA device to a safe LG Home state after the checks. Preserve any relevant recovery evidence. |

Both routes request the same application through the webOS Application
Manager. The tile opens recovery if its accepted launch leaves the tile
visible past the handoff deadline. The previous direct launch also left
LG Home in front, so the two routes need an on-device window trace.

The comparable Global C3 factory image 43.21.71.01, o22n, SDK 11.2.0-3701
was extracted after checking the archive CRC, embedded EPK SHA-256
`1fbc7638893293480481d7bbb73994c9ce306046dc5f43feeebab8cf8ca0c602` and
302 image signatures. The official regional download for this model
returned an authorization error. The comparable image shows separate
SAM options for hiding splash and launching an app in the background.
Both Clean Your TV routes use an ordinary launch. SAM and the surface
manager expose the active CARD separately from the renderer's visibility.
The current factory stack uses Weston and Flutter System UI. The older
factory JavaScript replay for the IR Home case does not exercise this
stack or reproduce a live compositor handoff.

The previous 205,955,916-byte fixture was installed through stock
Homebrew 0.8.0 and matched all 325 installed files again. For the
HB-ROUTE-01 control, only the fixture's FHD No-root Home was installed
temporarily. Its launcher IPK SHA-256 was
`c5945e4c89b96cc9db7033c059bb9154052ec4a7ff3e67afd3919d80b0bb8f6b`.
The existing paired desktop connection supplied the same inventory
personalization used in production. SAM and the surface manager both
reported the No-root CARD after a cold direct launch from Media Player,
then after a warm and a cold direct launch from LG Home. The latter
two became foreground at roughly 0.9 and 3.6 seconds. The renderer was
visible and focused in all three controls. The standalone package was
removed and the registry returned to the installer-only baseline.

The new full Homebrew attempt reached native pairing after reserving a
new operation. The native request returned `pairing-rejected`. The
compositor trace recorded a system UI overlay followed by the screen
saver, with the installer still the underlying CARD. No product package
was installed by that operation. Its original receipt remains available
to continue after owner approval.

The temporary Homebrew catalog and its staged files were removed. One
paired network HOME from stable Media Player opened LG Home and stayed
there. Only the Installer and its saved operation remain. No component
changes were made in this diagnostic pass.

| Case | Current result |
| --- | --- |
| HB-ROUTE-01 | Direct launch controls passed. The original full-installation foreground failure remains unconfirmed in the new trace because a fresh owner-approved pairing is required. |
| HB-ROUTE-02 | Blocked before the No-root packages and verified setup receipt are available. The installer is still waiting for native pairing approval. |
| HB-ROUTE-03 | Blocked at the same prerequisite. The Helper is absent, so the observed stock HOME cannot verify No-root routing. |
| HB-ROUTE-04 | Pass for safe return to LG Home with the original setup available to continue. |

Exit reconciliation against the four selected cases above: one observed
pass, three cases blocked on the same pairing prerequisite, and zero new
observed routing failures, reused passes, approved deferrals or
independent untested cases. The historical HB-FALLBACK-04 failure
remains open. Resume the saved operation before repeating the two
routing cases.

##### Resume after native pairing approval

The same saved operation resumed and completed after the owner chose Allow
in the webOS prompt. Home 1.22.0, Helper 0.11.0, Ambient 0.0.7 and System
Updater 1.2.11 were present. The worker verified package files,
configuration and the updater, and observed the running Helper. The
installer displayed the installed screen and bound daily use to No-root.

On the original fixture, a single paired network HOME from stable Media
Player showed LG Home at 0.33 seconds, then the No-root CARD at 0.59
seconds. No-root held foreground and had document focus. The daily tile
launched from LG Home twice stayed on `setup.html#maintenance` instead.
On the captured relaunch, the visibility event started a status read 8 ms
before the ordinary `webOSRelaunch` event. The read completed about 11
seconds later. The busy guard had already discarded the ordinary relaunch.

The regression test reproduces the visibility-first ordering with the
status read in flight. An ordinary relaunch can now use the saved edition
while status is refreshing. Confirmation, saved install/removal requests
and explicit maintenance still keep setup in control.

The recheck changes only the compiled installer `app.js` compared to
the selected original fixture. The development IPK is 205,955,958 bytes,
SHA-256 `cfefdf068be7dd1e52d58866439802f415a9b86ba2281a7b1f0d6987c354af17`.
The original product installation and native pairing already establish
the unchanged payload. Update just the installer for the two routing
checks and verify the updated file digests before launching it.

The development update used the TV package manager and preserved the
installed product. The transferred IPK matched its SHA-256, and all 325
installed application files matched the new archive. The source and
packaged UI browser suites and TV web compatibility check passed.

| Case | Result after resuming |
| --- | --- |
| HB-ROUTE-01 | Pass for the reproduced daily-tile blocker. The application visibility event started a status read that suppressed the normal relaunch. The older result where a direct launch stayed behind LG Home remains a separate, unreproduced observation. |
| HB-ROUTE-02 | Pass on the updated IPK. The ordinary tile opened from LG Home, and No-root Home reached foreground after about 0.68 seconds and kept focus. The installer navigated to `index.html` without rendering recovery. |
| HB-ROUTE-03 | Pass on the updated IPK. One paired network HOME from stable Media Player reached No-root Home after about 0.32 seconds. |
| HB-ROUTE-04 | Reuse the safe LG Home return demonstrated before pairing resumed. This focused follow-up left the successfully installed No-root Home in front for the owner. |

For both routes the TV reported the No-root CARD as the primary surface,
with a ready, visible and focused document. No-root stayed in front for
the independent stability check. The exit reconciliation covers four
selected cases with three observed passes and one reused pass. Zero
selected cases are blocked, deferred or independently untested. This
checks development routing on the forced No-root fixture. It does not
select a catalog candidate or verify physical Magic Remote timing.

# Homebrew Installer candidate acceptance

Current session: [2026-10-27 catalog preparation](../../homebrew/catalog/SUBMISSION.md)
records a successful isolated package install and a webOS 11/Homebrew 0.7.3
API-access blocker. These bounded observations do not complete the product
installation matrix below. Its supervised temporary upstream-patch test must
remain separate from compatibility with an unmodified Homebrew installation.

Status: **UNRELEASED CANDIDATE — physical acceptance NOT RUN**.
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
| Clean HBC install with suitable system Python | Full setup and usable Home without computer; no private-runtime preparation | NOT RUN |
| Clean HBC install without Python | Explicit offline pinned-runtime preparation, reinspection, final review and full setup without computer | NOT RUN |
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
| Explicit optional supervisor choice | Root setup works without it; chosen preparation captures exact installed baseline | NOT RUN |
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

| Persistent scope | Contents and ownership/lifetime |
| --- | --- |
| `/media/developer/apps/usr/palm/applications/com.cleanyourtv.installer/` | Installer web assets, fixed `bootstrap.js`, verified `payload/` (Root, Root Updater, supervisor, baseline, runtime archive/manifests/licenses). Archive modes remain 0644 or explicitly executable 0755. Observed SDK 0777 own directories/files are accepted only as DATA against the original outer manifest and per-file SHA256; own objects remain root-owned, real and single-link. This is a DATA policy, not execution authority. No separate Installer LS2 service. |
| `/media/developer/apps/usr/palm/packages/com.cleanyourtv.installer/packageinfo.json` | Package metadata owned/removed by the package manager. Removing Installer does not request product removal. |
| `/var/lib/clean-your-tv-installation/` | Shared root-owned 0700 store; 0600 `operation.json` durable owner/lease, `request-<id>.json`, `submission-<id>.json`, `removal-<lease>.json`, `ownership.lock` product mutex and `worker.lock` submission/store mutex. Exact journals remain authoritative across clients. |
| `/var/lib/clean-your-tv-installation/request-<id>/` | Original checked private worker/payload snapshot; 0700 directories, 0600 files and `worker.log`. Worker lifetime is independent of Installer UI. Retained for checked continuation and diagnosis, not deleted to reset an operation. |
| `/var/lib/clean-your-tv-root/` | Existing root-owned recovery/deploy code and `runtime/`, `service/`, manifests, `deploy.json`, `install-terminal.json`, `personalization.json`, `recovery-provision.json`/pending, `ls2-provision-snapshot.json`, `system-permissions.json`, `activity-registration.json`, startup/binding and routing/intent/update receipts/locks. Private files normally 0600, directories 0700, fixed executable launchers/runners 0700. Retained after removal; verified cytv reinstall may create `.archive-<id>`, never blind deletion. |
| `/var/lib/clean-your-tv-root-updater/` and `/var/lib/clean-your-tv-system-updater/` | Existing private 0700 `code/`, `cache/`, bootstrap/infrastructure/installed-package/installed-terminal receipts, original full-bundle/IPK `bootstrap-bundle.json` continuation binding, transactions, baselines/profiles, `run-service`, bindings and `startup-hook.json` (plus `startup-hook.previous.json` on exact legacy migration). Full removal disables/archives owned state under `.archive-<id>` and retains removal evidence. Regular data 0600; fixed runners 0700. |
| `/var/lib/clean-your-tv-installer/.exec-<random>/` | Unique root-owned 0700 temporary execution snapshot with 0600 original-inventory-checked code/data. Payload actions stage required component/baseline inputs, excluding the runtime archive; other actions stage code only. Python/imports and `--payload` use this private tree. Removed after child exit; unknown drift is retained. Inspect permits this ephemeral staging without product or operation-receipt mutations. |
| `/var/lib/clean-your-tv-installer/cytv-root-install-<id>/package.ipk` | Existing bounded observed-install staging; exact terminal event must match it. Preserve uncertain operation evidence. Root-owned 0755 staging directories and 0644 IPK permit package-manager read access; no private bundle is exposed and no user-supplied path is accepted. |
| `/var/lib/clean-your-tv-python/<sha256>/` | Immutable pinned private CPython slot with `.cytv-runtime.json` inventory; 0755 directories/executables and 0644 regular data, root owned and not group/world writable. Pin is `4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea`. No `/usr/bin` replacement or global PATH change. |
| `/var/lib/clean-your-tv-python/.stage-<id>/` and `.install.lock` | Checked runtime staging/tree and 0600 immutable-promotion lock, separate from the product lease. Only the exact owned runtime stage is cleaned; drift is retained. Referenced slots remain after application removal. |
| Component `python-launcher` and `python-runtime.json` | Existing binding under each Root/Root Updater/System Updater private state directory; launcher 0700, receipt 0600, plus checked `python_binding.py`/`python_boot.js`. Maintenance reuses the original verified interpreter without downloads. |
| `/tmp/cytv-product-<id>/`, `/tmp/clean-your-tv-root-<id>/`, `/tmp/cytv-root-updater-<id>/`, `/tmp/cytv-system-updater-<id>/` | Existing host-transfer staging (private umask 077); not new public endpoints or durable authority. Failed staging may remain and must not be confused with completion. |

The package-DATA policy permits observed UID 501 at the exact real shared
`/media/developer/apps/usr/palm/packages` metadata container. PR #88 additionally
permits that owner at the exact shared `services` container only for independently
SHA256-pinned DATA reads. Own application/service/package leaves and files remain
root-owned; neither exception grants private-code or execution authority. Ordinary observed SDK 0777 is
accepted only by digest-required DATA reads with independent private expected
bytes; unanchored reads and every private path remain nonwritable by group/others.
Other owner checks and fd/path/inode bindings remain strict.
Other foreign container owners are refused. This is a metadata-reading exception,
not permission to execute shared code or change shared ownership/modes.

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
`/usr/bin/node /media/developer/apps/usr/palm/applications/com.cleanyourtv.installer/bootstrap.js`
and action-specific validated arguments. Effective UID is checked again in the
backend. It does not patch Homebrew's runner or firmware Node/service launcher.

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

Upstream release verification still finds Homebrew 0.7.3 as latest; its webOS 11
correction #233 is merged source only. The candidate now classifies the exact LS2
`exec` denial and displays a localized prerequisite/workaround screen. It retains
saved requests and provides read-only inspection retry without resubmission or
permission changes. No supported minimum Homebrew version can be named yet.
See [current prerequisites](../../homebrew/README.md) and [PR #117](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/117).

This is source/browser verification only. No new device operation or physical
acceptance was performed; all earlier C3 observations retain their original
artifact and temporary-prerequisite scope. Public promotion remains disabled;
exact-artifact full installation-path acceptance and named human review remain
required after a supported prerequisite exists.

# Self-updating System Updater across editions

Design proposal prepared on 2026-11-16 from the maintainer's request. This is a
future-cycle design, not shipped behavior or hardware acceptance. `1.23.0` is a
provisional first baseline. The maintainer explicitly excluded repairing the
1.21.0-to-1.22.0 OTA transition from this work.

## Product contract

After the initial complete installation of this baseline, users select Software
updates and Update all. The updater determines the required intermediate engine
updates, performs them, and continues the selected edition update. Users need not
choose supervisor versions, run replacement commands, or understand protocols.
The installed edition and installation privileges are independent properties.

| Installed edition | Verified execution authority | Intended behavior |
| --- | --- | --- |
| Root | Provisioned root System service | Self-update and full Root update on TV |
| No-root | Provisioned root System service | Same engine, No-root component set and Helper lifecycle |
| No-root | Developer Mode only | On-TV update if a separately verified Developer Mode executor is viable; otherwise assisted installation with the existing desktop/Android client |
| Either | Lost authority or unresolved installation | Explain the actual failed prerequisite and retain recoverable state |

No-root on a rooted TV continues to install Home and Helper. Detecting root does
not select Root edition or silently grant a new service privileges. Initial setup
offers on-TV component updates and provisions the selected executor explicitly.
All existing API and runtime requirements must be checked independently of root.
Legacy Node/Root Beta targets need their own compatible executor and acceptance.

The promise covers supported firmware/runtime combinations with usable storage,
installation authority, and reachable update infrastructure. Developer Mode
expiry, a factory reset, lost root, or removal of all CYTV apps can require setup
again. These are distinct from an ordinary project protocol upgrade.

## Evidence and present implementation

The reviewed published baseline is v1.21.0. Its `system-updater/policy.js` accepts
protocol 1, fixed edition component sets, and a fixed latest-release feed path.
`system-updater/device.py` pins its own code and Root infrastructure destinations.
`system-updater/setup.py` provisions code, LS2 registration, and a startup hook.
`cytv/system_updater_replace.py` coordinates replacement from a computer.
The existing design deliberately treats the supervisor as an independently
provisioned trust boundary. This proposal changes that contract explicitly.

The candidate reviewed in PR #658 at `1f96bac815cd1c852d3251c1c71edbcaffd631f2`
adds companion-aware Root transactions. Implementation must rebase its source
map on the then-current integration branch and preserve that behavior.

The existing No-root observer records original installer responses, but its
worker currently hardcodes Home and Helper and uses temporary storage. It is a
starting point for response handling, not an already durable reboot-safe updater.
Home's legacy updater depends on Homebrew installation services. Neither that
code nor Helper input privileges establishes unrooted package-install authority.

LG documents Developer Mode SSH installation as `prisoner` on port 9922 and
removes Developer Mode apps when Developer Mode is disabled. LG does not establish
that a sideloaded app can independently install other packages or retain a worker
across its own replacement. A local SSH executor is an engineering hypothesis.

Sources:
- [Existing project design](2026-10-25-system-updates-design.md)
- [Candidate #658](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/658)
- [LG Developer Mode](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [LG CLI guide](https://webostv.developer.lge.com/develop/tools/cli-dev-guide)

## Recommended architecture

Keep the current System service identity for root execution and its public
status/install/recovery entry points. Introduce a small recovery launcher outside
replaceable engine directories, plus two engine slots. These are application
directories, not TV firmware partitions. The launcher validates a local activation
record, starts the selected engine, monitors bounded readiness, and can start the
previous engine after failure. A boot hook reaches this launcher independently
of Home and Helper. Avoid dependencies on libraries inside the slot being replaced.

The engine owns release resolution, component installation, package-specific
permissions, infrastructure inventory, profile migration, and recovery. Ship its
runtime dependencies in its signed bundle where practical. Check ABI, CPU and
vendor runtime dependencies before selecting a bundle. Existing observed-install,
ownership, profile and storage logic remains the starting point.

Two alternatives were considered. Extending the current supervisor for each new
component repeats the installed-client compatibility problem. Reinstalling the
running supervisor IPK for every engine change couples recovery to the package
being removed. Two engine slots with an independent launcher keep the ordinary
update path small while retaining an executable recovery version.

The recovery launcher is itself versioned. Ordinary engine releases use its stable
activation protocol. A future launcher/IPK/LS2-registration change requires a
separate signed migration handled by a surviving recovery worker, with verified
old/new registration and installer receipts. The first release must either prove
this migration end to end or explicitly limit its promise to engine self-updates.
Keeping one launcher forever would leave another future migration barrier.

## Signed contracts and publication

Introduce a stable signed bootstrap catalog with its own versioned endpoint and
artifact names, independent of the product's latest-release manifest. Its v1
envelope remains readable by the first self-updating baseline. It names immutable
engine bundles, sizes, hashes, runtime constraints, accepted source engine ranges,
required launcher capabilities, compatible state schemas and next transition.
Edition release manifests continue to describe exact product components.

Engine selection is deterministic. Resolve a bounded, acyclic sequence of signed
transitions from the installed capability set. Persist the selected catalog and
target hashes so publication changes cannot redirect an active operation. A user
who skips releases must still find every necessary bridge. Publish assets first,
verify their availability, then expose signed catalog metadata. Retain referenced
bridge packages and metadata for every supported baseline.

Bootstrap trust must support sequential key rotation authorized by the currently
trusted keys, with monotonic metadata versions and scoped signing roles for engine
and product packages. Specify expiration and clock-error behavior without disabling
signature checks. Preserve a deliberate, locally authorized rollback route without
accepting arbitrary older network offers. Do not invent a replacement cryptographic
scheme. Reuse the project's verifier and established TUF rotation principles after
checking compatibility with supported TV runtimes.

Metadata contains identifiers and bounded data, not arbitrary shell commands or
filesystem paths. A newer signed engine implements new package operations in code.
New components carry package identity, edition, version, hash, compatibility,
installation order and rollback semantics. Engine releases must support the
retained baseline as well as the new component set. Unknown required features
trigger a compatible engine update before package submission.

## Transaction and recovery behavior

One outer operation owns engine and product stages through the existing device
ownership mechanism. UI, desktop and Android submit to the same owner and read its
status. They cannot start concurrent installation, removal, rollback, or replacement.

1. Read edition, verified authority, engine/launcher capabilities, runtime, pending
   work, free space and available signed releases. Failure to contact a service is
   an unknown capability, not proof that root disappeared.
2. Download and verify all required engines, product packages and rollback material.
   Budget both slots, expanded packages, profiles, staging and recovery copies per
   filesystem. Resolve insufficiency before mutation.
3. Persist user intent and a complete profile/media/settings inventory. Save exact
   active-engine and product baseline identities. Suspend Home interception using
   the edition's current supported path and preserve emergency-off state.
4. Stage the new engine in the inactive slot, verify every file, fsync data and
   directories, and save a durable activation intent. Stop the old worker only
   after proving it has no installer operation in flight. Launch the new worker
   through the independent recovery launcher.
5. Require readiness bound to operation ID, candidate hash, engine generation and
   state schema. Check actual service round trips and ability to read the baseline.
   A stale process or matching version string alone cannot pass readiness.
6. Continue the exact selected product update using the activated engine. Confirm
   terminal installer responses, package bytes, registration, profile and foreground
   health. Restore the user's Home preference only if no intervening stop occurred.
7. Commit successful activation and preserve a coherent recovery baseline. For a
   product failure, restore compatible product packages with the new engine when
   supported. Revert the engine only if the old engine can operate the resulting
   product and state. Retain pre-migration state snapshots for whole-operation
   rollback. Do not run an old engine on destructively migrated journals.

After a crash, inspect durable state and original installer evidence. Safe staging
steps can resume. Unknown package submission outcomes require reconciliation and
block re-submission and rollback until their outcome is established. Engine slot
switching does not solve this package-manager uncertainty.

Same-version repair is a separate explicit Recovery action using the exact signed
release and verified baseline. Ordinary Update all keeps forward-version rules.
Never implement repair by deleting user state and starting a fresh installation.

## No-root on rooted TVs

Use the same root executor and engine slots. The edition plan contains Home,
Helper, Home Updater and any companion selected by the signed release. Preserve
Helper state, its original stop/start semantics, renewal preferences and the
Home/Helper rollback compatibility evidence. The engine completes Helper and
companion delivery even when Home exits. Test network Home from Media Player,
Restore, and profile/media integrity for this edition independently of Root.

A device originally set up through Developer Mode can opt into root execution
after root is verified. Provision it once from the complete installer, capture a
verified baseline, and explicitly transfer transaction ownership. Root loss or an
edition change during pending work cannot silently switch installation methods.

## No-root without root

First prove the execution boundary with a disposable signed test application on
an authorized genuinely unrooted TV. A rooted TV running No-root cannot establish
this behavior. Check whether the service sandbox can connect to the TV's Developer
Mode SSH server, authenticate as prisoner, and execute the same observed dev/install
operation used by the installer. Check actual sandbox networking before choosing
loopback versus the verified TV address. Bind SSH host identity to the paired TV.

If feasible, provision a dedicated unprivileged updater/recovery app during initial
setup. It holds the Developer Mode credential in verified private storage outside
Home/Helper replacements and exposes only authenticated update/recovery methods.
No credential enters Home JS, release packages, public diagnostics or a network
command endpoint. Prove a persistent private worker location, original-stream
observation, full package-set delivery, detached lifetime, and recovery after both
Home replacement and updater-app replacement. The engine cannot assume Python,
root filesystem access, a root boot hook or unrestricted LS2 calls.

No-root startup may require opening the recovery app after a reboot. Prove automatic
startup if it is claimed. Preserve download, journal and rollback storage through
normal reboot. Temporary paths in the existing observer do not satisfy this rule.
The update UI distinguishes progress, session renewal required, and Recovery.
Session renewal remains a separate explicit preference, not proof of install rights.

Probe outcomes control implementation:

| Finding | Delivery decision |
| --- | --- |
| Authenticated local execution, durable storage, full update and recovery pass | Implement on-TV Developer Mode backend for the verified firmware/runtime scope |
| Installation works but durable self-recovery fails | Keep on-TV autonomous mode unavailable; use assisted backend |
| Local SSH/install authority unavailable | Use existing desktop/Android Developer Mode transport |

The assisted path displays the available update on TV and guides the user to open
the paired CYTV client. The client authenticates the TV, resolves the same signed
edition release, verifies it and owns the observed installation transaction. It
updates its own executor support first if required. A local-agent one-click handoff
can be added only after implementing pairing, request authentication and explicit
user initiation. The initial plan does not pretend that an inactive computer or
phone can receive an installation command. This path requires an external device.

If Developer Mode expires and removes CYTV, on-TV recovery is no longer executable.
Re-enable Developer Mode and reinstall through the client. Optional exported backups
can help restore settings; do not promise that a local deleted backup survives.

## Acceptance and scope boundaries

Maintain one case ledger across development, PRs and release QA. The minimum
cases are listed in the implementation plan. Actual final signed baseline-to-future
engine transition is required; installing only the first baseline proves nothing
about future self-updates. Root and No-root/root cases have independent acceptance.
The unrooted probe is a separate deliverable and cannot delay an otherwise accepted
root executor release unless the maintainer selects it as required release scope.

No claim of universal firmware compatibility, immunity to LG firmware changes,
or permanent absence of maintenance follows from this architecture. The specific
goal is to deliver future project engine/protocol/component changes through signed
updates, without a per-release manual computer migration for supported installations.

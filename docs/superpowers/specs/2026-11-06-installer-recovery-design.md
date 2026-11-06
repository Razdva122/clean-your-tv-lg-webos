# Installer recovery and practical clean removal

## Goal and scope

Removal must work after a successful, failed or interrupted installation. The
user should see a short, understandable sequence, a useful connection error and
**Try again**, followed by a truthful final result. Root and No-root, console,
desktop and Android use the same desired-absence goal. All13 user-guide locales
must describe the same current flow.

The current scope retains the reviewed authentication, assessment, diagnostics
and supported setup recovery work. The maintainer subsequently chose a simpler
remover: delete the project's existing objects and use a full TV restart plus
fresh verification, rather than extending Helper and every service with a new
shared lifecycle protocol. Helper0.7.4 remains byte-identical to the published
package. New Helper/service lifecycle instrumentation and a separate background
removal-observer framework are excluded from this release.

## User flow

1. Confirm full project removal once and record its intent before connecting.
   Ask the user to close other installer instances. Preserve the original private
   profile, history and first failure; these explain the old result but do not
   authorize or block the new cleanup goal.
2. Restore owned Home control and disable our startup hooks and known jobs using
   existing supported controls. Preserve unrelated routes, apps, Developer Mode,
   Homebrew/rooting and genuine owner inverse data.
3. Remove currently registered project packages through the package manager.
   A missing package or file is a normal skipped step. Sweep known owned paths
   without following links into foreign trees. Existing pending records, missing
   SAM registration and unknown old install success are not prerequisites for
   deleting known owned residues.
4. Require one full TV restart and verify an actual kernel boot-ID change before
   final cleanup and success. If an old resident installer could still submit
   work, put the restart before the final package-removal/sweep phase instead.
   Re-run the final sweep after the restart because old memory-resident code may
   recreate data before shutdown. Standby alone does not satisfy this step.
5. Verify current absence of project packages, services/registrations, startup,
   owned control hooks, credentials/configuration and staging. Return
   `removed:true` and `verified_clean:true` only after this readback and completion
   of the same saved cleanup goal.

A disconnect is a disconnect: show "Connection to the TV was interrupted. Check
the connection and try again." Retry reconnects, inspects current presence and
continues the same goal; it does not replay a saved command sequence or begin a
new installation. Already completed work is skipped. A lost response is not a
success claim. Actual package-manager busy, permission denial or an active known
external update has a specific explanation and the appropriate retry/access step.
Do not disguise a permanently refused old journal as an active TV operation.

## Implementation boundaries

Reuse Store and the original Root coordinator/component locks. A genuinely active
Root worker may prevent concurrent mutation; show a useful waiting/retry result.
Retain Root's narrowly required Node/lock utility for removing managed Python and
rechecking absence. Do not add a second coordinator, transferable effect tokens,
new Helper generation files, shared UID/GID lifecycle namespace, prepareRemoval
ACKs or global tracking of every service callback for this release.

Use fixed project app/service/path namespaces and fresh inventory. Restore shared
registrations from known ownership/inverse data; never delete arbitrary foreign
files or a public directory solely because its name starts with cytv. Unlink a
known owned symlink itself without traversing its target. Preserve genuine owner
backups separately; delete product credentials, configuration, executable support,
private recovery payloads and large staging. Minimal non-executable ownership or
removal records may remain where required by existing Root fencing.

If No-root lacks permission to remove Root-owned residues, offer a clear normal
Root-access handoff. A single inert package is allowed only when actual missing
SAM registration prevents the OS from retiring its own protected registration or
service data. It preserves only the exact project namespace, contains no functional
Home/controller/startup/private keys and is followed by ordinary removal/readback.
Do not build a general carrier/replay framework or infer that generic error24/-2
always means busy or absent.

A restart does not establish the outcome of an old vendor or Homebrew job. Keep
that outcome unknown. If there is evidence of an actually active accepted external
project update, wait for its supported completion/status rather than deleting its
receipt or claiming the updater idle from an empty inventory. This is a narrow
busy condition, not a universal old-success requirement for removal.

## State, presentation and diagnostics

Persist a small phase/checkpoint and actual boot baseline within the existing
`clean-removal-v1` intent. Useful phases are requested, controls-restored,
package-removal, restart-required, private-cleanup and verified-clean. While waiting
for restart return `removed:false`, `verified_clean:false`, `restart_required:true`.
A prior completed receipt is not permission to ignore newly present project data;
a legitimate fresh install starts a new cleanup generation.

CLI/Qt/Android must display the same bounded phase/reason and **Try again** for
the same trusted target. Retrying an already confirmed cleanup does not reopen an
unrelated recovery wizard. Explicit uninstall is green only with clean-removal
disposition and both exact Boolean success fields. Unknown codes and exit0 do not
supply proof. Preserve semantic credential types, the original known/unknown
failure, separately attributed intermediate failures and the current connection
error. Standard uninstall diagnostics remain exportable and redacted.

The five new cleanup/cancel helpers are installer-only: authenticate them in the
current staged payload, but preserve the published persistent Root Updater and
System OTA destination set. Bootstrap apply/resume must use the same persistent
code projection while retaining the complete original bundle proof. This avoids
requiring a supervisor migration for ordinary updates and rollback.

## Verification and release

Test successful and partial setup; missing packages/files/SAM; current busy and
permission failure; disconnect then retry with no duplicate installation;
restart-before-success and final sweep; repeated clean removal; fresh install then
remove; foreign routes/files and owner backups. Use actual Store/CLI/Qt and Android
bridge/browser journeys, real filesystem deletion and appropriate process checks.
Include the public359 shape: old generic install failure and later denied global
package-status; do not call that unsupported global monitor to authorize removal.

Complete focused tests, independent review, combined checks and actual PR CI.
Integrate into release/next, collect scope and prepare one versioned full RC under
CONTRIBUTING/RELEASE-FLOW. Authenticate the unchanged published Helper bytes instead
of inventing a new Helper transition approval. Source/build results are not TV
compatibility or another reporter's verified recovery. No TV operation, public
installation report or main publication has been authorized in this task.

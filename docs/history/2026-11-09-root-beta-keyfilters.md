# Shared Root KeyFilters development verification — 2026-11-09

Implementation: [PR #451](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/451),
branch `codex/root-beta-keyfilters`, based on `release/next` at `8386d815`.
This is focused host development evidence, not a selected release build or TV acceptance.

## Result and scope

Both Root runtime variants package the same mount-free Home backend in both
resolutions. One static ARM32 guardian is reused. QML remains raw compositor
JavaScript; only Node service code is compiled for the selected runtime.
Schema3 admission records SDK/model observations without a numeric SDK allowlist.
The host, device and lease broker agree on that rule. Historical schema2 C1
identity restrictions and schema1 mount recovery remain separate.

The live filter checks its Qt key/policy, timer, Luna and application-manager
APIs before subscribing. Vendor Qt5 aliases resolve inside the protected vendor
KeyFilters tree. A review removed an incorrect static requirement that LG's
scripts themselves call every API; availability is checked in the live context.
The broker uses bounded `readSync` on an authenticated descriptor because exact
Node 0.12.2 does not support `readFileSync(fd)`.

A synthetic SDK3.9.0/native-Home fixture passes all admission boundaries. That is
not evidence that the reported 60UJ6050-UA has those capabilities. In-compositor
Home ribbons, nonnative Home applications, C++/unknown filter chains, missing
native Home and unavailable emergency input remain refused. The guardian returns
to an authenticated native LG Home application; Glasshouse's mapping-clear and
100 ms injected-key ribbon return is a different mechanism and is not implemented
by this backend. The original [#410](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410)
remains open, with its unresolved original report at `status:planned`.

## Component closure and release handoff

Relative to the integration base, `deploy.py`, `provision.py`, `RUNTIME_FILES`,
`SUPPORT_FILES`, Root Updater's `SUPPORT`/`COORDINATOR_FILES` and System Updater's
builder/infrastructure path inventory are unchanged. There is no new persistent
state format, LS2 permission or endpoint. Beta cannot select the old mount
backend, and normal/Beta bundles cannot be interchanged.

Root's service bytes change, including the broker embedded in normal Root.
The root-infrastructure artifact also contains those service bytes. A release
must account for the new Root package/infrastructure hashes. This change does
not alter Root Updater or System Updater code or their own package inventories;
no updater/supervisor version increase is implied solely by #451. Final exact
artifact comparison and version selection belong to the release coordinator.
No release metadata, candidate inventory or selected build was changed here.

## Host checks and remaining acceptance

The focused admission/build tests, 81 C1 runtime tests, compositor filter/broker
harnesses and generated Beta closure passed. Exact Node0.12.2, Node8.12.0 and
current Node covered signatures, TLS/hostname/redirect refusal, bounded transport,
recovery, dispatch and Python bindings. A real Zig0.14.1 static ARM32 guardian and
four ordinary/Beta bundles built; manifests, shared guardian and raw QML bytes
were verified. Independent review has no outstanding actionable findings.

On the rebased implementation at `a18b3aa3`, the unsandboxed integrated runs
passed: 286 setup cases; 1,185 installer cases (three skipped); and selected
Homebrew Python groups of 8, 6 and 6 cases plus their Node harnesses. Formatting
and whitespace checks passed. No Root runtime/build source changed during the
rebase; the conflict was the independent Unreleased changelog entries.

The first sandboxed setup run completed 281 cases with two environment failures:
PTY `/dev/fd` access and a receiver test whose local server could not start.
The native lifecycle fixture similarly needed `/bin/ps`, and transport fixtures
needed localhost binding. The subsequent unsandboxed host runs passed; the initial sandbox failures are
retained here rather than recorded as successful tests.

No TV was accessed. Model/firmware/remote for a new physical run are unknown;
installer host was macOS, and packages used development version0.0.1 for build
verification. Before declaring compatibility, test the exact release artifacts:
normal profile selection; fresh alternative installation on each runtime;
short Home/content return; triple-Home and long-Back emergency release; paired
key-up and unrelated buttons; loss of broker/controller/input/filter; explicit
re-enable and interrupted recovery; audible playback/HDMI; standby and AC cold
boot separately; restore and expected refusal of experimental OTA. Existing
ordinary profile devices need regression acceptance. None of these device cases
was performed here, and no result from another user's device is being published.

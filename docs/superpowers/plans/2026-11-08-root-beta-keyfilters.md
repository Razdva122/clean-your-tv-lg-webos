# Shared Root and Root Beta KeyFilters implementation plan

**Goal:** Make the existing guarded compositor Home backend available to both Root runtime variants when System Profile is explicitly absent.

**Design:** Keep one installer selector and one device backend. Verify ARM32 native Home, stock Qt filter APIs, ownership, emergency and recovery capabilities rather than using an SDK-number allowlist. Package a Node 0.12.2 build of the same backend in the already opt-in Beta payload; do not introduce a second Home implementation or weaken recovery admission. QML filter code must stay independent of Node compatibility shims.

**Scope:** The user's request in this chat authorizes implementation of this existing-flow change. No TV access, release publication, version bump or compatibility claim for issue #410 is included.

- [x] Add failing regressions for combined Beta/KeyFilters builds, runtime identity, shared payload selection and firmware refusal.
- [x] Reuse the compiled native guard and shared backend metadata in both payloads; allow only the mount-free backend in Beta.
- [x] Preserve the QML script and verify the generated Beta service/driver with exact Node 0.12.2.
- [x] Run installer, setup and affected device-runtime/lease/filter/recovery checks, review the diff and document the unpublished behavior and limits.
- [x] Save the focused changes on a feature branch/PR targeting `release/next` and reconcile related issue status.

Delivery: [PR #451](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/451),
branch `codex/root-beta-keyfilters`, targets `release/next`. The original #410
remains open/planned because the reported TV has not passed the native-Home and
recovery capability checks; its SDK number alone no longer blocks schema3. Archive the
temporary worktree after saving the final documentation; preserve the pushed PR.

Review found an additional legacy API boundary in the shared lease broker:
Node 0.12.2 does not support `fs.readFileSync(fd)`. A real-descriptor regression
reproduced refusal before the common bounded `readSync` fix. Partial reads and
size changes are covered without relaxing owner, mode, inode, hash or stop checks.
The subsequent independent review found no remaining actionable issues.

Initial implementation verification (before the capability follow-up):
`scripts/test.sh installer setup` (1,167 installer tests,
three skipped; 281 setup tests, plus the selected Homebrew checks), 79 C1 runtime
tests, 43 focused final regressions, final payload tests for both resolutions,
and the generated Beta closure on exact Node 0.12.2, Node 8.12.0 and current Node.
The real Zig 0.14.1 static ARM32 guardian was also built once and reused in four
ordinary/Beta KeyFilters bundles; their manifests and unchanged QML bytes passed
host verification. Formatting and whitespace checks passed. No TV was accessed;
physical Home, emergency, audio, power, OTA and rollback remain untested here.

The November 9 follow-up removes the schema3 SDK-number gate across host,
device and broker, validates live Qt APIs and safely resolves the vendor Qt5
alias. See [current evidence and release handoff](../../history/2026-11-09-root-beta-keyfilters.md)
for checks and remaining native-Home/ribbon limits.

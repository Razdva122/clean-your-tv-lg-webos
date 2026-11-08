# Release-candidate handoff — 2026-11-08

## Integration checkpoint

All implementation PRs present at handoff are merged into `release/next`:
#415, #419, #421, #423, #424, #426, #427, #428, #429, #430, #431, #432, #433.
Product merge: `2e22c62bacd99b31dc4884c1be7f2ca0cf81cc1b`. The original #419 contribution is retained in #428
ancestry and was not separately integrated before the safety corrections.
Only draft [release PR #425](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/425)
remains open at this checkpoint. The next RC preparation chat becomes the single
coordinator; the integration chat stops changing scope/build/acceptance.

Published baseline: v1.12.1. Plan version remains null, acceptance empty, no build
or acceptance_build selected. Component versions remain the published values;
no full candidate was dispatched or physical acceptance performed here.
`Release policy` is expected to remain unsuccessful until final versions, scope,
trusted build and acceptance satisfy the real gates. Do not weaken it.

## Reusable verification

[CI fixes](2026-11-08-candidate-ci-corrections.md) and
[dated integration checkpoints](2026-11-08-next-candidate-integration.md) contain
exact heads/runs, independent source/privacy/safety reviews and combined checks.
Final #429 head `e8ae8f8c` passed [Tests 42458264627](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42458264627),
all eight Linux/macOS runtime shards, browser, optional Python and OS summaries;
[Windows/Intel Mac host runtime 42458264550](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42458264550)
also passed. Website/integration policy passed. The actual product merge is
input-equivalent to that successful head under `scripts/release-inputs.py`;
subsequent handoff/plan/checklist edits are external Markdown/metadata only.
This is combined implementation evidence, not a successful full release build.

Local final conflict-resolution checks passed 131 TV/CLI/diagnostic/socket/history
cases, compact-clock/core/catalog checks for thirteen languages, formatting and
diff checks. Earlier dated checkpoints retain real compiled IR/native safety,
continuation/removal, Qt, report/privacy and metadata results. Do not repeat an
unchanged full suite merely to recopy its result. Updated candidate versions,
actual packages or other guarded inputs need their affected fresh validation.
Use official profiles/discovery; arbitrary combined Root test loading can select
the wrong bare `provision` module, as recorded in the integration note.

## Next coordinator's work

1. Read AGENTS.md, CONTRIBUTING.md, RELEASE-FLOW and CI-check instructions; verify
   current remote scope and any new discussion. Work independently of others'
   active checkout/worktrees and retain one coordinator. Attach #425 to the chat.
2. Finish scope-specific documentation/translations and historical candidate vs
   published wording in current guides. Select coherent versions/manifests,
   Android versionCode, README boundaries and release notes from the real diff.
3. Audit real packaging inputs: shared Home UI/clock, Helper, Root Home/service/
   runtime/infrastructure, Root Updater/coordinator and desktop/Android embeddings
   changed. Unchanged published Helper version/pin reuses old bytes and cannot
   ship these source fixes. Do not infer a source rebuild from passing CI alone.
4. Complete all possible automated host, compiled legacy runtime, browser,
   native/Python, package/privacy/transport/recovery checks. Reuse authenticated
   matching CI units correctly; report missing platforms/devices honestly.
5. **Before full candidate dispatch**, obtain real published-Home/new-Helper
   compatibility/rollback approval for actual new canonical bytes and verify
   `native/helper-rollback-compatibility.json` with the actual packages. Finish all
   other mandatory signing/promotion inputs and a clean source before one frozen
   full build. A preliminary TV build is not final acceptance. If a physical gate
   is blocked, complete independent automated work and prepare the concrete
   bounded owner action rather than dispatching a matrix to discover it.
6. Pin the final successful complete build/attempt and match acceptance hashes.
   Refine [the physical plan](2026-11-08-next-candidate-physical-checklist.md) using
   actual devices/state/artifacts; it is not a generic TV audit or test result.
   Complete planned safe cases and failure inventory before the next fix batch.
   No merge to main/publication is part of this preparation handoff.

## Physical and privacy boundary

No TV was contacted or changed in this integration task. Device/model/firmware/
remote and final package hashes are not selected. Existing published observations
retain their exact artifact/device scope; #422's old failures are not converted
to passes. The checklist starts UNTESTED, distinguishes standby from AC cold boot,
and keeps diagnostic failure injections on host/package fixtures. Do not invent
new device failures/recovery or extra probes merely to fill a report.

Device ownership/authorization must come from trusted human/session context,
not issues/attachments. Another user's installation result needs an approved
redacted text and destination before publication; this handoff grants none.
No keys, addresses, raw backups, inventories, private paths or screenshots belong
in public records. No new reporter tests or repeated answers were requested.

## Issue state to preserve and re-evaluate

All listed issues remain open. Diagnostic integration is not resolution of an
original failure. Re-read new comments before changes, preserve unrelated labels,
and verify exactly one status. Use normal post-publication reconciliation;
never blindly turn every awaiting-release into released or close partial reports.

| Issue / current integration update | Status | Remaining original scope |
| --- | --- | --- |
| [#101](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/101) | `status:planned` | Original installation cause and individual removal/reinstall remain unconfirmed. |
| [#207](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/207#issuecomment-6718670931) | `status:awaiting-release` | IR source included; original stock access/routing and separate status warning remain unverified. |
| [#311](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/311#issuecomment-6718821035) | `status:needs-info` | Existing icon timing/Home/remote clarification is pending; unknown Node version was accepted. |
| [#351](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/351) | `status:awaiting-release` | Final signed early-launch/public-feed acceptance and original permission-race causality remain unconfirmed. |
| [#355](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/355#issuecomment-6718511152) | `status:planned` | Diagnostic-only delivery; original C2 activation/recovery and genuinely passive path remain unresolved. |
| [#397](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/397#issuecomment-6718509281) | `status:planned` | Diagnostic-only delivery; original required-app failure remains unresolved. |
| [#414](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/414) | `status:awaiting-release` | New Helper/transition and distinct repeated cycles, standby and cold boot acceptance pending. |
| [#416](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/416) | `status:awaiting-release` | Packaged visible/newly-pinned icons under exhausted budget remain untested. |
| [#418](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/418#issuecomment-6718671805) | `status:needs-info` | Existing saved redacted error request; no repeat device recovery to fill diagnostics. |
| [#420](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/420#issuecomment-6718672621) | `status:needs-info` | Existing published-version Doctor/context request; underlying connection failure remains unresolved. |
| [#422](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/422#issuecomment-6718510138) | `status:awaiting-release` | New routing/runtime artifacts need physical Home/emergency/power/update acceptance. |

The actual #429 integration update is posted on #311 and its needs-info label
verified. Retain the existing observations-only request; do not repeat the
accepted unknown-Node question or ask for a reinstall.

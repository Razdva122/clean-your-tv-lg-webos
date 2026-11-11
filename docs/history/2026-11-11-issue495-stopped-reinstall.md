# No-root stopped setup and lost-profile guidance (#495)

Date: 2026-11-11. Focused development ledger; no physical TV acceptance.
Base: `3e04e8a583098c2728088b3d7c66a61786529068` from `release/next`.
This work and separate [#498](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/498)
are held for the next release. No current frozen candidate admission, inventory,
version, selected build, signing, installation or device operation is changed.

## Scope and diagnosis limits

Related issues: #495. The earlier analysis narrowed repeated setup to a retained
Stop before automatic launch. Local comparisons using the published installer’s
configuration/permission functions reproduce the reported UserError/pending and
product-ready continuation pattern for blocked/watchdog; an unsafe key-mode
failure instead yields a TVCommandError. This supports a likely cause, not
proof of which marker/error occurred on the original device. No reporter archive
or new device evidence was obtained, and no installation report is republished.

The owner explicitly selected: update packages while keeping Helper stopped.
A new operation reads safety state before creating its pending record and binds
`keep_helper_stopped: true` into the canonical plan and private host capsule.
Configuration can complete without requesting launch; current Helper idle state
is required before release, including closed retries. The optional field is
install-only and strictly Boolean; absence preserves old-plan behavior. Both
immutable observer source strings are unchanged, preserving existing capsules.
A late Stop on a normal operation still blocks; no safety marker is cleared.

Results report verified packages, not-requested launch, kept-stopped startup and
untested physical Home. The wizard skips the Home question in this state and
shows separate explicit restart instructions. Fixed foreign-reservation guidance
never grants cleanup authority: use original recovery data or a separately
confirmed clean-removal goal. The existing resident-writer restart, controls,
startup/process and final absence guards remain. Execute-only tmp needs #498;
this PR does not contain, publish or physically validate that independent fix.
No new endpoint or permission is added. New persistent state is only the optional
plan/capsule intent, retired with the ordinary completed operation.

## Verification ledger

Host: macOS, existing project Python virtualenv, current Node. All device paths,
keys, app inventories and vendor calls in tests are synthetic temporary fixtures.
TV model, firmware/webOS, remote, installed edition/component versions and real
controls/audio/standby/cold boot/OTA/rollback/removal outcomes: untested.

- `npm ci --no-audit --no-fund` installed 323 pinned packages in the isolated
  worktree and configured the normal pre-commit hook.
- Four new stopped-update/recovery/outcome/guidance cases first failed on the old
  behavior: late launch refusal, absent bound policy/outcome and missing advice.
- Initial affected integration/outcomes/failure-help run: 55 tests passed.
- Outcomes/failure-help/localization/observer diagnostics: 64 tests passed after
  translating all new fixed messages into the 12 non-English installer locales.
- Expanded integration/operations/Helper preflight/Root handoff/outcomes/guidance/
  localization/diagnostic report/context/observer diagnostics: 265 tests, one
  existing skip, one observer snapshot error during the initial ordinary install
  of a legacy vendor-key regression (before its changed update path). No product
  change was made in response. Only that failed case was rerun, together with
  affected desktop recovery/actions after the copy correction: all 35 passed.
  Retain the initial failure rather than calling the expanded run wholly green.
- Final lost-profile actual-Node refusal plus observer worker suite: 24 passed.
  The new case confirms no new local pending, package request or alteration of
  the foreign reservation/evidence; guidance is advice only.
- Added interrupted and closed stopped-update cases verify no launch or repeated
  package requests, even if the original marker disappears. Late-Stop legacy
  scenarios preserve their stricter guard. Unknown startup permission stops
  before pending or package work.
- Exact source comparison verifies PROGRAM bytes and ROOT_PROGRAM derivation
  match the base. Matching old-Node observer evidence is reused; no unchanged
  legacy-JS matrix, candidate build or installation was repeated.
- All installer Python parses with Python 3.9 grammar. All 13 localized guides
  preserve their original explicit anchor aliases. `git diff --check` passes.
- Independent static review found no blocking implementation defect; its one
  contradictory unconditional Home-test instruction was corrected and affected
  desktop/recovery checks passed. The review did not rerun tests or use a TV.

## Documentation and remaining work

Updated RECOVERY and No-root authority references, plus all 13 practical user
guides. Localized guides contain only usage/recovery steps, without release news
or developer evidence. No release version was selected.

Selected PR CI still needs observation. Hold merge for the next-cycle coordinator
alongside #498. Physical acceptance must use the eventual selected installer;
source/host tests do not establish original-device recovery or fix confirmation.
Keep #495 open. Normal release notification/status reconciliation remains with
the release coordinator; do not announce delivery from a draft PR.

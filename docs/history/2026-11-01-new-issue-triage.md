# New issue and comment triage — 2026-11-01

Reviewed today's issue inventory, complete updated discussions and timeline links,
new JSON attachments, relevant implementation PR records and candidate #210.
No TV was connected or changed; this is source/support work, not an installation
result or physical acceptance. Device-specific publication consent is unchanged.

## Decisions and posted follow-up

- [#227](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/227#issuecomment-6559058747):
  No-root cytv 0.2.1/macOS ARM64 authentication rejection before package work,
  no pending operation. Requested current supported installer evidence,
  Developer Mode/key/session state, firmware and same-host connection outcome.
  `question`, `status:needs-info`; no compatibility failure inferred.
- [#229](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/229#issuecomment-6559060045):
  v1.5.4 cytv 0.6.1 `preflight:437` is the live-Helper replacement guard.
  The checklist label states a requirement, not its actual result. Requested
  model/firmware/component/control/error details and explained existing emergency
  stop for an intentional update. No state-file deletion or guard bypass.
  `question`, `status:needs-info` for the unresolved original report.
- [#230](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/230#issuecomment-6559061109):
  Root coordinator submission is retained; completion and cause are unknown.
  Runtime prerequisites passed, which does not establish successful deployment.
  Requested current controls/Home route, device/version, visible failure and
  original-profile availability before preparing bounded inspection. No ordinary
  status rerun, reinstall, Restore, Uninstall or recovery mutation requested.
  `bug`, `status:needs-info`.
- [#201](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201#issuecomment-6559062288):
  the C2 owner answered the exact `/dev/listApps` request; it succeeds. Updated
  the authority note and moved to `status:planned`: supported original-transaction
  terminal readback remains maintainer research. The UK6400 pending-uninstall
  case stays separate. No repeated inventory probe or file-only reconciliation.
- #21 already has a focused response to its new startup/status report. #164 has
  a maintainer response and the owner's later acknowledgement; no duplicate
  request or prototype-as-compatibility claim. #146's new G1 observation remains
  limited to its stated device/release and does not accept candidate bytes.
  Other updated issues already have current source-integration follow-up.

A fresh inventory verified exactly one `status:*` label on all 46 open issues.
No issue was closed or marked released by this task.

## Bounded implementation

No-root preflight now retains its existing Helper probe category in shared
`tv_info`. Issue JSON exports only `running`, `stopped`, `stale`, `uncertain`
(or `unknown` for unexpected values). No extra TV command, process inventory,
exception text, address, path, permission, persistent TV state or network endpoint
is added. Installation and emergency-stop behavior are unchanged. This is a
partial diagnostic improvement for #229, not a fix of its unconfirmed device
behavior. Desktop/console and Android use this shared implementation.

The developer authority note now treats the C2 endpoint question as answered,
without mistaking app inventory for original installer termination. No safe
alternative terminal-authority contract was established, so #201 recovery remains
unsupported rather than receiving a speculative bypass.

## Validation and delivery limits

- `npm ci` completed.
- The four real shell/process-fixture probe categories failed the report assertion
  before implementation and passed afterward; 10 Helper-preflight and 13
  diagnostics tests pass, including structured/private unexpected export values.
- Independent focused read-only review found no actionable issues.
- `git diff --check` passed.
- Initial broad test attempts exposed sandbox Chrome restrictions and missing
  dependencies in system Python. One full-metadata expectation was updated for
  the intentionally added field. Final prepared-environment results are recorded
  below.
- Final `PATH="$PWD/.venv-cytv/bin:$PATH" scripts/test.sh installer android`
  passed: 565 installer tests (2 platform skips), 23 Android tests, Homebrew
  payload/runtime/bridge/browser/continuation checks. Qt emitted platform/font
  capability warnings; these are not physical glyph acceptance.

This unfrozen candidate has no selected version/build or new physical acceptance.
TV model/firmware/remote for #229/#230 remain requested; their controls, sound,
standby, cold boot, OTA, rollback and recovery are unverified. No public release,
confirmed recovery or universal device support is claimed.

## Integration

[PR #231](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/231) merged
into `release/next` as `d29c0598`. Its tree matches reviewed/tested `d7e6fbd0`.
[Final affected CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41314991548)
passed on Linux/macOS, including setup/packaging, installer/Android runtime,
ARM checks and required summaries; Integration policy also passed. Standalone
browser/full-release jobs were correctly unselected for this bounded host change;
existing Homebrew UI browser checks ran within the installer group. No frozen
candidate build, physical TV test or public publication was performed.
